import { SessionRepo } from "../repositories/sessionRepo";
import { ConsentBody } from "../types/api";

export type ConsentService = {
  saveConsent(payload: ConsentBody): Promise<void>;
};

export function createConsentService(sessionRepo: SessionRepo): ConsentService {
  return {
    async saveConsent(payload: ConsentBody): Promise<void> {
      const existing = await sessionRepo.get(payload.sessionId);

      await sessionRepo.upsert({
        sessionId: payload.sessionId,
        consentToStore: payload.consentToStore,
        consentToReminders: payload.consentToReminders ?? false,
        context: existing?.context,
        lastMessageAt: existing?.lastMessageAt,
      });
    },
  };
}
