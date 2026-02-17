"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemorySessionRepo = void 0;
class MemorySessionRepo {
    sessions = new Map();
    async get(sessionId) {
        return this.sessions.get(sessionId) ?? null;
    }
    async upsert(record) {
        this.sessions.set(record.sessionId, record);
    }
}
exports.MemorySessionRepo = MemorySessionRepo;
