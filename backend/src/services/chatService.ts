import { SessionRepo } from "../repositories/sessionRepo";
import { detectSafetyFlags } from "./safetyService";
import { ChatContext, ChatRequestBody, ChatResponseBody } from "../types/api";

const DEFAULT_OPTIONS = [
  "Find local resources",
  "Talk through my options",
  "Emergency hotlines",
];

export type ChatModelClient = {
  generateReply(message: string, contextSummary?: string): Promise<string>;
};

export type PromptContextBuilder = {
  build(input: ChatRequestBody, mergedContext: ChatContext): Promise<string | undefined>;
};

export type ChatService = {
  handleChat(input: ChatRequestBody): Promise<ChatResponseBody>;
};

export type ChatServiceDeps = {
  sessionRepo: SessionRepo;
  modelClient: ChatModelClient;
  promptContextBuilder?: PromptContextBuilder;
};

// Default context builder; partner can swap with a RAG-backed implementation later.
export const defaultPromptContextBuilder: PromptContextBuilder = {
  async build(_input, mergedContext) {
    if (!mergedContext.zip) {
      return undefined;
    }

    return `zip=${mergedContext.zip}, helpType=${mergedContext.helpType ?? "unsure"}`;
  },
};

export function createChatService(deps: ChatServiceDeps): ChatService {
  const promptContextBuilder = deps.promptContextBuilder ?? defaultPromptContextBuilder;

  return {
    async handleChat(input: ChatRequestBody): Promise<ChatResponseBody> {
      const safety = detectSafetyFlags(input.message);
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
