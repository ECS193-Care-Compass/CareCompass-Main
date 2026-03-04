# PowerShell deployment script for CARE Compass AWS Lambda + S3
# Usage: .\deploy.ps1 -Environment dev -GoogleApiKey "xxx"

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "prod")]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$GoogleApiKey,
    
    [Parameter(Mandatory=$false)]
    [string]$AWSProfile = "default",
    
    [Parameter(Mandatory=$false)]
    [string]$AWSRegion = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [int]$LambdaMemory = 1024,
    
    [Parameter(Mandatory=$false)]
    [int]$LambdaTimeout = 300
)

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "CARE Compass AWS Deployment" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$awsDir = Split-Path -Parent $scriptDir
$projectRoot = Split-Path -Parent $awsDir

Write-Host "`nEnvironment: $Environment" -ForegroundColor Yellow
Write-Host "AWS Profile: $AWSProfile" -ForegroundColor Yellow
Write-Host "AWS Region: $AWSRegion" -ForegroundColor Yellow
Write-Host "Lambda Memory: ${LambdaMemory}MB" -ForegroundColor Yellow
Write-Host "Lambda Timeout: ${LambdaTimeout}s" -ForegroundColor Yellow

# Validate AWS credentials
Write-Host "`n[1/5] Validating AWS credentials..." -ForegroundColor Cyan

$awsOutput = & aws sts get-caller-identity --profile $AWSProfile --region $AWSRegion 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Error: AWS credentials not configured or invalid" -ForegroundColor Red
    Write-Host "  Run: aws configure" -ForegroundColor Yellow
    Write-Host "  Error Details: $awsOutput" -ForegroundColor Red
    exit 1
}

Write-Host "✓ AWS credentials valid" -ForegroundColor Green

# Parse the JSON output to extract account ID
try {
    $sts = $awsOutput | ConvertFrom-Json
    $accountId = $sts.Account
    if (-not $accountId) {
        throw "Could not extract Account ID from AWS response"
    }
} catch {
    Write-Host "✗ Error parsing AWS response: $_" -ForegroundColor Red
    Write-Host "  Response was: $awsOutput" -ForegroundColor Red
    exit 1
}

Write-Host "  Account ID: $accountId" -ForegroundColor Gray

# Validate template
Write-Host "`n[2/5] Validating CloudFormation template..." -ForegroundColor Cyan
$templatePath = Join-Path $projectRoot "aws/infrastructure/template.yaml"

$templateCheck = & aws cloudformation validate-template `
    --template-body "file://$templatePath" `
    --profile $AWSProfile `
    --region $AWSRegion 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Template validation failed" -ForegroundColor Red
    Write-Host "  Error: $templateCheck" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Template is valid" -ForegroundColor Green

# Build Lambda package
Write-Host "`n[3/5] Building Lambda deployment package..." -ForegroundColor Cyan
$lambdaDir = Join-Path $projectRoot "aws/lambda"
$buildDir = Join-Path $lambdaDir "build"

# Clean previous build
if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
    Write-Host "  Cleaned previous build" -ForegroundColor Gray
}

# Create build directory
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# Copy Lambda handler and modules
Write-Host "  Copying Lambda handler..." -ForegroundColor Gray
Copy-Item (Join-Path $lambdaDir "lambda_handler.py") (Join-Path $buildDir "lambda_handler.py")
Copy-Item (Join-Path $lambdaDir "s3_manager.py") (Join-Path $buildDir "s3_manager.py")

# Copy source code
Write-Host "  Copying source code..." -ForegroundColor Gray
$srcDir = Join-Path $projectRoot "backend/src"
Copy-Item $srcDir (Join-Path $buildDir "src") -Recurse

$configDir = Join-Path $projectRoot "backend/config"
Copy-Item $configDir (Join-Path $buildDir "config") -Recurse

$mainFile = Join-Path $projectRoot "backend/main.py"
Copy-Item $mainFile (Join-Path $buildDir "main.py")

# Install dependencies
Write-Host "  Installing Python dependencies..." -ForegroundColor Gray
$reqFile = Join-Path $lambdaDir "requirements.txt"
& pip install -r $reqFile -t $buildDir --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Lambda package built successfully" -ForegroundColor Green

# Deploy with SAM
Write-Host "`n[4/5] Deploying with AWS SAM..." -ForegroundColor Cyan

$stackName = "care-compass-stack-$Environment"
$samCache = Join-Path $buildDir ".aws-sam"
$s3Bucket = "care-compass-deploy-$accountId-$Environment"

# Create S3 bucket for SAM artifacts if it doesn't exist
$s3BucketCheck = & aws s3 ls "s3://$s3Bucket" --profile $AWSProfile --region $AWSRegion 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating S3 bucket for SAM artifacts..." -ForegroundColor Gray
    & aws s3 mb "s3://$s3Bucket" --profile $AWSProfile --region $AWSRegion 2>&1 | Out-Null
}

# Run SAM deploy
Write-Host "  Running SAM deploy..." -ForegroundColor Gray

$samCommand = @(
    "sam", "deploy",
    "--template-file", $templatePath,
    "--stack-name", $stackName,
    "--s3-bucket", $s3Bucket,
    "--capabilities", "CAPABILITY_IAM",
    "--profile", $AWSProfile,
    "--region", $AWSRegion,
    "--parameter-overrides",
    "Environment=$Environment",
    "GoogleAPIKey=$GoogleApiKey",
    "LambdaMemory=$LambdaMemory",
    "LambdaTimeout=$LambdaTimeout",
    "--no-fail-on-empty-changeset",
    "--no-confirm-changeset"
)

# Debug: show what we're about to run
Write-Host "  Stack Name: $stackName" -ForegroundColor Gray
Write-Host "  Template: $templatePath" -ForegroundColor Gray
Write-Host "  S3 Bucket: $s3Bucket" -ForegroundColor Gray

& @samCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ SAM deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ SAM deployment successful" -ForegroundColor Green

# Get stack outputs
Write-Host "`n[5/5] Retrieving deployment outputs..." -ForegroundColor Cyan
try {
    $outputs = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --profile $AWSProfile `
        --region $AWSRegion `
        --query 'Stacks[0].Outputs' | ConvertFrom-Json
    
    Write-Host "`n" + "="*50 -ForegroundColor Cyan
    Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
    Write-Host "="*50 -ForegroundColor Cyan
    
    foreach ($output in $outputs) {
        Write-Host "`n$($output.OutputKey):" -ForegroundColor Yellow
        Write-Host "  $($output.OutputValue)" -ForegroundColor White
    }
    
    # Save outputs to file
    $outputFile = Join-Path $scriptDir "deployment-outputs-$Environment.json"
    $outputs | ConvertTo-Json | Set-Content $outputFile
    Write-Host "`nOutputs saved to: $outputFile" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Error retrieving outputs: $_" -ForegroundColor Red
}

Write-Host "`n" + "="*50 -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "="*50 -ForegroundColor Cyan
Write-Host "1. Update your Electron frontend with the API endpoint"
Write-Host "2. Test the /health endpoint in your browser"
Write-Host "3. Upload reference documents to S3 (optional)"
Write-Host "4. Monitor CloudWatch logs for any issues"
