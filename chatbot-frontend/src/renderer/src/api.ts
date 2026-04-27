// chatbot-frontend/src/renderer/src/api.ts
// API client for CARE Bot (FastAPI Backend)

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const DEBUG = import.meta.env.VITE_DEBUG === 'true';

// ── INTERFACES ────────────────────────────────────────────────────────────────

export interface ChatRequest {
  query: string;
  scenario?: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  is_crisis: boolean;
  num_docs_retrieved: number;
  scenario?: string;
  blocked?: boolean;
  processing_time_ms?: number;
}

export interface CategoryInfo {
  id: string;
  name: string;
  description: string;
}

export interface CategoriesResponse {
  categories: CategoryInfo[];
}

export interface VoiceResponse {
  user_transcript: string;
  bot_response: string;
  audio_base64: string;
  is_crisis: boolean;
  session_id: string;
}

export interface StatsResponse {
  vector_store: {
    document_count: number;
    collection_name: string;
  };
  retriever_top_k: number;
  llm_model: string;
  crisis_keywords: number;
  conversation_history: {
    total_turns: number;
    max_turns: number;
    messages: number;
  };
}

export interface DashboardResponse {
  server_metrics: {
    server_start_time: string;
    total_requests: number;
    total_errors: number;
    total_crisis_events: number;
    voice_requests: number;
    response_times: {
      count: number;
      avg_ms: number;
      min_ms: number;
      max_ms: number;
      p95_ms: number | null;
    };
    docs_retrieved: { avg: number };
    category_counts: Record<string, number>;
    crisis_rate: number;
    error_rate: number;
  };
  bot_stats: {
    llm_model: string;
    retriever_top_k: number;
    crisis_keywords: number;
    vector_store: { document_count: number };
  };
}

// ── ENDPOINTS ─────────────────────────────────────────────────────────────────

const endpoints = {
  chat: `${API_BASE_URL}/chat`,
  voiceChat: `${API_BASE_URL}/voice-chat`,
  clear: `${API_BASE_URL}/clear`,
  stats: `${API_BASE_URL}/stats`,
  health: `${API_BASE_URL}/health`,
  categories: `${API_BASE_URL}/categories`,
  adminDashboard: `${API_BASE_URL}/admin/dashboard`,
};

// ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

function logDebug(message: string, data?: unknown) {
  if (DEBUG) {
    console.log(`[DEBUG] ${message}`, data || '');
  }
}

function buildHeaders(authToken?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (authToken) {
    headers['Authorization'] = authToken;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text();
    logDebug(`API Error: ${response.status}`, error);
    throw new Error(`API Error: ${response.status} - ${error}`);
  }
  return response.json();
}

// ── API METHODS ───────────────────────────────────────────────────────────────

export async function sendChatMessage(
  query: string,
  scenario?: string,
  sessionId?: string,
  authToken?: string,
): Promise<ChatResponse> {
  logDebug('sendChatMessage', { query, scenario, sessionId });

  const request: ChatRequest = {
    query,
    scenario,
    session_id: sessionId,
  };

  const response = await fetch(endpoints.chat, {
    method: 'POST',
    headers: buildHeaders(authToken),
    body: JSON.stringify(request),
  });

  return handleResponse<ChatResponse>(response);
}

export async function sendVoiceChat(
  audioBlob: Blob,
  sessionId?: string,
  authToken?: string,
  scenario?: string,
): Promise<VoiceResponse> {
  logDebug('sendVoiceChat', { blobSize: audioBlob.size, sessionId });

  const formData = new FormData();
  const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
  formData.append('audio', audioFile);
  if (sessionId) formData.append('session_id', sessionId);
  if (scenario) formData.append('scenario', scenario);

  const headers: Record<string, string> = {};
  if (authToken) headers['Authorization'] = authToken;

  const response = await fetch(endpoints.voiceChat, {
    method: 'POST',
    headers,
    body: formData,
  });

  return handleResponse<VoiceResponse>(response);
}

export async function clearConversation(
  sessionId?: string,
  authToken?: string,
): Promise<{ status: string; message: string }> {
  logDebug('clearConversation', { sessionId });

  const headers = buildHeaders(authToken);
  if (sessionId) {
    headers['X-Session-ID'] = sessionId;
  }

  const response = await fetch(endpoints.clear, {
    method: 'POST',
    headers,
  });

  return handleResponse(response);
}

export async function getStats(): Promise<StatsResponse> {
  logDebug('getStats');

  const response = await fetch(endpoints.stats, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<StatsResponse>(response);
}

export async function checkHealth(): Promise<{ status: string; message: string }> {
  logDebug('checkHealth');

  const response = await fetch(endpoints.health, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse(response);
}

export async function getCategories(): Promise<CategoriesResponse> {
  logDebug('getCategories');

  const response = await fetch(endpoints.categories, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<CategoriesResponse>(response);
}

export async function getDashboardStats(): Promise<DashboardResponse> {
  logDebug('getDashboardStats');

  const response = await fetch(endpoints.adminDashboard, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<DashboardResponse>(response);
}

// ── UTILITY FUNCTIONS ─────────────────────────────────────────────────────────

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export async function verifyBackendConnection(): Promise<boolean> {
  try {
    const health = await checkHealth();
    logDebug('Backend health check', health);
    return health.status === 'ok';
  } catch (error) {
    logDebug('Backend connection failed', error);
    return false;
  }
}