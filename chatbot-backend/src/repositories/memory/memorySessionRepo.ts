import { SessionRecord, SessionRepo } from "../sessionRepo";

export class MemorySessionRepo implements SessionRepo {
  private readonly sessions = new Map<string, SessionRecord>();

  async get(sessionId: string): Promise<SessionRecord | null> {
    return this.sessions.get(sessionId) ?? null;
  }

  async upsert(record: SessionRecord): Promise<void> {
    this.sessions.set(record.sessionId, record);
  }
}
