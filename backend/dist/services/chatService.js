"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultPromptContextBuilder = void 0;
exports.createChatService = createChatService;
const safetyService_1 = require("./safetyService");
const DEFAULT_OPTIONS = [
    "Find local resources",
    "Talk through my options",
    "Emergency hotlines",
];
// Default context builder; partner can swap with a RAG-backed implementation later.
exports.defaultPromptContextBuilder = {
    async build(_input, mergedContext) {
        if (!mergedContext.zip) {
            return undefined;
        }
        return `zip=${mergedContext.zip}, helpType=${mergedContext.helpType ?? "unsure"}`;
    },
};
function createChatService(deps) {
    const promptContextBuilder = deps.promptContextBuilder ?? exports.defaultPromptContextBuilder;
    return {
        async handleChat(input) {
            const safety = (0, safetyService_1.detectSafetyFlags)(input.message);
            const existing = await deps.sessionRepo.get(input.sessionId);
            const mergedContext = {
                ...(existing?.context ?? {}),
                ...(input.context ?? {}),
            };
            await deps.sessionRepo.upsert({
                sessionId: input.sessionId,
                consentToStore: existing?.consentToStore ?? false,
                consentToReminders: existing?.consentToReminders ?? false,
                context: mergedContext,
                lastMessageAt: new Date().toISOString(),
            });
            const contextSummary = await promptContextBuilder.build(input, mergedContext);
            const modelReply = await deps.modelClient.generateReply(input.message, contextSummary);
            const crisisPrefix = safety.crisis
                ? "If you are in immediate danger, call 911. You can also call or text 988 for 24/7 support. "
                : "";
            return {
                reply: `${crisisPrefix}${modelReply}`.trim(),
                options: DEFAULT_OPTIONS,
                safety,
            };
        },
    };
}
