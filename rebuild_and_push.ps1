$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$lambdaDir = Join-Path $projectRoot "aws\lambda"
$buildDir = Join-Path $lambdaDir "build"

Write-Host "Cleaning build dir..." -ForegroundColor Cyan
Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $buildDir | Out-Null

Write-Host "Copying source..." -ForegroundColor Cyan
Copy-Item (Join-Path $projectRoot "backend\src") (Join-Path $buildDir "src") -Recurse
Copy-Item (Join-Path $projectRoot "backend\config") (Join-Path $buildDir "config") -Recurse
Copy-Item (Join-Path $projectRoot "backend\main.py") (Join-Path $buildDir "main.py")

Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build --platform linux/amd64 --provenance=false --no-cache `
    -t care-compass-dev:latest `
    -f (Join-Path $lambdaDir "Dockerfile") `
    $lambdaDir

Write-Host "Logging in to ECR..." -ForegroundColor Cyan
$loginPassword = aws ecr get-login-password --profile carecompass --region us-east-1
$loginPassword | docker login --username AWS --password-stdin 432732422396.dkr.ecr.us-east-1.amazonaws.com

Write-Host "Tagging and pushing..." -ForegroundColor Cyan
docker tag care-compass-dev:latest 432732422396.dkr.ecr.us-east-1.amazonaws.com/care-compass-dev:latest
docker push 432732422396.dkr.ecr.us-east-1.amazonaws.com/care-compass-dev:latest

Write-Host "Updating Lambda..." -ForegroundColor Cyan
aws lambda update-function-code `
    --function-name care-compass-dev `
    --image-uri 432732422396.dkr.ecr.us-east-1.amazonaws.com/care-compass-dev:latest `
    --profile carecompass

Write-Host "Done! Waiting for Lambda update..." -ForegroundColor Green
do {
    Start-Sleep -Seconds 3
    $status = aws lambda get-function --function-name care-compass-dev --profile carecompass --query "Configuration.LastUpdateStatus" --output text
    Write-Host "  Status: $status"
} while ($status -eq "InProgress")

Write-Host "Lambda is ready." -ForegroundColor Green
