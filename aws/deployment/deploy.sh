#!/bin/bash

# Bash deployment script for CARE Compass AWS Lambda + S3
# Usage: ./deploy.sh -e dev -p "your-gcp-project" -k "/path/to/gcp-key.json"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
GCP_PROJECT_ID=""
GCP_KEY_FILE=""
GCP_LOCATION="us-central1"
AWS_PROFILE="default"
AWS_REGION="us-east-1"
LAMBDA_MEMORY=1024
LAMBDA_TIMEOUT=300

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--project-id)
            GCP_PROJECT_ID="$2"
            shift 2
            ;;
        -k|--key-file)
            GCP_KEY_FILE="$2"
            shift 2
            ;;
        -l|--location)
            GCP_LOCATION="$2"
            shift 2
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -m|--memory)
            LAMBDA_MEMORY="$2"
            shift 2
            ;;
        -t|--timeout)
            LAMBDA_TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$ENVIRONMENT" ] || [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_KEY_FILE" ]; then
    echo -e "${RED}Error: Missing required parameters${NC}"
    echo "Usage: $0 -e dev|prod -p 'gcp-project-id' -k '/path/to/gcp-key.json' [options]"
    echo ""
    echo "Options:"
    echo "  -e, --environment dev|prod   Deployment environment (required)"
    echo "  -p, --project-id ID          GCP project ID (required)"
    echo "  -k, --key-file PATH          Path to GCP service account JSON key (required)"
    echo "  -l, --location REGION        GCP location (default: us-central1)"
    echo "  --profile PROFILE            AWS profile to use (default: default)"
    echo "  -r, --region REGION          AWS region (default: us-east-1)"
    echo "  -m, --memory MB              Lambda memory (default: 1024)"
    echo "  -t, --timeout SEC            Lambda timeout (default: 300)"
    exit 1
fi

# Validate GCP key file exists
if [ ! -f "$GCP_KEY_FILE" ]; then
    echo -e "${RED}Error: GCP key file not found: $GCP_KEY_FILE${NC}"
    exit 1
fi

# Base64 encode GCP credentials
GCP_CREDENTIALS_BASE64=$(base64 -w0 "$GCP_KEY_FILE")

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}CARE Compass AWS Deployment${NC}"
echo -e "${CYAN}================================${NC}"

echo -e "\nEnvironment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "AWS Profile: ${YELLOW}$AWS_PROFILE${NC}"
echo -e "AWS Region: ${YELLOW}$AWS_REGION${NC}"
echo -e "Lambda Memory: ${YELLOW}${LAMBDA_MEMORY}MB${NC}"
echo -e "Lambda Timeout: ${YELLOW}${LAMBDA_TIMEOUT}s${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Step 1: Validate AWS credentials
echo -e "\n${CYAN}[1/5] Validating AWS credentials...${NC}"
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${RED}[FAIL] Error: AWS credentials not configured or invalid${NC}"
    exit 1
fi
echo -e "${GREEN}[PASS] AWS credentials valid${NC}"

ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" --query Account --output text)
echo -e "  Account ID: $(tput setaf 8)$ACCOUNT_ID$(tput sgr0)"

# Step 2: Validate template
echo -e "\n${CYAN}[2/5] Validating CloudFormation template...${NC}"
TEMPLATE_PATH="$PROJECT_ROOT/aws/infrastructure/template.yaml"
if ! aws cloudformation validate-template \
    --template-body "file://$TEMPLATE_PATH" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${RED}[FAIL] Template validation failed${NC}"
    exit 1
fi
echo -e "${GREEN}[PASS] Template is valid${NC}"

# Step 3: Build Lambda package
echo -e "\n${CYAN}[3/5] Building Lambda deployment package...${NC}"
LAMBDA_DIR="$PROJECT_ROOT/aws/lambda"
BUILD_DIR="$LAMBDA_DIR/build"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
    echo -e "  Cleaned previous build"
fi

# Create build directory
mkdir -p "$BUILD_DIR"

# Copy Lambda handler and modules
echo -e "  Copying Lambda handler..."
cp "$LAMBDA_DIR/lambda_handler.py" "$BUILD_DIR/"
cp "$LAMBDA_DIR/s3_manager.py" "$BUILD_DIR/"

# Copy source code
echo -e "  Copying source code..."
cp -r "$PROJECT_ROOT/backend/src" "$BUILD_DIR/"
cp -r "$PROJECT_ROOT/backend/config" "$BUILD_DIR/"
cp "$PROJECT_ROOT/backend/main.py" "$BUILD_DIR/"

# Install dependencies
echo -e "  Installing Python dependencies..."
pip install -r "$LAMBDA_DIR/requirements.txt" -t "$BUILD_DIR" --quiet

echo -e "${GREEN}[PASS] Lambda package built successfully${NC}"

# Step 4: Deploy with SAM
echo -e "\n${CYAN}[4/5] Deploying with AWS SAM...${NC}"

STACK_NAME="care-compass-stack-$ENVIRONMENT"
S3_BUCKET="care-compass-deploy-$ACCOUNT_ID-$ENVIRONMENT"

# Create S3 bucket for SAM artifacts if it doesn't exist
if ! aws s3 ls "s3://$S3_BUCKET" --profile "$AWS_PROFILE" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "  Creating S3 bucket for SAM artifacts..."
    aws s3 mb "s3://$S3_BUCKET" --profile "$AWS_PROFILE" --region "$AWS_REGION"
fi

# Run SAM deploy
sam deploy \
    --template-file "$TEMPLATE_PATH" \
    --stack-name "$STACK_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --capabilities CAPABILITY_IAM \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        GCPProjectId="$GCP_PROJECT_ID" \
        GCPLocation="$GCP_LOCATION" \
        GCPCredentialsBase64="$GCP_CREDENTIALS_BASE64" \
        LambdaMemory="$LAMBDA_MEMORY" \
        LambdaTimeout="$LAMBDA_TIMEOUT" \
    --resolve-image-repos \
    --no-fail-on-empty-changeset \
    --no-confirm-changeset

if [ $? -ne 0 ]; then
    echo -e "${RED}[FAIL] SAM deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}[PASS] SAM deployment successful${NC}"

# Step 5: Get stack outputs
echo -e "\n${CYAN}[5/5] Retrieving deployment outputs...${NC}"

echo -e "\n${CYAN}$( printf '%.0s=' {1..50} )${NC}"
echo -e "${GREEN}DEPLOYMENT COMPLETE${NC}"
echo -e "${CYAN}$( printf '%.0s=' {1..50} )${NC}"

aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

# Save outputs to file
OUTPUT_FILE="$SCRIPT_DIR/deployment-outputs-$ENVIRONMENT.json"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs' > "$OUTPUT_FILE"

echo -e "\nOutputs saved to: ${GREEN}$OUTPUT_FILE${NC}"

echo -e "\n${CYAN}$( printf '%.0s=' {1..50} )${NC}"
echo -e "${CYAN}Next Steps:${NC}"
echo -e "${CYAN}$( printf '%.0s=' {1..50} )${NC}"
echo "1. Update your Electron frontend with the API endpoint"
echo "2. Test the /health endpoint in your browser"
echo "3. Upload reference documents to S3 (optional)"
echo "4. Monitor CloudWatch logs for any issues"
