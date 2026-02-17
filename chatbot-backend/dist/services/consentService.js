"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createConsentService = createConsentService;
function createConsentService(sessionRepo) {
    return {
        async saveConsent(payload) {
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
