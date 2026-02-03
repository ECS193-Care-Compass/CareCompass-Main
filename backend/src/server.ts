import cors from "cors";
import express from "express";
import helmet from "helmet";
import morgan from "morgan";

import { createGeminiClient } from "./clients/geminiClient";
import { loadConfig } from "./config";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler";
import { createResourcesRepo } from "./repositories/resourcesRepo";
import { createSessionRepo } from "./repositories/sessionRepo";
import { createChatRouter } from "./routes/chat";
import { createConsentRouter } from "./routes/consent";
import healthRouter from "./routes/health";
import { createResourcesRouter } from "./routes/resources";
import { createChatService } from "./services/chatService";
import { createConsentService } from "./services/consentService";
import { createResourcesService } from "./services/resourcesService";

export function createServer() {
  const app = express();
  const config = loadConfig();
  const sessionRepo = createSessionRepo();
  const resourcesRepo = createResourcesRepo();

  const chatService = createChatService({
    sessionRepo,
    modelClient: createGeminiClient(),
  });
  const consentService = createConsentService(sessionRepo);
  const resourcesService = createResourcesService(resourcesRepo);

  app.use(helmet());
  app.use(cors({ origin: config.corsOrigin }));
  app.use(morgan(config.nodeEnv === "production" ? "combined" : "dev"));
  app.use(express.json());

  app.use("/health", healthRouter);
  app.use("/chat", createChatRouter(chatService));
  app.use("/consent", createConsentRouter(consentService));
  app.use("/resources", createResourcesRouter(resourcesService));

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
