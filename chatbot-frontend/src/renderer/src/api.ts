// chatbot-frontend/src/renderer/src/api.ts
// API client for CARE Bot (FastAPI Backend)

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const DEBUG = import.meta.env.VITE_DEBUG === 'true';

// ==================== USER ID MANAGEMENT ====================

const USER_ID_STORAGE_KEY = 'care_bot_user_id';

/**
 * Generate a unique user ID based on timestamp
 */
function generateUserId(): string {
  return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get or create a persistent user ID for this device/browser
 */
export function getUserId(): string {
  let userId = localStorage.getItem(USER_ID_STORAGE_KEY);
  
  if (!userId) {
    userId = generateUserId();
    localStorage.setItem(USER_ID_STORAGE_KEY, userId);
    logDebug('Generated new user ID', userId);
  }
  
  return userId;
}

/**
 * Reset user ID (for testing or manual user switch)
 */
export function resetUserId(): void {
  localStorage.removeItem(USER_ID_STORAGE_KEY);
  logDebug('User ID reset');
}

// ==================== INTERFACES ====================

export interface ChatRequest {
  query: string;
  user_id?: string;
  scenario?: string;
}

export interface ChatResponse {
  response: string;
  is_crisis: boolean;
  num_docs_retrieved: number;
  scenario?: string;
  blocked?: boolean;
}

export interface CategoryInfo {
  id: string;
  name: string;
  description: string;
}

export interface CategoriesResponse {
  categories: CategoryInfo[];
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

// ==================== ENDPOINTS ====================

export interface VoiceResponse {
  user_transcript: string;
  bot_response: string;
  audio_base64: string;
  is_crisis: boolean;
  session_id: string;
}

const endpoints = {
  chat: `${API_BASE_URL}/chat`,
  voice: `${API_BASE_URL}/voice-chat`,
  clear: `${API_BASE_URL}/clear`,
  stats: `${API_BASE_URL}/stats`,
  health: `${API_BASE_URL}/health`,
  categories: `${API_BASE_URL}/categories`,
};

// ==================== HELPER FUNCTIONS ====================

function logDebug(message: string, data?: unknown): void {
  if (DEBUG) {
    console.log(`[DEBUG] ${message}`, data || '')
  }
}

const DEFAULT_TIMEOUT_MS = 60000; // 60 seconds

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text();
    logDebug(`API Error: ${response.status}`, error);
    throw new Error(`API Error: ${response.status} - ${error}`);
  }
  return response.json();
}

// ==================== API METHODS ====================

/**
 * Send a chat message to CARE Bot
 * @param query - User's message/question
 * @param scenario - Optional scenario category
 * @returns Chat response with bot reply and metadata
 */
export async function sendChatMessage(
  query: string,
  scenario?: string
): Promise<ChatResponse> {
  logDebug('sendChatMessage', { query, scenario });

  const request: ChatRequest = {
    query,
    user_id: getUserId(),
    scenario,
  };

  const response = await fetchWithTimeout(endpoints.chat, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<ChatResponse>(response);
}

/**
 * Send voice audio to CARE Bot
 * @param audioBlob - Blob of recorded audio
 * @param scenario - Optional scenario category
 */
export async function sendVoiceChat(
  audioBlob: Blob,
  scenario?: string,
  text?: string
): Promise<VoiceResponse> {
  console.log(`[API] sendVoiceChat called. Blob size: ${audioBlob.size} bytes, text: ${text ? "provided" : "none"}`);

  const formData = new FormData();
  // Converting Blob to File ensures standard multipart compatibility
  const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
  formData.append('audio', audioFile);
  
  formData.append('user_id', getUserId());
  if (scenario) formData.append('scenario', scenario);
  if (text) formData.append('text', text);

  try {
    const response = await fetchWithTimeout(endpoints.voice, {
      method: 'POST',
      body: formData,
    }, 90000); // 90 second timeout for voice (transcription + synthesis)
    console.log(`[API] voice-chat fetch response status: ${response.status}`);
    return handleResponse<VoiceResponse>(response);
  } catch (err) {
    console.error(`[API] voice-chat fetch FAILED:`, err);
    throw err;
  }
}

/**
 * Clear the conversation history
 */
export async function clearConversation(): Promise<{ status: string; message: string }> {
  logDebug('clearConversation');

  const response = await fetchWithTimeout(endpoints.clear, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return handleResponse(response);
}

/**
 * Get bot statistics
 */
export async function getStats(): Promise<StatsResponse> {
  logDebug('getStats');

  const response = await fetchWithTimeout(endpoints.stats, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return handleResponse<StatsResponse>(response);
}

/**
 * Check if backend is healthy
 */
export async function checkHealth(): Promise<{ status: string; message: string }> {
  logDebug('checkHealth');

  const response = await fetchWithTimeout(endpoints.health, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return handleResponse(response);
}

/**
 * Get available scenario categories
 */
export async function getCategories(): Promise<CategoriesResponse> {
  logDebug('getCategories');

  const response = await fetchWithTimeout(endpoints.categories, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return handleResponse<CategoriesResponse>(response);
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Get API base URL (useful for debugging)
 */
export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/**
 * Verify backend connectivity
 */
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
