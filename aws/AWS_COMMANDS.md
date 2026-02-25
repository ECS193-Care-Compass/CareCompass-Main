# AWS CLI Cheat Sheet for CARE Compass

## Common Commands

### CloudFormation

```bash
# Validate template
aws cloudformation validate-template --template-body file://aws/infrastructure/template.yaml

# Describe stack
aws cloudformation describe-stacks --stack-name care-compass-stack-dev

# Get stack outputs
aws cloudformation describe-stacks --stack-name care-compass-stack-dev \
  --query 'Stacks[0].Outputs' --output table

# Delete stack
aws cloudformation delete-stack --stack-name care-compass-stack-dev

# Wait for stack deletion
aws cloudformation wait stack-delete-complete --stack-name care-compass-stack-dev
```

### Lambda

```bash
# Get function info
aws lambda get-function --function-name care-compass-dev

# Update function code
aws lambda update-function-code --function-name care-compass-dev \
  --zip-file fileb://lambda_function.zip

# Invoke function
aws lambda invoke --function-name care-compass-dev \
  --payload '{"httpMethod":"GET","path":"/health"}' response.json

# View concurrent executions
aws lambda get-provisioned-concurrency-config --function-name care-compass-dev

# Set reserved concurrency
aws lambda put-function-concurrency --function-name care-compass-dev \
  --reserved-concurrent-executions 10

# View environment variables
aws lambda get-function-configuration --function-name care-compass-dev \
  --query 'Environment.Variables' --output table

# Update environment variables
aws lambda update-function-configuration --function-name care-compass-dev \
  --environment Variables={GOOGLE_API_KEY=new_key}
```

### S3

```bash
# List buckets
aws s3 ls

# List objects in bucket
aws s3 ls s3://care-compass-documents-{account-id}-dev/

# Upload file
aws s3 cp /path/to/file.pdf s3://care-compass-documents-{account-id}-dev/

# Download file
aws s3 cp s3://care-compass-documents-{account-id}-dev/file.pdf ./file.pdf

# Sync directory
aws s3 sync /path/to/directory s3://care-compass-documents-{account-id}-dev/

# Remove file
aws s3 rm s3://care-compass-documents-{account-id}-dev/file.pdf

# Remove all files
aws s3 rm s3://care-compass-documents-{account-id}-dev --recursive

# Get object info
aws s3api head-object --bucket care-compass-documents-{account-id}-dev \
  --key file.pdf

# Create signed URL (valid for 1 hour)
aws s3 presign s3://care-compass-documents-{account-id}-dev/file.pdf \
  --expires-in 3600
```

### CloudWatch Logs

```bash
# List log groups
aws logs describe-log-groups

# View logs
aws logs tail /aws/lambda/care-compass-dev

# View logs with follow
aws logs tail /aws/lambda/care-compass-dev --follow

# Filter errors
aws logs tail /aws/lambda/care-compass-dev --grep "ERROR"

# Get specific log entries
aws logs filter-log-events --log-group-name /aws/lambda/care-compass-dev \
  --start-time $(date -d '1 hour ago' +%s)000

# Set retention policy
aws logs put-retention-policy --log-group-name /aws/lambda/care-compass-dev \
  --retention-in-days 7

# Delete log group
aws logs delete-log-group --log-group-name /aws/lambda/care-compass-dev
```

### IAM

```bash
# Get current user
aws sts get-caller-identity

# List users
aws iam list-users

# Get user permissions
aws iam get-user-policy --user-name USERNAME --policy-name POLICY_NAME

# List roles
aws iam list-roles

# Get role
aws iam get-role --role-name care-compass-lambda-role
```

### API Gateway

```bash
# List APIs
aws apigateway get-rest-apis

# Get API details
aws apigateway get-rest-api --rest-api-id {api-id}

# Get stages
aws apigateway get-stages --rest-api-id {api-id}
```

### Cost Management

```bash
# Estimate costs for specific resources
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity DAILY --metrics "UnblendedCost"

# Get lambda costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity DAILY --metrics "UnblendedCost" \
  --filter file://lambda-filter.json
```

---

## Useful Aliases

Add to `.bashrc` or `.zshrc`:

```bash
# Lambda shortcuts
alias lambda-logs='aws logs tail /aws/lambda/care-compass-dev --follow'
alias lambda-health='curl -s https://xxxxx.lambda-url.us-east-1.on.aws/health | jq'
alias lambda-stats='curl -s https://xxxxx.lambda-url.us-east-1.on.aws/stats | jq'

# S3 shortcuts
alias s3-docs='aws s3 ls s3://care-compass-documents-{account-id}-dev/'
alias s3-upload='aws s3 sync . s3://care-compass-documents-{account-id}-dev/'

# Stack shortcuts
alias cf-outputs='aws cloudformation describe-stacks --stack-name care-compass-stack-dev --query "Stacks[0].Outputs" --output table'
alias cf-delete='aws cloudformation delete-stack --stack-name care-compass-stack-dev'

# General
alias aws-whoami='aws sts get-caller-identity'
alias aws-region='echo $AWS_REGION'
```

---

## Troubleshooting Commands

```bash
# Check Lambda metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-02-01T23:59:59Z --period 86400 \
  --statistics Sum --dimensions Name=FunctionName,Value=care-compass-dev

# Check S3 bucket size
aws s3 ls s3://care-compass-documents-{account-id}-dev --recursive --summarize

# Get API endpoint
aws apigateway get-rest-apis --query 'items[?name==`care-compass-api-dev`]' --output table

# Validate JSON in S3
aws s3api get-object --bucket care-compass-vectordb-{account-id}-dev \
  --key config.json - | jq

# Check stack events (for deployment issues)
aws cloudformation describe-stack-events --stack-name care-compass-stack-dev \
  --query 'StackEvents[0:10]' --output table
```

---

## Batch Operations

### Upload Multiple Files

```bash
for file in /path/to/documents/*.pdf; do
  aws s3 cp "$file" s3://care-compass-documents-{account-id}-dev/
done
```

### Delete Multiple Objects

```bash
aws s3 ls s3://care-compass-documents-{account-id}-dev/ | \
  awk '{print $4}' | \
  xargs -I {} aws s3 rm s3://care-compass-documents-{account-id}-dev/{}
```

### Backup Vector Store

```bash
# Download entire vectordb bucket
aws s3 sync s3://care-compass-vectordb-{account-id}-dev/ ./vectordb-backup/

# Compress and upload to archive
tar -czf vectordb-backup.tar.gz vectordb-backup/
aws s3 cp vectordb-backup.tar.gz s3://care-compass-vectordb-{account-id}-dev/backups/
```

---

## Performance Tips

1. **Profile**: Add `--profile dev` to commands if using multiple AWS profiles
2. **Region**: Add `--region us-east-1` to specify region
3. **Output**: Use `--output table`, `--output json`, or `--output text`
4. **Query**: Use `--query` to filter output (supports JMESPath)
5. **Pagination**: Use `--max-items` and `--starting-token` for large results

Example:
```bash
aws logs tail /aws/lambda/care-compass-dev \
  --profile prod \
  --region us-west-2 \
  --output json \
  --follow
```

---

## References

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/latest/userguide/)
- [JMESPath Query Language](https://jmespath.org/)
- [AWS CLI Cheat Sheet](https://aws.amazon.com/cli/)
