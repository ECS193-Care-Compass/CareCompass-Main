# CARE Compass AWS Infrastructure

Complete serverless deployment for CARE Compass on AWS Lambda + S3.

## Architecture Overview

```
Electron Frontend 
    ↓ (HTTPS)
API Gateway → Lambda (care-compass-dev) 
    ↓
    ├── ChromaDB (Vector Store)
    ├── Google Gemini AI (LLM)
    └── S3 (Document Storage + Logs)
```

## File Structure

```
aws/
├── lambda/                  # Lambda function code
│   ├── lambda_handler.py    # Main Lambda handler
│   ├── s3_manager.py        # S3 integration
│   ├── requirements.txt     # Python dependencies
│   └── build/               # Deployment package (generated)
├── infrastructure/
│   └── template.yaml        # SAM CloudFormation template
├── deployment/
│   ├── deploy.ps1          # Windows deployment
│   ├── deploy.sh           # Mac/Linux deployment
│   └── .env.example        # Reference only (use root .env)
└── README.md               # This file
```

## Quick Start

### Prerequisites
- AWS CLI v2
- AWS SAM CLI
- Python 3.11+
- Google Generative AI Key
- Root `.env` file configured (copy from `.env.example` and fill in your values)

### Deploy to Lambda (2 minutes)

**Windows (PowerShell):**
```powershell
.\aws\deployment\deploy.ps1 -Environment dev -GoogleApiKey "your_key_here"
```

**Mac/Linux:**
```bash
./aws/deployment/deploy.sh -e dev -k "your_key_here"
```

This will:
- Create S3 buckets (documents, processed, vectors)
- Build Lambda package with dependencies
- Deploy via CloudFormation
- Output API Gateway URL

### After Deployment

Update your frontend `.env.local`:
```
VITE_API_BASE_URL=https://xxxxx.lambda-url.us-east-1.on.aws
```

## S3 Buckets

| Bucket | Purpose |
|--------|---------|
| `care-compass-documents-*-dev` | Original documents |
| `care-compass-processed-*-dev` | Processed metadata |
| `care-compass-logs-*-dev` | Interaction logs |

## Lambda Configuration

- **Runtime:** Python 3.11
- **Memory:** 1024 MB
- **Timeout:** 300s
- **Concurrent Executions:** 1000

## Local Development

Run locally before deploying:

```bash
cd C:\Users\steph\CARE-COMPASS\CareCompass
uvicorn api:app --port 8000 --reload
```

Frontend will connect to `http://localhost:8000` if configured locally.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Send query, get response |
| `/clear` | POST | Clear conversation history |
| `/health` | GET | Health check |
| `/stats` | GET | Bot statistics |
| `/categories` | GET | Available scenarios |

## Useful AWS Commands

See [AWS_COMMANDS.md](AWS_COMMANDS.md) for CLI reference.

**Quick check:**
```powershell
# View Lambda logs
aws logs tail /aws/lambda/care-compass-dev --follow

# View S3 interactions log
aws s3 ls s3://care-compass-logs-432732422396-dev/logs/interactions/ --recursive

# Get API URL
aws lambda get-function-url-config --function-name care-compass-dev
```

## Troubleshooting

**Lambda timeout?**
- Increase timeout in SAM template from 300s to 900s
- Redeploy via `deploy.ps1`

**S3 access denied?**
- Check IAM role permissions in CloudFormation stack
- Verify bucket names match environment

**No logs appearing?**
- Check CloudWatch: `aws logs tail /aws/lambda/care-compass-dev --follow`
- Enable debug mode in lambda_handler.py

## Cleanup

Delete stack and all resources:
```bash
aws cloudformation delete-stack --stack-name care-compass-stack-dev
```

## Support

Check ARCHITECTURE.md for detailed component breakdown.
Check DEPLOYMENT_GUIDE.md for step-by-step setup.
