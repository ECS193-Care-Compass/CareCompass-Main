"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadConfig = loadConfig;
function loadConfig() {
    const port = Number(process.env.PORT || 8080);
    const corsOrigin = process.env.CORS_ORIGIN || "*";
    const nodeEnv = (process.env.NODE_ENV || "development");
    const geminiApiKey = process.env.GEMINI_API_KEY || undefined;
    const geminiModel = process.env.GEMINI_MODEL || "gemini-1.5-flash";
    return { port, corsOrigin, nodeEnv, geminiApiKey, geminiModel };
}
