"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectSafetyFlags = detectSafetyFlags;
const CRISIS_TERMS = [
    "suicide",
    "kill myself",
    "self harm",
    "abuse",
    "overdose",
    "not safe",
    "unsafe",
];
function detectSafetyFlags(message) {
    const text = message.toLowerCase();
    const matched = CRISIS_TERMS.filter((term) => text.includes(term));
    const crisis = matched.length > 0;
    return {
        crisis,
        recommendHotline: crisis,
        matched,
    };
}
