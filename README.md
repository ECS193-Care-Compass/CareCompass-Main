# CareCompass

## Quick Start

Prereqs:
- Node.js `>=20` (uses built-in `fetch`)
- npm

Setup:
```bash
cd backend
npm install
cp .env.example .env
```

Fill in `.env`:
- `GEMINI_API_KEY` (required for real Gemini responses)
- `PORT` (default `8080`)
- `CORS_ORIGIN` (default frontend origin)
- `GEMINI_MODEL` (default `gemini-1.5-flash`)

Run:
```bash
npm run dev
```

Build/start:
```bash
npm run build
npm run start
```

## Current Backend Status

Implemented:
- Express server with middleware (`helmet`, `cors`, `morgan`, JSON parsing)
- Endpoints: `GET /health`, `POST /chat`, `POST /consent`, `GET /resources`
- Zod request validation
- In-memory repositories for session/resource data
- Gemini client integration with graceful fallback if key is missing
- Basic safety flag detection for crisis terms

Important current limitations:
- Persistence is in-memory only (data resets on restart)
- No auth/rate-limiting yet
- No automated test suite yet
- RAG is scaffolded but not connected

## API Contract (Current)

- `GET /health` -> `{ status: "ok" }`
- `POST /chat`
  - body: `{ sessionId, message, context?: { zip?, helpType?, anonymous? } }`
  - returns: `{ reply, options, safety }`
- `POST /consent`
  - body: `{ sessionId, consentToStore, consentToReminders? }`
  - returns: `{ ok: true }`
- `GET /resources?zip=#####&category=medical|mental_health|legal|hotline|advocacy`
  - returns: `{ resources: Resource[] }`

## Where To Modify What

- Server wiring / composition root: `backend/src/server.ts`
- Request/response schemas: `backend/src/types/api.ts`
- Chat orchestration: `backend/src/services/chatService.ts`
- Gemini integration: `backend/src/clients/geminiClient.ts`
- Resource filtering: `backend/src/services/resourcesService.ts`
- Consent persistence logic: `backend/src/services/consentService.ts`
- Storage adapters:
  - Session repo: `backend/src/repositories/sessionRepo.ts`
  - Resources repo: `backend/src/repositories/resourcesRepo.ts`
  - In-memory impls in `backend/src/repositories/memory/`

## RAG Integration Prep (For Partner)

Scaffold is here:
- `backend/src/services/ragPromptContextBuilder.ts`
- `PromptContextBuilder` interface in `backend/src/services/chatService.ts`

To wire RAG in:
1. Implement retrieval logic inside `RagPromptContextBuilder.build(...)`.
2. Update `backend/src/server.ts` chat service creation to inject it:
```ts
const chatService = createChatService({
  sessionRepo,
  modelClient: createGeminiClient(),
  promptContextBuilder: new RagPromptContextBuilder(),
});
```
3. Keep output small/clean (context summary + citations if needed) before passing to Gemini.

## Suggested Next Tasks

1. Replace in-memory repos with DynamoDB-backed repos.
2. Add automated API tests (health/chat/consent/resources).
3. Add auth + rate limiting for production safety.
4. Add structured logging + request IDs.
5. Document deployment for Lambda/EC2 split.
