"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.GeminiClient = void 0;
exports.createGeminiClient = createGeminiClient;
const config_1 = require("../config");
const GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models";
class GeminiClient {
    async generateReply(message, contextSummary) {
        const { geminiApiKey, geminiModel } = (0, config_1.loadConfig)();
        if (!geminiApiKey) {
            return "Thanks for sharing that. I can help you find support resources near you.";
        }
        const prompt = contextSummary
            ? `Context: ${contextSummary}\n\nUser: ${message}`
            : `User: ${message}`;
        let response;
        try {
            response = await fetch(`${GEMINI_API_URL}/${geminiModel}:generateContent?key=${geminiApiKey}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    contents: [{ parts: [{ text: prompt }] }],
                }),
            });
        }
        catch (error) {
            console.error("Gemini API request failed:", error);
            return "I am here with you. I can still share local resources while we retry chat generation.";
        }
        if (!response.ok) {
            const errorBody = await response.text().catch(() => "");
            console.error("Gemini API error:", {
                status: response.status,
                statusText: response.statusText,
                body: errorBody,
            });
            return "I am here with you. I can still share local resources while we retry chat generation.";
        }
        const data = (await response.json());
        return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ||
            "I hear you. Let us find the right next step together.";
    }
}
exports.GeminiClient = GeminiClient;
function createGeminiClient() {
    return new GeminiClient();
}
