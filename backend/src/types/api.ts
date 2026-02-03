import { z } from "zod";

export const helpTypeSchema = z.enum(["medical", "emotional", "legal", "unsure"]);
export type HelpType = z.infer<typeof helpTypeSchema>;

export const chatContextSchema = z.object({
  zip: z.string().trim().length(5).optional(),
  helpType: helpTypeSchema.optional(),
  anonymous: z.boolean().optional(),
});
export type ChatContext = z.infer<typeof chatContextSchema>;

export const chatRequestSchema = z.object({
  sessionId: z.string().trim().min(1),
  message: z.string().trim().min(1),
  context: chatContextSchema.optional(),
});
export type ChatRequestBody = z.infer<typeof chatRequestSchema>;

export type SafetyFlags = {
  crisis: boolean;
  recommendHotline: boolean;
  matched: string[];
};

export type ChatResponseBody = {
  reply: string;
  options: string[];
  safety: SafetyFlags;
};

export const consentSchema = z.object({
  sessionId: z.string().trim().min(1),
  consentToStore: z.boolean(),
  consentToReminders: z.boolean().optional(),
});
export type ConsentBody = z.infer<typeof consentSchema>;

export const resourceCategorySchema = z.enum([
  "medical",
  "mental_health",
  "legal",
  "hotline",
  "advocacy",
]);
export type ResourceCategory = z.infer<typeof resourceCategorySchema>;

export type Resource = {
  id: string;
  name: string;
  category: ResourceCategory;
  phone?: string;
  website?: string;
  area?: string;
  zipPrefixes?: string[];
};

export const resourcesQuerySchema = z.object({
  zip: z.string().trim().length(5).optional(),
  category: resourceCategorySchema.optional(),
});
export type ResourcesQuery = z.infer<typeof resourcesQuerySchema>;
