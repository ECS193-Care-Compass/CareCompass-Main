// chatbot-frontend/src/renderer/src/api.ts
// API client for CARE Bot (FastAPI or AWS Lambda backend)

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const DEBUG = import.meta.env.VITE_DEBUG === 'true';

// ==================== INTERFACES ====================

export interface ChatRequest {
  query: string;
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

const endpoints = {
  chat: `${API_BASE_URL}/chat`,
  clear: `${API_BASE_URL}/clear`,
  stats: `${API_BASE_URL}/stats`,
  health: `${API_BASE_URL}/health`,
  categories: `${API_BASE_URL}/categories`,
};

// ==================== HELPER FUNCTIONS ====================

function logDebug(message: string, data?: any) {
  if (DEBUG) {
    console.log(`[DEBUG] ${message}`, data || '');
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
 * @param scenario - Optional scenario category (immediate_followup, mental_health, etc.)
 * @returns Chat response with bot reply and metadata
 */
export async function sendChatMessage(
  query: string,
  scenario?: string
): Promise<ChatResponse> {
  logDebug('sendChatMessage', { query, scenario });

  const request: ChatRequest = {
    query,
    scenario,
  };

  const response = await fetch(endpoints.chat, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<ChatResponse>(response);
}

/**
 * Clear the conversation history
 */
export async function clearConversation(): Promise<{ status: string; message: string }> {
  logDebug('clearConversation');

  const response = await fetch(endpoints.clear, {
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

  const response = await fetch(endpoints.stats, {
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

  const response = await fetch(endpoints.health, {
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

  const response = await fetch(endpoints.categories, {
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