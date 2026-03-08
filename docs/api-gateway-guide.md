# Connecting a Frontend to the CARE Compass API

## API Gateway URL

```
https://7i51eh59p0.execute-api.us-east-1.amazonaws.com/dev
```

This is the backend. It runs on AWS Lambda and handles all chat logic, crisis detection, and document retrieval.

## Available Endpoints

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/health` | — | Health check |
| POST | `/chat` | `{"query": "...", "session_id": "..."}` | Send a message, get a response |
| POST | `/clear` | — | Clear conversation history |
| GET | `/categories` | — | List available help categories |
| GET | `/stats` | — | Bot statistics |

## How to Call the API

### Basic Chat Request

```javascript
const API_URL = "https://7i51eh59p0.execute-api.us-east-1.amazonaws.com/dev";

const response = await fetch(`${API_URL}/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: "What is trauma-informed care?",
    session_id: "guest-abc123"  // unique per user session
  })
});

const data = await response.json();
// data.response    → bot's reply (string)
// data.is_crisis   → whether crisis was detected (boolean)
// data.num_docs_retrieved → number of documents used (number)
```

### With Authentication (Supabase)

```javascript
const response = await fetch(`${API_URL}/chat`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${supabaseSession.access_token}`
  },
  body: JSON.stringify({
    query: "How do I find a counselor?"
  })
});
```

When an `Authorization` header is provided, the backend extracts the user ID from the JWT and uses it as the session ID. No need to pass `session_id` in the body.

### With Scenario Filtering

```javascript
const response = await fetch(`${API_URL}/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: "What STI tests should I get?",
    session_id: "guest-abc123",
    scenario: "immediate_followup"  // filters retrieval to medical docs
  })
});
```

Available scenarios: `immediate_followup`, `mental_health`, `practical_social`, `legal_advocacy`, `delayed_ambivalent`

### Clear Conversation

```javascript
// Guest user
await fetch(`${API_URL}/clear`, {
  method: "POST",
  headers: { "X-Session-ID": "guest-abc123" }
});

// Authenticated user
await fetch(`${API_URL}/clear`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` }
});
```

## Response Format

```json
{
  "response": "Bot's reply text here...",
  "is_crisis": false,
  "num_docs_retrieved": 3,
  "scenario": null,
  "blocked": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | The bot's reply |
| `is_crisis` | boolean | `true` if crisis language was detected (keywords or AI assessment) |
| `num_docs_retrieved` | number | How many reference documents were used for context |
| `scenario` | string/null | The scenario category used, if any |
| `blocked` | boolean | `true` if the response was blocked by safety filters |

## Connecting from Any Frontend

### React / Next.js (Vercel)

```jsx
const [messages, setMessages] = useState([]);
const sessionId = useRef(`guest-${crypto.randomUUID()}`);

async function sendMessage(query) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId.current })
  });
  const data = await res.json();

  setMessages(prev => [
    ...prev,
    { role: "user", text: query },
    { role: "bot", text: data.response, is_crisis: data.is_crisis }
  ]);
}
```

### Plain HTML / Vanilla JS

```html
<input id="input" placeholder="Type a message..." />
<button onclick="send()">Send</button>
<div id="chat"></div>

<script>
const API_URL = "https://7i51eh59p0.execute-api.us-east-1.amazonaws.com/dev";
const sessionId = "guest-" + crypto.randomUUID();

async function send() {
  const query = document.getElementById("input").value;
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId })
  });
  const data = await res.json();
  document.getElementById("chat").innerHTML += `<p><b>You:</b> ${query}</p>`;
  document.getElementById("chat").innerHTML += `<p><b>Bot:</b> ${data.response}</p>`;
}
</script>
```

### Mobile (React Native / Flutter)

Same HTTP calls — just replace `fetch` with your platform's HTTP client. The API is a standard REST API.

## CORS

The API allows requests from any origin (`Access-Control-Allow-Origin: *`). For production, you may want to restrict this to your frontend domain.

## Session Management

- **Guest users**: Generate a unique `session_id` on the frontend (e.g., `guest-<uuid>`) and send it with every request. Conversation history auto-expires after 30 minutes.
- **Authenticated users**: Send a Supabase JWT in the `Authorization` header. The backend extracts the user ID as the session ID. History persists longer.

## Rate Limits

- Lambda concurrency: 1000 (AWS default)
- Gemini API: depends on your Google API key tier
- No rate limiting on API Gateway by default (add a usage plan for production)