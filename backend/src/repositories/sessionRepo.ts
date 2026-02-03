import { ChatContext } from "../types/api";
import { MemorySessionRepo } from "./memory/memorySessionRepo";

export type SessionRecord = {
  sessionId: string;
  consentToStore: boolean;
  consentToReminders: boolean;
  context?: ChatContext;
  lastMessageAt?: string;
};

export type SessionRepo = {
  get(sessionId: string): Promise<SessionRecord | null>;
  upsert(record: SessionRecord): Promise<void>;
};

export function createSessionRepo(): SessionRepo {
  return new MemorySessionRepo();
}
