"""
AWS S3 Integration for CARE Bot
Handles document storage and retrieval from S3
"""
try:
    import boto3  # type: ignore
except ImportError:
    boto3 = None  # type: ignore
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class S3Manager:
    """Manages S3 operations for CARE Bot documents"""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize S3 Manager
        
        Args:
            region: AWS region (default: us-east-1)
        """
        self.s3_client = boto3.client("s3", region_name=region)
        self.documents_bucket = os.getenv("S3_DOCUMENTS_BUCKET", "")
        self.processed_bucket = os.getenv("S3_PROCESSED_BUCKET", "")
        self.vectordb_bucket = os.getenv("S3_VECTORDB_BUCKET", "")
        if not self.documents_bucket:
            logger.warning("S3_DOCUMENTS_BUCKET not set in environment variables")
        if not self.vectordb_bucket:
            logger.warning("S3_VECTORDB_BUCKET not set in environment variables")
        
        logger.info(f"S3Manager initialized with buckets: {self.documents_bucket}, {self.processed_bucket}, {self.vectordb_bucket}")
    
    def upload_document(self, file_path: str, s3_key: str, bucket: Optional[str] = None) -> bool:
        """
        Upload a document to S3
        
        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path in bucket)
            bucket: Target bucket (uses documents_bucket if None)
        
        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self.documents_bucket
        
        try:
            logger.info(f"Uploading {file_path} to s3://{bucket}/{s3_key}")
            self.s3_client.upload_file(file_path, bucket, s3_key)
            logger.info(f"Successfully uploaded to S3")
            return True
        except Exception as e:
            logger.error(f"Failed to upload document: {str(e)}")
            return False
    
    def download_document(self, s3_key: str, local_path: str, bucket: Optional[str] = None) -> bool:
        """
        Download a document from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            local_path: Local path to save file
            bucket: Source bucket (uses documents_bucket if None)
        
        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self.documents_bucket
        
        try:
            logger.info(f"Downloading s3://{bucket}/{s3_key} to {local_path}")
            self.s3_client.download_file(bucket, s3_key, local_path)
            logger.info(f"Successfully downloaded from S3")
            return True
        except Exception as e:
            logger.error(f"Failed to download document: {str(e)}")
            return False
    
    def list_documents(self, prefix: str = "", bucket: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List documents in S3 bucket
        
        Args:
            prefix: Filter by key prefix
            bucket: Bucket to list (uses documents_bucket if None)
        
        Returns:
            List of document metadata
        """
        bucket = bucket or self.documents_bucket
        
        try:
            logger.info(f"Listing documents in s3://{bucket}/{prefix}")
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            documents = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    documents.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat()
                    })
            
            logger.info(f"Found {len(documents)} documents")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            return []
    
    def backup_vectordb(self, vectordb_path: str, s3_key: str = "vectordb_backup.tar.gz") -> bool:
        """
        Backup ChromaDB to S3
        
        Args:
            vectordb_path: Local path to ChromaDB
            s3_key: Target S3 key in vectordb_bucket
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Backing up vector database from {vectordb_path}")
            self.s3_client.upload_file(
                vectordb_path,
                self.vectordb_bucket,
                s3_key
            )
            logger.info(f"Vector database backed up to S3")
            return True
        except Exception as e:
            logger.error(f"Failed to backup vector database: {str(e)}")
            return False
    
    def restore_vectordb(self, local_path: str, s3_key: str = "vectordb_backup.tar.gz") -> bool:
        """
        Restore ChromaDB from S3
        
        Args:
            local_path: Local path to restore to
            s3_key: Source S3 key in vectordb_bucket
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Restoring vector database to {local_path}")
            self.s3_client.download_file(
                self.vectordb_bucket,
                s3_key,
                local_path
            )
            logger.info(f"Vector database restored from S3")
            return True
        except Exception as e:
            logger.error(f"Failed to restore vector database: {str(e)}")
            return False
    
    def create_signed_url(self, s3_key: str, expiration: int = 3600, bucket: Optional[str] = None) -> str:
        """
        Generate a signed URL for S3 object
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds (default: 1 hour)
            bucket: Bucket (uses documents_bucket if None)
        
        Returns:
            Signed URL string
        """
        bucket = bucket or self.documents_bucket
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return ""
    
    def get_object_info(self, s3_key: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get metadata about an S3 object
        
        Args:
            s3_key: S3 object key
            bucket: Bucket (uses documents_bucket if None)
        
        Returns:
            Object metadata dictionary or None
        """
        bucket = bucket or self.documents_bucket
        
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=s3_key)
            return {
                "size": response["ContentLength"],
                "last_modified": response["LastModified"].isoformat(),
                "content_type": response.get("ContentType", "unknown"),
                "etag": response.get("ETag", "")
            }
        except Exception as e:
            logger.warning(f"Object not found or error: {str(e)}")
            return None
    
    def setup_buckets(self) -> bool:
        """
        Create S3 buckets if they don't exist
        (Useful for initial setup)
        
        Returns:
            True if successful
        """
        try:
            for bucket_name in [self.documents_bucket, self.processed_bucket, self.vectordb_bucket]:
                try:
                    self.s3_client.head_bucket(Bucket=bucket_name)
                    logger.info(f"Bucket {bucket_name} already exists")
                except Exception:
                    logger.info(f"Creating bucket {bucket_name}")
                    self.s3_client.create_bucket(Bucket=bucket_name)
                    # Enable versioning for backups
                    self.s3_client.put_bucket_versioning(
                        Bucket=bucket_name,
                        VersioningConfiguration={"Status": "Enabled"}
                    )
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup buckets: {str(e)}")
            return False


def get_s3_manager(region: str = "us-east-1") -> S3Manager:
    """Factory function to get S3Manager instance"""
    return S3Manager(region=region)
