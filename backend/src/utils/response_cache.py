"""
Response cache using semantic similarity matching.

Two-tier caching architecture:
- L1: In-memory (fast, limited size, lost on restart)
- L2: DynamoDB (persistent, survives restarts, shared across instances)

PRIVACY PROTECTION:
- ONLY caches responses for preset/featured queries from the UI
- Free-form user input is NEVER cached or stored
- This prevents storing sensitive PII/PHI (critical for HIPAA compliance)
- Common queries like "Mental Health Support" are safe to cache
- Personal queries like "I'm suicidal and my name is..." are NEVER cached

Caches LLM responses and returns cached results for semantically similar queries
to avoid redundant LLM calls and reduce costs.
"""
import json
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
import hashlib
import time
import boto3
from botocore.exceptions import ClientError
import vertexai
from vertexai.language_models import TextEmbeddingModel
from config.settings import (
    GCP_PROJECT_ID, GCP_LOCATION, DYNAMODB_REGION,
    RESPONSE_CACHE_TABLE_NAME, RESPONSE_CACHE_PERSIST
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Featured queries from the frontend UI - ONLY these are safe to cache
# User free-form queries are NOT cached to protect sensitive information (PII/PHI)
# This is critical for HIPAA-like compliance in a mental health context
FEATURED_QUERIES = [
    "mental health support",
    "practical needs help",
    "legal & advocacy help",
    "legal and advocacy help",
]

# Exact match threshold - must be very close to preset to be considered safe
FEATURED_QUERY_SIMILARITY_THRESHOLD = 0.98


class ResponseCache:
    """
    Two-tier semantic response cache using embedding similarity.
    
    L1 (in-memory): Fast lookup for hot entries
    L2 (DynamoDB): Persistent storage across restarts
    
    Stores query embeddings and their responses. On lookup, finds the most
    similar cached query and returns its response if similarity exceeds threshold.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_cache_size: int = 500,
        ttl_seconds: int = 3600,  # 1 hour default
        featured_ttl_seconds: int = 86400,  # 24 hours for featured queries
    ):
        """
        Initialize response cache.
        
        Args:
            similarity_threshold: Minimum cosine similarity to return cached response (0.95 = very similar)
            max_cache_size: Maximum number of cached responses in L1 (LRU eviction)
            ttl_seconds: Time-to-live for cache entries in seconds
            featured_ttl_seconds: TTL for featured/preset queries (longer = more savings)
        """
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        self.featured_ttl_seconds = featured_ttl_seconds
        
        # L1 Cache: {query_hash: {"embedding": [...], "response": {...}, "timestamp": float}}
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Initialize embedding model
        if GCP_PROJECT_ID:
            vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
            self._embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            logger.info("ResponseCache initialized with Vertex AI embeddings")
        else:
            self._embedding_model = None
            logger.warning("ResponseCache disabled: GCP_PROJECT_ID not set")
        
        # Initialize DynamoDB (L2)
        self._dynamodb_available = False
        if RESPONSE_CACHE_PERSIST:
            try:
                self._dynamodb = boto3.resource("dynamodb", region_name=DYNAMODB_REGION)
                self._table = self._dynamodb.Table(RESPONSE_CACHE_TABLE_NAME)
                self._table.load()  # Verify table exists
                self._dynamodb_available = True
                logger.info(f"ResponseCache L2 (DynamoDB) connected: {RESPONSE_CACHE_TABLE_NAME}")
                # Warm L1 cache from DynamoDB
                self._warm_cache()
            except Exception as e:
                logger.warning(f"DynamoDB cache unavailable, using L1 only: {e}")
        
        # Stats
        self._hits = 0
        self._misses = 0
        self._l1_hits = 0
        self._l2_hits = 0
    
    def _warm_cache(self):
        """Load recent entries from DynamoDB into L1 cache on startup."""
        if not self._dynamodb_available:
            return
        
        try:
            now = int(time.time())
            response = self._table.scan(
                FilterExpression="#t > :now",
                ExpressionAttributeNames={"#t": "ttl"},
                ExpressionAttributeValues={":now": now},
                Limit=self.max_cache_size,
            )
            
            items = response.get("Items", [])
            for item in items:
                query_hash = item.get("query_hash")
                embedding = json.loads(item.get("embedding", "[]"))
                response_data = json.loads(item.get("response", "{}"))
                timestamp = float(item.get("timestamp", 0))
                
                if query_hash and embedding and response_data:
                    self._cache[query_hash] = {
                        "embedding": embedding,
                        "response": response_data,
                        "timestamp": timestamp,
                    }
            
            logger.info(f"Warmed L1 cache with {len(items)} entries from DynamoDB")
        except Exception as e:
            logger.warning(f"Failed to warm cache from DynamoDB: {e}")
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using Vertex AI."""
        if not self._embedding_model:
            return None
        
        try:
            embeddings = self._embedding_model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def _query_hash(self, query: str) -> str:
        """Generate hash for query (used as cache key)."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _evict_expired(self):
        """Remove expired entries from L1."""
        now = time.time()
        expired = [
            k for k, v in self._cache.items()
            if now - v["timestamp"] > v.get("ttl", self.ttl_seconds)
        ]
        for k in expired:
            del self._cache[k]
    
    def _evict_lru(self):
        """Remove least recently used entries from L1 if over max size."""
        while len(self._cache) > self.max_cache_size:
            self._cache.popitem(last=False)
    
    def _find_similar_in_l1(self, query_embedding: List[float]) -> Optional[Tuple[str, float, Dict]]:
        """Find most similar entry in L1 cache."""
        best_match = None
        
        for key, entry in self._cache.items():
            similarity = self._cosine_similarity(query_embedding, entry["embedding"])
            if similarity >= self.similarity_threshold:
                if best_match is None or similarity > best_match[1]:
                    best_match = (key, similarity, entry["response"])
        
        return best_match
    
    def _find_similar_in_l2(self, query_embedding: List[float]) -> Optional[Tuple[str, float, Dict, Dict]]:
        """Find most similar entry in L2 (DynamoDB) cache."""
        if not self._dynamodb_available:
            return None
        
        try:
            now = int(time.time())
            response = self._table.scan(
                FilterExpression="ttl > :now",
                ExpressionAttributeValues={":now": now},
            )
            
            items = response.get("Items", [])
            best_match = None
            
            for item in items:
                embedding = json.loads(item.get("embedding", "[]"))
                if not embedding:
                    continue
                
                similarity = self._cosine_similarity(query_embedding, embedding)
                if similarity >= self.similarity_threshold:
                    if best_match is None or similarity > best_match[1]:
                        response_data = json.loads(item.get("response", "{}"))
                        best_match = (
                            item.get("query_hash"),
                            similarity,
                            response_data,
                            item  # Full item for L1 promotion
                        )
            
            return best_match
        except Exception as e:
            logger.warning(f"Error scanning DynamoDB cache: {e}")
            return None
    
    def _promote_to_l1(self, item: Dict):
        """Promote a DynamoDB entry to L1 cache."""
        query_hash = item.get("query_hash")
        embedding = json.loads(item.get("embedding", "[]"))
        response_data = json.loads(item.get("response", "{}"))
        timestamp = float(item.get("timestamp", time.time()))
        
        self._cache[query_hash] = {
            "embedding": embedding,
            "response": response_data,
            "timestamp": timestamp,
        }
        self._cache.move_to_end(query_hash)
        self._evict_lru()
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Look up cached response for a query.
        
        PRIVACY PROTECTION: Only returns cache hits for preset/featured queries.
        Free-form user queries bypass the cache entirely to ensure personalized,
        context-appropriate responses for potentially sensitive situations.
        
        Args:
            query: User query to look up
            
        Returns:
            Cached response dict if found and query is safe, None otherwise
        """
        if not self._embedding_model:
            return None
        
        # PRIVACY CHECK: Only return cached results for safe preset queries
        # This prevents returning generic cached answers for sensitive situations
        is_safe, canonical_query = self._is_safe_to_cache(query)
        if not is_safe:
            logger.debug(f"Cache bypassed for privacy (not a preset query): '{query[:30]}...'")
            self._misses += 1
            return None
        
        self._evict_expired()
        
        # Get embedding for canonical query (normalized preset, not raw user input)
        query_embedding = self._get_embedding(canonical_query)
        if query_embedding is None:
            self._misses += 1
            return None
        
        # Check L1 (in-memory) first
        l1_match = self._find_similar_in_l1(query_embedding)
        if l1_match:
            key, similarity, response = l1_match
            self._cache.move_to_end(key)
            self._hits += 1
            self._l1_hits += 1
            logger.info(f"Cache HIT L1 (similarity={similarity:.3f}): '{query[:30]}...'")
            return response
        
        # Check L2 (DynamoDB)
        l2_match = self._find_similar_in_l2(query_embedding)
        if l2_match:
            key, similarity, response, item = l2_match
            # Promote to L1
            self._promote_to_l1(item)
            self._hits += 1
            self._l2_hits += 1
            logger.info(f"Cache HIT L2 (similarity={similarity:.3f}): '{query[:30]}...'")
            return response
        
        self._misses += 1
        logger.debug(f"Cache MISS: '{query[:30]}...'")
        return None
    
    def _is_safe_to_cache(self, query: str) -> Tuple[bool, str]:
        """
        Check if query is safe to cache (i.e., matches a preset/featured query).
        
        PRIVACY PROTECTION: Only caches responses for generic preset queries.
        User free-form input is NEVER cached to avoid storing sensitive PII/PHI.
        
        Returns:
            Tuple of (is_safe, matched_query) - matched_query is the canonical
            featured query to use as the cache key (not the user's raw input)
        """
        query_lower = query.lower().strip()
        
        # Check for exact or near-exact match with featured queries
        for featured in FEATURED_QUERIES:
            # Exact match
            if query_lower == featured:
                return (True, featured)
            # Near-exact (handle minor variations like trailing punctuation)
            if query_lower.rstrip('?!.') == featured:
                return (True, featured)
        
        # Not a featured query - do NOT cache (may contain PII)
        return (False, "")
    
    def put(self, query: str, response: Dict[str, Any]):
        """
        Store a response in cache (both L1 and L2).
        
        PRIVACY PROTECTION: Only caches preset/featured queries.
        Free-form user input is NEVER stored to avoid caching sensitive PII/PHI.
        
        Args:
            query: User query
            response: Response dict to cache
        """
        if not self._embedding_model:
            return
        
        # Skip caching crisis responses (these should always be fresh)
        if response.get("is_crisis", False):
            logger.debug("Skipping cache for crisis response")
            return
        
        # PRIVACY CHECK: Only cache preset queries, not free-form user input
        is_safe, canonical_query = self._is_safe_to_cache(query)
        if not is_safe:
            logger.debug(f"Skipping cache for privacy (not a preset query): '{query[:30]}...'")
            return
        
        # Use the canonical featured query as key, not the user's raw input
        query_hash = self._query_hash(canonical_query)
        
        # Get embedding for the canonical query
        embedding = self._get_embedding(canonical_query)
        if embedding is None:
            return
        
        timestamp = time.time()
        
        # Featured queries get longer TTL
        entry_ttl = self.featured_ttl_seconds
        
        # Store in L1 (using canonical query, not raw user input)
        self._cache[query_hash] = {
            "embedding": embedding,
            "response": response,
            "timestamp": timestamp,
            "ttl": entry_ttl,
            "canonical_query": canonical_query,  # Store canonical form, not raw
        }
        self._cache.move_to_end(query_hash)
        self._evict_lru()
        
        # Store in L2 (DynamoDB) - NO raw user input stored
        if self._dynamodb_available:
            try:
                ttl = int(timestamp + entry_ttl)
                self._table.put_item(
                    Item={
                        "query_hash": query_hash,
                        "embedding": json.dumps(embedding),
                        "response": json.dumps(response),
                        "timestamp": str(timestamp),
                        "ttl": ttl,
                        "canonical_query": canonical_query,  # Safe preset query only
                    }
                )
                logger.info(f"Cached preset response (TTL={entry_ttl}s): '{canonical_query}'")
            except Exception as e:
                logger.warning(f"Failed to write to DynamoDB cache: {e}")
                logger.debug(f"Cached response in L1 only: '{query[:30]}...'")
        else:
            logger.debug(f"Cached response in L1: '{query[:30]}...'")
    
    def clear(self):
        """Clear L1 cache (DynamoDB entries expire via TTL)."""
        self._cache.clear()
        logger.info("L1 response cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "l1_hits": self._l1_hits,
            "l2_hits": self._l2_hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_rate, 1),
            "l1_size": len(self._cache),
            "max_l1_size": self.max_cache_size,
            "dynamodb_enabled": self._dynamodb_available,
        }
