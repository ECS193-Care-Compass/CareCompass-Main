// chatbot-frontend/src/renderer/src/api.ts

//const API_BASE = 'http://localhost:8080';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:3000";

export const CHAT_ENDPOINT = `${API_BASE_URL}/chat`;


export async function sendChatMessage(message: string, sessionId: string) {
   const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
         sessionId,
         message,
         context: { anonymous: true } // Default context
      }),
   });
   
   if (!response.ok) throw new Error('Failed to reach backend');
   return response.json(); // Returns { reply, options, safety }
}