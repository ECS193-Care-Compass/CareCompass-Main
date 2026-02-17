"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createServer = createServer;
const cors_1 = __importDefault(require("cors"));
const express_1 = __importDefault(require("express"));
const helmet_1 = __importDefault(require("helmet"));
const morgan_1 = __importDefault(require("morgan"));
const geminiClient_1 = require("./clients/geminiClient");
const config_1 = require("./config");
const errorHandler_1 = require("./middleware/errorHandler");
const resourcesRepo_1 = require("./repositories/resourcesRepo");
const sessionRepo_1 = require("./repositories/sessionRepo");
const chat_1 = require("./routes/chat");
const consent_1 = require("./routes/consent");
const health_1 = __importDefault(require("./routes/health"));
const resources_1 = require("./routes/resources");
const chatService_1 = require("./services/chatService");
const consentService_1 = require("./services/consentService");
const resourcesService_1 = require("./services/resourcesService");
function createServer() {
    const app = (0, express_1.default)();
    const config = (0, config_1.loadConfig)();
    const sessionRepo = (0, sessionRepo_1.createSessionRepo)();
    const resourcesRepo = (0, resourcesRepo_1.createResourcesRepo)();
    const resourcesService = (0, resourcesService_1.createResourcesService)(resourcesRepo);
    const chatService = (0, chatService_1.createChatService)({
        sessionRepo,
        modelClient: (0, geminiClient_1.createGeminiClient)(),
        resourcesService,
    });
    const consentService = (0, consentService_1.createConsentService)(sessionRepo);
    app.use((0, helmet_1.default)());
    app.use((0, cors_1.default)({ origin: config.corsOrigin }));
    app.use((0, morgan_1.default)(config.nodeEnv === "production" ? "combined" : "dev"));
    app.use(express_1.default.json());
    app.use("/health", health_1.default);
    app.use("/chat", (0, chat_1.createChatRouter)(chatService));
    app.use("/consent", (0, consent_1.createConsentRouter)(consentService));
    app.use("/resources", (0, resources_1.createResourcesRouter)(resourcesService));
    app.use(errorHandler_1.notFoundHandler);
    app.use(errorHandler_1.errorHandler);
    return app;
}
