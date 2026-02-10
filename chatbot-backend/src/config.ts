export type AppConfig = {
  port: number;
  corsOrigin: string;
  nodeEnv: "development" | "test" | "production";
  geminiApiKey?: string;
  geminiModel: string;
};

export function loadConfig(): AppConfig {
  const port = Number(process.env.PORT || 8080);
  const corsOrigin = process.env.CORS_ORIGIN || "*";
  const nodeEnv = (process.env.NODE_ENV || "development") as AppConfig["nodeEnv"];

  const geminiApiKey = process.env.GEMINI_API_KEY || undefined;
  const geminiModel = process.env.GEMINI_MODEL || "gemini-1.5-flash";

  return { port, corsOrigin, nodeEnv, geminiApiKey, geminiModel };
}
