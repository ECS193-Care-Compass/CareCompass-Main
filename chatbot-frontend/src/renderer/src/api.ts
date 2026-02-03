// chatbot-frontend/src/renderer/src/api.ts

const API_BASE = 'http://localhost:8080';

export async function sendChatMessage(message: string, sessionId: string) {
   const response = await fetch(`${API_BASE}/chat`, {
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