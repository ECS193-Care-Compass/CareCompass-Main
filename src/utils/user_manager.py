"""
User Manager with S3 Storage
Manages user profiles, sessions, and conversation history
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

logger = logging.getLogger(__name__)


class UserManagerWithS3:
    """Manages user data with optional S3 persistence"""
    
    def __init__(self, use_s3: bool = True, local_data_dir: Optional[str] = None):
        """
        Initialize UserManager
        
        Args:
            use_s3: Whether to sync data to S3
            local_data_dir: Local directory for user data (default: data/users)
        """
        self.use_s3 = use_s3 and boto3 is not None
        self.local_data_dir = Path(local_data_dir or "data/users")
        self.profiles_dir = self.local_data_dir / "profiles"
        self.sessions_dir = self.local_data_dir / "sessions"
        
        # Create directories
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # S3 setup
        self.s3_client = None
        self.s3_bucket = None
        
        if self.use_s3:
            try:
                self.s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                self.s3_bucket = os.getenv('S3_LOGS_BUCKET', '')
                if not self.s3_bucket:
                    logger.warning("S3_LOGS_BUCKET not set, disabling S3 sync")
                    self.use_s3 = False
                else:
                    logger.info(f"UserManager initialized with S3: {self.s3_bucket}")
            except Exception as e:
                logger.warning(f"S3 initialization failed, using local only: {e}")
                self.use_s3 = False
        else:
            logger.info("UserManager initialized (local only)")
    
    def _get_profile_path(self, user_id: str) -> Path:
        """Get local path for user profile"""
        safe_id = user_id.replace("/", "_").replace("\\", "_")
        return self.profiles_dir / f"{safe_id}.json"
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get local path for session"""
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        return self.sessions_dir / f"{safe_id}.json"
    
    def _sync_to_s3(self, key: str, data: dict):
        """Sync data to S3"""
        if not self.use_s3 or not self.s3_client:
            return
        
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(data, indent=2, default=str),
                ContentType='application/json'
            )
        except Exception as e:
            logger.warning(f"Failed to sync to S3: {e}")
    
    def _load_from_s3(self, key: str) -> Optional[dict]:
        """Load data from S3"""
        if not self.use_s3 or not self.s3_client:
            return None
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logger.warning(f"Failed to load from S3: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load from S3: {e}")
            return None
    
    # ==================== USER OPERATIONS ====================
    
    def create_user(self, user_id: str, metadata: Optional[dict] = None) -> dict:
        """Create a new user profile"""
        user = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "session_count": 0
        }
        
        # Save locally
        profile_path = self._get_profile_path(user_id)
        with open(profile_path, 'w') as f:
            json.dump(user, f, indent=2)
        
        # Sync to S3
        self._sync_to_s3(f"users/profiles/{user_id}.json", user)
        
        logger.info(f"Created user: {user_id}")
        return user
    
    def get_user(self, user_id: str) -> Optional[dict]:
        """Get user profile by ID"""
        profile_path = self._get_profile_path(user_id)
        
        # Try local first
        if profile_path.exists():
            try:
                with open(profile_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load local profile: {e}")
        
        # Try S3 fallback
        s3_data = self._load_from_s3(f"users/profiles/{user_id}.json")
        if s3_data:
            # Cache locally
            with open(profile_path, 'w') as f:
                json.dump(s3_data, f, indent=2)
            return s3_data
        
        return None
    
    def update_user(self, user_id: str, updates: dict) -> Optional[dict]:
        """Update user profile"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        user.update(updates)
        user["updated_at"] = datetime.now().isoformat()
        
        # Save locally
        profile_path = self._get_profile_path(user_id)
        with open(profile_path, 'w') as f:
            json.dump(user, f, indent=2)
        
        # Sync to S3
        self._sync_to_s3(f"users/profiles/{user_id}.json", user)
        
        return user
    
    # ==================== SESSION OPERATIONS ====================
    
    def create_session(self, session_id: str, user_id: str, metadata: Optional[dict] = None) -> dict:
        """Create a new session for a user"""
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "messages": [],
            "message_count": 0
        }
        
        # Save locally
        session_path = self._get_session_path(session_id)
        with open(session_path, 'w') as f:
            json.dump(session, f, indent=2)
        
        # Update user session count
        user = self.get_user(user_id)
        if user:
            self.update_user(user_id, {"session_count": user.get("session_count", 0) + 1})
        
        # Sync to S3
        self._sync_to_s3(f"users/sessions/{session_id}.json", session)
        
        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID"""
        session_path = self._get_session_path(session_id)
        
        # Try local first
        if session_path.exists():
            try:
                with open(session_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load local session: {e}")
        
        # Try S3 fallback
        s3_data = self._load_from_s3(f"users/sessions/{session_id}.json")
        if s3_data:
            # Cache locally
            with open(session_path, 'w') as f:
                json.dump(s3_data, f, indent=2)
            return s3_data
        
        return None
    
    def get_user_sessions(self, user_id: str) -> List[dict]:
        """Get all sessions for a user"""
        sessions = []
        
        # Scan local sessions directory
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                    if session.get("user_id") == user_id:
                        sessions.append({
                            "session_id": session.get("session_id"),
                            "created_at": session.get("created_at"),
                            "message_count": session.get("message_count", len(session.get("messages", [])))
                        })
            except Exception as e:
                logger.warning(f"Failed to load session {session_file}: {e}")
        
        # Sort by created_at descending
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions
    
    # ==================== MESSAGE OPERATIONS ====================
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[dict] = None) -> Optional[dict]:
        """Add a message to a session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        session["messages"].append(message)
        session["message_count"] = len(session["messages"])
        session["updated_at"] = datetime.now().isoformat()
        
        # Save locally
        session_path = self._get_session_path(session_id)
        with open(session_path, 'w') as f:
            json.dump(session, f, indent=2)
        
        # Sync to S3
        self._sync_to_s3(f"users/sessions/{session_id}.json", session)
        
        return message
    
    def get_session_messages(self, session_id: str) -> List[dict]:
        """Get all messages in a session"""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.get("messages", [])
