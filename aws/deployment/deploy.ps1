# PowerShell deployment script for CARE Compass AWS Lambda (Container Image)
# Uses Docker + AWS CLI (no SAM CLI required)
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
    [int]$LambdaTimeout = 300,

    [Parameter(Mandatory=$false)]
    [string]$SupabaseJwtSecret = ""
)

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "CARE Compass AWS Deployment" -ForegroundColor Cyan
Write-Host "(Container Image)" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$awsDir = Split-Path -Parent $scriptDir
$projectRoot = Split-Path -Parent $awsDir

Write-Host "`nEnvironment: $Environment" -ForegroundColor Yellow
Write-Host "AWS Profile: $AWSProfile" -ForegroundColor Yellow
Write-Host "AWS Region: $AWSRegion" -ForegroundColor Yellow

# ==================== Step 1: Validate Prerequisites ====================
Write-Host "`n[1/6] Validating prerequisites..." -ForegroundColor Cyan

# Check Docker
$dockerCheck = & docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "x Docker is not installed or not running" -ForegroundColor Red
    exit 1
}
Write-Host "  Docker: $dockerCheck" -ForegroundColor Gray

# Check AWS credentials
$ErrorActionPreference = "Continue"
$awsOutput = & aws sts get-caller-identity --profile $AWSProfile --region $AWSRegion 2>&1
$ErrorActionPreference = "Stop"

if ($LASTEXITCODE -ne 0) {
    Write-Host "x AWS credentials not configured" -ForegroundColor Red
    Write-Host "  Run: aws configure --profile $AWSProfile" -ForegroundColor Yellow
    exit 1
}

$sts = $awsOutput | ConvertFrom-Json
$accountId = $sts.Account
Write-Host "  AWS Account: $accountId" -ForegroundColor Gray
Write-Host "OK - Prerequisites valid" -ForegroundColor Green

# ==================== Step 2: Prepare Source Code ====================
Write-Host "`n[2/6] Preparing source code..." -ForegroundColor Cyan

$lambdaDir = Join-Path $projectRoot "aws/lambda"
$buildDir = Join-Path $lambdaDir "build"

# Clean previous build
if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# Copy source code into build dir (Docker will copy from here)
$srcDir = Join-Path $projectRoot "backend/src"
Copy-Item $srcDir (Join-Path $buildDir "src") -Recurse

$configDir = Join-Path $projectRoot "backend/config"
Copy-Item $configDir (Join-Path $buildDir "config") -Recurse

$mainFile = Join-Path $projectRoot "backend/main.py"
Copy-Item $mainFile (Join-Path $buildDir "main.py")

Write-Host "OK - Source code prepared" -ForegroundColor Green

# ==================== Step 3: Build Docker Image ====================
Write-Host "`n[3/6] Building Docker image..." -ForegroundColor Cyan

$ecrRepo = "care-compass-$Environment"
$imageTag = "latest"
$imageName = "${ecrRepo}:${imageTag}"

& docker build --platform linux/amd64 --provenance=false --no-cache -t $imageName -f (Join-Path $lambdaDir "Dockerfile") $lambdaDir

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Docker image built: $imageName" -ForegroundColor Green

# ==================== Step 4: Push to ECR ====================
Write-Host "`n[4/6] Pushing image to ECR..." -ForegroundColor Cyan

$ecrUri = "$accountId.dkr.ecr.$AWSRegion.amazonaws.com"
$fullImageUri = "$ecrUri/${ecrRepo}:${imageTag}"

# Create ECR repo if it doesn't exist
$ErrorActionPreference = "Continue"
& aws ecr describe-repositories --repository-names $ecrRepo --profile $AWSProfile --region $AWSRegion 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating ECR repository: $ecrRepo" -ForegroundColor Gray
    & aws ecr create-repository --repository-name $ecrRepo --profile $AWSProfile --region $AWSRegion 2>&1 | Out-Null
}
$ErrorActionPreference = "Stop"

# Login to ECR
Write-Host "  Logging in to ECR..." -ForegroundColor Gray
$loginPassword = & aws ecr get-login-password --profile $AWSProfile --region $AWSRegion
$loginPassword | docker login --username AWS --password-stdin $ecrUri

if ($LASTEXITCODE -ne 0) {
    Write-Host "x ECR login failed" -ForegroundColor Red
    exit 1
}

# Tag and push
Write-Host "  Pushing image to $fullImageUri ..." -ForegroundColor Gray
& docker tag $imageName $fullImageUri
& docker push $fullImageUri

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Docker push failed" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Image pushed to ECR" -ForegroundColor Green

# ==================== Step 5: Deploy CloudFormation ====================
Write-Host "`n[5/6] Deploying CloudFormation stack..." -ForegroundColor Cyan

$stackName = "care-compass-stack-$Environment"
$templatePath = Join-Path $projectRoot "aws/infrastructure/template.yaml"

Write-Host "  Stack: $stackName" -ForegroundColor Gray
Write-Host "  Image: $fullImageUri" -ForegroundColor Gray
Write-Host "  (This may take several minutes)" -ForegroundColor Gray

$ErrorActionPreference = "Continue"
$deployOutput = & aws cloudformation deploy --template-file $templatePath --stack-name $stackName --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --parameter-overrides "Environment=$Environment" "GoogleAPIKey=$GoogleApiKey" "LambdaMemory=$LambdaMemory" "LambdaTimeout=$LambdaTimeout" "SupabaseJwtSecret=$SupabaseJwtSecret" "ImageUri=$fullImageUri" --profile $AWSProfile --region $AWSRegion --no-fail-on-empty-changeset 2>&1
$deployExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

if ($deployExitCode -ne 0) {
    Write-Host "x Deployment failed" -ForegroundColor Red
    Write-Host "  Output: $deployOutput" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Deployment successful" -ForegroundColor Green

# ==================== Step 6: Retrieve Outputs ====================
Write-Host "`n[6/6] Retrieving deployment outputs..." -ForegroundColor Cyan

try {
    $outputs = aws cloudformation describe-stacks --stack-name $stackName --profile $AWSProfile --region $AWSRegion --query 'Stacks[0].Outputs' | ConvertFrom-Json

    Write-Host "`n==================================================" -ForegroundColor Cyan
    Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Cyan

    foreach ($output in $outputs) {
        Write-Host "`n$($output.OutputKey):" -ForegroundColor Yellow
        Write-Host "  $($output.OutputValue)" -ForegroundColor White
    }

    $outputFile = Join-Path $scriptDir "deployment-outputs-$Environment.json"
    $outputs | ConvertTo-Json | Set-Content $outputFile
    Write-Host "`nOutputs saved to: $outputFile" -ForegroundColor Green

} catch {
    Write-Host "x Error retrieving outputs: $_" -ForegroundColor Red
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "1. Update your Electron frontend API_BASE_URL with the API endpoint above"
Write-Host "2. Test: curl <api-endpoint>/health"
Write-Host "3. Monitor CloudWatch logs for any issues"