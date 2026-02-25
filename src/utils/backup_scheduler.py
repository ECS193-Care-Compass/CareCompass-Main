"""
Backup scheduler for ChromaDB vector store
Periodically backs up the local vector database to S3
"""
import logging
import os
import tarfile
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
try:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
    from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
except ImportError:
    BackgroundScheduler = None  # type: ignore
    IntervalTrigger = None  # type: ignore

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Schedule periodic backups of ChromaDB to S3"""
    
    def __init__(self, 
                 vectorstore_path: str,
                 s3_manager=None,
                 backup_interval_hours: int = 24):
        """
        Initialize backup scheduler
        
        Args:
            vectorstore_path: Path to local ChromaDB directory
            s3_manager: S3Manager instance for uploads
            backup_interval_hours: Interval between backups (default: daily)
        """
        self.vectorstore_path = Path(vectorstore_path)
        self.s3_manager = s3_manager
        self.backup_interval_hours = backup_interval_hours
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        
        logger.info(f"BackupScheduler initialized: {vectorstore_path}, interval: {backup_interval_hours}h")
    
    def start(self):
        """Start the backup scheduler"""
        if self.is_running:
            logger.warning("BackupScheduler is already running")
            return
        
        if not self.s3_manager:
            logger.warning("S3Manager not configured - backups disabled")
            return
        
        try:
            self.scheduler.add_job(
                self._backup_job,
                IntervalTrigger(hours=self.backup_interval_hours),
                id='vectordb_backup',
                name='ChromaDB Backup to S3',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"BackupScheduler started (runs every {self.backup_interval_hours} hours)")
            
        except Exception as e:
            logger.error(f"Failed to start BackupScheduler: {e}")
    
    def stop(self):
        """Stop the backup scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("BackupScheduler stopped")
    
    def _backup_job(self):
        """Backup job executed on schedule"""
        try:
            logger.info("Starting ChromaDB backup...")
            
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"vectordb_backup_{timestamp}.tar.gz"
            temp_backup_path = Path(tempfile.gettempdir()) / backup_name
            
            # Compress vectorstore directory using tarfile
            logger.info(f"Compressing vectorstore to {temp_backup_path}")
            try:
                with tarfile.open(str(temp_backup_path), "w:gz") as tar:
                    tar.add(str(self.vectorstore_path), arcname="vectorstore")
            except Exception as tar_error:
                logger.error(f"Tarfile compression failed: {tar_error}")
                return
            
            
            if not temp_backup_path.exists():
                logger.error(f"Backup file not created: {temp_backup_path}")
                return
            
            file_size_mb = temp_backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup compressed: {file_size_mb:.2f}MB")
            
            # Upload to S3
            s3_key = f"backups/{backup_name}"
            logger.info(f"Uploading to S3: {s3_key}")
            
            success = self.s3_manager.upload_document(
                str(temp_backup_path),
                s3_key,
                bucket=self.s3_manager.vectordb_bucket
            )
            
            # Cleanup temp file
            temp_backup_path.unlink()
            
            if success:
                logger.info(f"✓ ChromaDB backup successful: {s3_key} ({file_size_mb:.2f}MB)")
                
                # Keep only last 5 backups
                self._cleanup_old_backups()
            else:
                logger.error("Failed to upload backup to S3")
                
        except Exception as e:
            logger.error(f"Backup job failed: {e}", exc_info=True)
    
    def _cleanup_old_backups(self, keep_count: int = 5):
        """Remove old backups, keep only the most recent ones"""
        try:
            if not self.s3_manager:
                return
            
            backups = self.s3_manager.list_documents(
                prefix="backups/",
                bucket=self.s3_manager.vectordb_bucket
            )
            
            # Sort by last modified (newest first)
            backups.sort(
                key=lambda x: x['last_modified'],
                reverse=True
            )
            
            # Delete old ones
            for backup in backups[keep_count:]:
                try:
                    self.s3_manager.s3_client.delete_object(
                        Bucket=self.s3_manager.vectordb_bucket,
                        Key=backup['key']
                    )
                    logger.info(f"Deleted old backup: {backup['key']}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup['key']}: {e}")
            
        except Exception as e:
            logger.warning(f"Could not cleanup old backups: {e}")
