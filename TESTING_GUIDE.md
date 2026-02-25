# CARE Compass - Frontend & Lambda Integration Testing Guide

## Part 1: Start & Test Frontend Electron App

### Step 1: Install Frontend Dependencies
```powershell
cd C:\Users\steph\CARE-COMPASS\CareCompass\chatbot-frontend
npm install
```

### Step 2: Set Lambda Endpoint
Create file `.env.local` in `chatbot-frontend/`:
```
VITE_API_BASE_URL=https://YOUR-LAMBDA-URL
VITE_DEBUG=true
```

**To find your Lambda URL:**
1. AWS Console → Lambda → `care-compass-dev` 
2. Click **Function URL** (if not visible, create one: Configuration → Function URL → Create)
3. Copy the HTTPS URL (looks like: `https://xxxxxx.lambda-url.us-east-1.on.aws`)

### Step 3: Start Frontend in Development Mode
```powershell
cd chatbot-frontend
npm run dev
```

Electron window will open with the chat interface.

### Step 4: Test Chat Interaction
1. Type a message: "I'm experiencing anxiety after a traumatic event"
2. Click **Send**
3. Response should come from Lambda
4. **Check S3 for logs** (see Part 3)

---

## Part 2: Build Electron App (Optional)

### For Windows:
```powershell
cd chatbot-frontend
npm run build:win
```

The `.exe` installer will be in `chatbot-frontend/dist/`.

### For macOS:
```powershell
npm run build:mac
```

---

## Part 3: Verify Logging to S3

After sending a chat message, check if Lambda logged it:

### Check S3 Logs via AWS Console:
1. Go to **S3** → `care-compass-documents-432732422396-dev`
2. Look for: **`logs/interactions/`** folder
3. You'll see JSON files with timestamps:
   ```
   logs/interactions/2026-02-24/2026-02-24T01:30:45.123456.json
   ```

### Check via CLI:
```powershell
aws s3 ls s3://care-compass-documents-432732422396-dev/logs/interactions/ --recursive

aws s3 cp s3://care-compass-documents-432732422396-dev/logs/interactions/2026-02-24/2026-02-24T01:30:45.json - | type
```

### Each Log Entry Contains:
```json
{
  "timestamp": "2026-02-24T01:30:45.123456",
  "status": "chat_request",
  "method": "POST",
  "path": "/chat",
  "request_id": "req-12345",
  "response_status": 200,
  "body": "[redacted]"  // Hidden for privacy
}
```

---

## Part 4: Full Testing Workflow

### Test 1: Health Check
```powershell
$payload = @{"requestContext"=@{"http"=@{"method"="GET"}};"rawPath"="/health"} | ConvertTo-Json
aws lambda invoke --function-name care-compass-dev --payload $payload --cli-binary-format raw-in-base64-out --profile default --region us-east-1 response.json
type response.json
```

**Expected:** `{"statusCode":200,"body":"{\"status\":\"ok\",\"message\":\"CARE Bot API is running\"}"}`

### Test 2: Get Categories
```powershell
$payload = @{"requestContext"=@{"http"=@{"method"="GET"}};"rawPath"="/categories"} | ConvertTo-Json
aws lambda invoke --function-name care-compass-dev --payload $payload --cli-binary-format raw-in-base64-out --profile default --region us-east-1 response.json
type response.json
```

**Expected:** List of 5 category scenarios (immediate_followup, mental_health, etc.)

### Test 3: Chat Request (Will Create S3 Log)
```powershell
$payload = @{
    "requestContext"=@{"http"=@{"method"="POST"}}
    "rawPath"="/chat"
    "body"='{"query":"What support is available?","scenario":"mental_health"}'
} | ConvertTo-Json

aws lambda invoke --function-name care-compass-dev --payload $payload --cli-binary-format raw-in-base64-out --profile default --region us-east-1 response.json
type response.json

# Check S3 for the logged interaction
aws s3 ls s3://care-compass-documents-432732422396-dev/logs/interactions/ --recursive
```

### Test 4: Check Logs in CloudWatch
```powershell
aws logs filter-log-events --log-group-name /aws/lambda/care-compass-dev --limit 20
```

---

## Part 5: How Data Flows

```
┌─────────────────┐
│   Electron      │
│   Frontend      │  (Chat UI)
└────────┬────────┘
         │ sends message
         │
         ▼
┌─────────────────────────────────┐
│   AWS Lambda                    │
│   (care-compass-dev)            │  ← Processes request
│   • Receives chat query         │
│   • Calls CAREBot logic         │
│   • Returns response            │
└────────┬────────────────────────┘
         │ logs interaction
         │
         ▼
┌──────────────────────────────────────┐
│   S3 Documents Bucket                │
│   (care-compass-documents-...dev)    │  ← Logs every interaction
│   logs/interactions/YYYY-MM-DD/      │
│   ├── timestamp1.json               │
│   ├── timestamp2.json               │
│   └── ...                            │
└──────────────────────────────────────┘
```

---

## Part 6: View Frontend Code

**Chat Component:**
```
C:\Users\steph\CARE-COMPASS\CareCompass\chatbot-frontend\src\renderer\src\Chat.tsx
```

**API Client:**
```
C:\Users\steph\CARE-COMPASS\CareCompass\chatbot-frontend\src\renderer\src\api.ts
```

---

## Troubleshooting

### Frontend can't connect to Lambda?
- Check VITE_API_BASE_URL env variable
- Verify Lambda URL is publicly accessible (Function URL should be created)
- Check CORS headers in lambda_handler.py (they're set to `*`)

### S3 logs not appearing?
- Check Lambda execution role has S3 permission
- Verify S3_DOCUMENTS_BUCKET env variable is set
- Check CloudWatch logs for S3 errors

### Lambda returns "Failed to import CAREBot"?
- `/health` endpoint works (doesn't need CAREBot)
- `/chat` endpoint fails (needs CAREBot imported)
- This is expected until CAREBot code is properly deployed

---

## Next Steps

1. ✅ Frontend running
2. ✅ Lambda receiving requests
3. ✅ S3 logging interactions
4. 🔄 **TODO:** Connect CAREBot logic to Lambda
5. 🔄 **TODO:** Deploy to production

