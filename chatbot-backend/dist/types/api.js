"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resourcesQuerySchema = exports.resourceCategorySchema = exports.consentSchema = exports.chatRequestSchema = exports.chatContextSchema = exports.helpTypeSchema = void 0;
const zod_1 = require("zod");
exports.helpTypeSchema = zod_1.z.enum(["medical", "emotional", "legal", "unsure"]);
exports.chatContextSchema = zod_1.z.object({
    zip: zod_1.z.string().trim().length(5).optional(),
    helpType: exports.helpTypeSchema.optional(),
    anonymous: zod_1.z.boolean().optional(),
});
exports.chatRequestSchema = zod_1.z.object({
    sessionId: zod_1.z.string().trim().min(1),
    message: zod_1.z.string().trim().min(1),
    context: exports.chatContextSchema.optional(),
});
exports.consentSchema = zod_1.z.object({
    sessionId: zod_1.z.string().trim().min(1),
    consentToStore: zod_1.z.boolean(),
    consentToReminders: zod_1.z.boolean().optional(),
});
exports.resourceCategorySchema = zod_1.z.enum([
    "medical",
    "mental_health",
    "legal",
    "hotline",
    "advocacy",
]);
exports.resourcesQuerySchema = zod_1.z.object({
    zip: zod_1.z.string().trim().length(5).optional(),
    category: exports.resourceCategorySchema.optional(),
});
