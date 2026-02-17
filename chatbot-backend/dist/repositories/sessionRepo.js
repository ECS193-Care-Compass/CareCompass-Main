"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createSessionRepo = createSessionRepo;
const memorySessionRepo_1 = require("./memory/memorySessionRepo");
function createSessionRepo() {
    return new memorySessionRepo_1.MemorySessionRepo();
}
