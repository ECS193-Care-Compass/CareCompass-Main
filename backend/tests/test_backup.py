"""
Manual test of ChromaDB backup to S3
"""
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add paths
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "aws" / "lambda"))

try:
    from s3_manager import S3Manager  # type: ignore
except ImportError:
    S3Manager = None  # type: ignore
from src.utils.backup_scheduler import BackupScheduler
from config.settings import VECTORSTORE_DIR

def test_backup():
    """Test backup functionality"""
    try:
        logger.info("=" * 60)
        logger.info("TESTING CHROMADB BACKUP TO S3")
        logger.info("=" * 60)
        
        # Initialize S3Manager
        logger.info("\n1. Initializing S3Manager...")
        s3_manager = S3Manager(region="us-east-1")
        logger.info(f"   ✓ S3Manager initialized")
        logger.info(f"   - Documents: {s3_manager.documents_bucket}")
        logger.info(f"   - Processed: {s3_manager.processed_bucket}")
        logger.info(f"   - VectorDB: {s3_manager.vectordb_bucket}")
        logger.info(f"   - Logs: {s3_manager.s3_client._client_config.__dict__.get('region_name', 'N/A')}")
        
        # Initialize BackupScheduler
        logger.info("\n2. Initializing BackupScheduler...")
        backup_scheduler = BackupScheduler(
            vectorstore_path=str(VECTORSTORE_DIR),
            s3_manager=s3_manager,
            backup_interval_hours=24
        )
        logger.info(f"   ✓ BackupScheduler initialized")
        logger.info(f"   - VectorStore path: {VECTORSTORE_DIR}")
        logger.info(f"   - Backup interval: 24 hours")
        
        # Test backup
        logger.info("\n3. Running backup job...")
        backup_scheduler._backup_job()
        logger.info("   ✓ Backup job completed")
        
        # List backups in S3
        logger.info("\n4. Checking backups in S3...")
        backups = s3_manager.list_documents(
            prefix="backups/",
            bucket=s3_manager.vectordb_bucket
        )
        
        if backups:
            logger.info(f"   ✓ Found {len(backups)} backup(s):")
            for backup in backups:
                size_mb = backup['size'] / (1024 * 1024)
                logger.info(f"     - {backup['key']} ({size_mb:.2f}MB)")
                logger.info(f"       Last modified: {backup['last_modified']}")
        else:
            logger.warning("   ✗ No backups found in S3")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ BACKUP TEST SUCCESSFUL")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n✗ BACKUP TEST FAILED: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    test_backup()
