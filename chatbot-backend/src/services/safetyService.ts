import { SafetyFlags } from "../types/api";

const CRISIS_TERMS = [
  "suicide",
  "kill myself",
  "self harm",
  "abuse",
  "overdose",
  "not safe",
  "unsafe",
];

export function detectSafetyFlags(message: string): SafetyFlags {
  const text = message.toLowerCase();
  const matched = CRISIS_TERMS.filter((term) => text.includes(term));
  const crisis = matched.length > 0;

  return {
    crisis,
    recommendHotline: crisis,
    matched,
  };
}
