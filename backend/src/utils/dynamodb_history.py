"""
DynamoDB-backed conversation history.

Stores per-session conversation turns in DynamoDB, replacing the
in-memory list that was previously in LLMHandler.

Schema:
    session_id  (partition key) — String
    timestamp   (sort key)      — Number (Unix timestamp in ms)
    role        — "user" or "model"
    message     — message content
    ttl         — auto-delete timestamp for guest sessions
"""

import time
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Optional
from config.settings import DYNAMODB_TABLE_NAME, DYNAMODB_REGION, DYNAMODB_TTL_MINUTES, MAX_HISTORY_TURNS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DynamoDBHistory:
    """Read/write conversation history to DynamoDB."""

    def __init__(
        self,
        table_name: str = DYNAMODB_TABLE_NAME,
        region: str = DYNAMODB_REGION,
        max_turns: int = MAX_HISTORY_TURNS,
        ttl_minutes: int = DYNAMODB_TTL_MINUTES,
    ):
        self.table_name = table_name
        self.max_turns = max_turns
        self.ttl_minutes = ttl_minutes

        try:
            self._dynamodb = boto3.resource("dynamodb", region_name=region)
            self._table = self._dynamodb.Table(table_name)
            # Verify table exists
            self._table.load()
            self._available = True
            logger.info(f"DynamoDB history connected: {table_name}")
        except Exception as e:
            self._available = False
            logger.warning(f"DynamoDB unavailable, falling back to in-memory history: {e}")

    @property
    def available(self) -> bool:
        return self._available

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get the last N turns for a session.

        Returns list of {"role": "user"|"model", "parts": ["message"]}
        in chronological order, matching the format LLMHandler expects.
        """
        if not self._available:
            return []

        try:
            max_messages = self.max_turns * 2  # 2 messages per turn
            response = self._table.query(
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": session_id},
                ScanIndexForward=True,  # oldest first
                Limit=max_messages + 20,  # fetch extra to trim
            )

            items = response.get("Items", [])

            # Take only the last max_messages
            items = items[-max_messages:]

            history = [
                {"role": item["role"], "parts": [item["message"]]}
                for item in items
            ]

            logger.info(f"Loaded {len(history)} messages for session {session_id[:12]}...")
            return history

        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            return []

    # ── Write ─────────────────────────────────────────────────────────────────

    def add_turn(self, session_id: str, user_message: str, model_message: str) -> None:
        """Write a user+model turn to DynamoDB."""
        if not self._available:
            return

        now_ms = int(time.time() * 1000)
        ttl_epoch = int(time.time()) + (self.ttl_minutes * 60)

        try:
            with self._table.batch_writer() as batch:
                batch.put_item(Item={
                    "session_id": session_id,
                    "timestamp":  now_ms,
                    "role":       "user",
                    "message":    user_message,
                    "ttl":        ttl_epoch,
                })
                batch.put_item(Item={
                    "session_id": session_id,
                    "timestamp":  now_ms + 1,  # +1ms so model sorts after user
                    "role":       "model",
                    "message":    model_message,
                    "ttl":        ttl_epoch,
                })

            logger.info(f"Saved turn for session {session_id[:12]}...")

        except Exception as e:
            logger.error(f"Failed to write history: {e}")

    # ── Clear ─────────────────────────────────────────────────────────────────

    def clear_session(self, session_id: str) -> None:
        """Delete all history for a session."""
        if not self._available:
            return

        try:
            response = self._table.query(
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": session_id},
                ProjectionExpression="session_id, #ts",
                ExpressionAttributeNames={"#ts": "timestamp"},
            )

            with self._table.batch_writer() as batch:
                for item in response.get("Items", []):
                    batch.delete_item(Key={
                        "session_id": item["session_id"],
                        "timestamp":  item["timestamp"],
                    })

            logger.info(f"Cleared history for session {session_id[:12]}...")

        except Exception as e:
            logger.error(f"Failed to clear history: {e}")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get message count for a session."""
        if not self._available:
            return {"total_turns": 0, "max_turns": self.max_turns, "messages": 0}

        try:
            response = self._table.query(
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": session_id},
                Select="COUNT",
            )
            count = response.get("Count", 0)
            return {
                "total_turns": count // 2,
                "max_turns":   self.max_turns,
                "messages":    count,
            }
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"total_turns": 0, "max_turns": self.max_turns, "messages": 0}
