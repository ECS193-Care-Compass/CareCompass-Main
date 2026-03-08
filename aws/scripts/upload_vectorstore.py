"""
Upload local vectorstore to S3 for Lambda cold-start restore.

Usage:
    python aws/scripts/upload_vectorstore.py

Reads AWS credentials from .env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).
"""
import os
import sys
import zipfile
from pathlib import Path

# Add project root so we can import settings
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import boto3

VECTORSTORE_DIR = project_root / "data" / "processed" / "vectorstore"
S3_BUCKET = os.getenv("S3_VECTORDB_BUCKET", "care-compass-vectordb-432732422396-dev")
S3_KEY = "vectorstore/vectorstore.zip"
ZIP_PATH = project_root / "data" / "processed" / "vectorstore.zip"


def create_zip():
    """Zip the vectorstore directory"""
    print(f"Zipping {VECTORSTORE_DIR} ...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(VECTORSTORE_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(VECTORSTORE_DIR)
                zf.write(file_path, arcname)
    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Created {ZIP_PATH} ({size_mb:.1f} MB)")


def upload_to_s3():
    """Upload zip to S3"""
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    print(f"Uploading to s3://{S3_BUCKET}/{S3_KEY} ...")
    s3.upload_file(str(ZIP_PATH), S3_BUCKET, S3_KEY)
    print("Upload complete!")


def main():
    if not VECTORSTORE_DIR.exists():
        print(f"ERROR: Vectorstore not found at {VECTORSTORE_DIR}")
        print("Run the backend locally first to build it.")
        sys.exit(1)

    create_zip()
    upload_to_s3()

    # Clean up local zip
    ZIP_PATH.unlink()
    print(f"Cleaned up {ZIP_PATH}")
    print(f"\nDone! Lambda will download from s3://{S3_BUCKET}/{S3_KEY} on cold start.")


if __name__ == "__main__":
    main()