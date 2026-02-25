import { ChatContext, ChatRequestBody } from "../types/api";
import { PromptContextBuilder } from "./chatService";

export class RagPromptContextBuilder implements PromptContextBuilder {
  async build(_input: ChatRequestBody, _mergedContext: ChatContext): Promise<string | undefined> {
    // Placeholder for partner's retrieval + citation context injection.
    return undefined;
  }
}
