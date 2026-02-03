import { loadConfig } from "../config";
import { ChatModelClient } from "../services/chatService";

const GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models";

export class GeminiClient implements ChatModelClient {
  async generateReply(message: string, contextSummary?: string): Promise<string> {
    const { geminiApiKey, geminiModel } = loadConfig();

    if (!geminiApiKey) {
      return "Thanks for sharing that. I can help you find support resources near you.";
    }

    const prompt = contextSummary
      ? `Context: ${contextSummary}\n\nUser: ${message}`
      : `User: ${message}`;

    const response = await fetch(`${GEMINI_API_URL}/${geminiModel}:generateContent?key=${geminiApiKey}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
      }),
    });

    if (!response.ok) {
      return "I am here with you. I can still share local resources while we retry chat generation.";
    }

    const data = (await response.json()) as {
      candidates?: Array<{
        content?: { parts?: Array<{ text?: string }> };
      }>;
    };

    return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ||
      "I hear you. Let us find the right next step together.";
  }
}

export function createGeminiClient(): ChatModelClient {
  return new GeminiClient();
}
