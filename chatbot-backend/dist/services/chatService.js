"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultPromptContextBuilder = void 0;
exports.createChatService = createChatService;
const safetyService_1 = require("./safetyService");
const DEFAULT_OPTIONS = [
    "Find local resources",
    "Talk through my options",
    "Emergency hotlines",
];
const RESOURCE_HINTS = [
    "resource",
    "resources",
    "near me",
    "nearby",
    "find",
    "support",
    "clinic",
    "shelter",
    "hotline",
    "help line",
];
const CATEGORY_KEYWORDS = [
    {
        category: "medical",
        keywords: ["medical", "doctor", "hospital", "clinic", "healthcare", "health care"],
    },
    {
        category: "mental_health",
        keywords: ["mental", "therapy", "therapist", "counseling", "counselling", "anxiety", "depression", "emotional"],
    },
    {
        category: "legal",
        keywords: ["legal", "lawyer", "attorney", "court", "restraining order", "custody"],
    },
    {
        category: "hotline",
        keywords: ["hotline", "helpline", "crisis line", "988", "911"],
    },
    {
        category: "advocacy",
        keywords: ["advocacy", "advocate", "domestic violence", "dv shelter", "shelter"],
    },
];
const HELP_TYPE_TO_CATEGORY = {
    medical: "medical",
    emotional: "mental_health",
    legal: "legal",
};
function extractZip(text) {
    const match = text.match(/\b\d{5}\b/);
    return match?.[0];
}
function inferCategoryFromText(text) {
    for (const mapping of CATEGORY_KEYWORDS) {
        if (mapping.keywords.some((keyword) => text.includes(keyword))) {
            return mapping.category;
        }
    }
    return undefined;
}
function inferCategory(text, context) {
    return inferCategoryFromText(text) ?? (context.helpType ? HELP_TYPE_TO_CATEGORY[context.helpType] : undefined);
}
function shouldSuggestResources(text) {
    return RESOURCE_HINTS.some((hint) => text.includes(hint));
}
function formatResourcesReply(resources, filter) {
    const scope = [];
    if (filter.category) {
        scope.push(filter.category.replace(/_/g, " "));
    }
    if (filter.zip) {
        scope.push(`near ${filter.zip}`);
    }
    const intro = scope.length
        ? `Here are local ${scope.join(" ")} resources from our directory:`
        : "Here are resources from our local directory:";
    const lines = resources.map((resource) => {
        const details = [];
        if (resource.phone) {
            details.push(`call ${resource.phone}`);
        }
        if (resource.website) {
            details.push(resource.website);
        }
        const areaLabel = resource.area ? ` (${resource.area})` : "";
        const detailLabel = details.length ? ` - ${details.join(" | ")}` : "";
        return `- ${resource.name}${areaLabel}${detailLabel}`;
    });
    return `${intro}\n${lines.join("\n")}`;
}
// Default context builder; partner can swap with a RAG-backed implementation later.
exports.defaultPromptContextBuilder = {
    async build(_input, mergedContext) {
        if (!mergedContext.zip) {
            return undefined;
        }
        return `zip=${mergedContext.zip}, helpType=${mergedContext.helpType ?? "unsure"}`;
    },
};
function createChatService(deps) {
    const promptContextBuilder = deps.promptContextBuilder ?? exports.defaultPromptContextBuilder;
    return {
        async handleChat(input) {
            const safety = (0, safetyService_1.detectSafetyFlags)(input.message);
            const normalizedMessage = input.message.toLowerCase();
            const existing = await deps.sessionRepo.get(input.sessionId);
            const mergedContext = {
                ...(existing?.context ?? {}),
                ...(input.context ?? {}),
            };
            await deps.sessionRepo.upsert({
                sessionId: input.sessionId,
                consentToStore: existing?.consentToStore ?? false,
                consentToReminders: existing?.consentToReminders ?? false,
                context: mergedContext,
                lastMessageAt: new Date().toISOString(),
            });
            const contextSummary = await promptContextBuilder.build(input, mergedContext);
            const modelReply = await deps.modelClient.generateReply(input.message, contextSummary);
            let resourcesReply;
            if (deps.resourcesService && shouldSuggestResources(normalizedMessage)) {
                const filter = {
                    zip: extractZip(normalizedMessage) ?? mergedContext.zip,
                    category: inferCategory(normalizedMessage, mergedContext),
                };
                const resources = await deps.resourcesService.getResources(filter);
                if (resources.length > 0) {
                    resourcesReply = formatResourcesReply(resources.slice(0, 3), filter);
                }
                else if (filter.zip || filter.category) {
                    resourcesReply = "I could not find a direct match in our local directory yet. I can still help you search nearby options.";
                }
            }
            const crisisPrefix = safety.crisis
                ? "If you are in immediate danger, call 911. You can also call or text 988 for 24/7 support. "
                : "";
            return {
                reply: [`${crisisPrefix}${modelReply}`.trim(), resourcesReply].filter(Boolean).join("\n\n"),
                options: DEFAULT_OPTIONS,
                safety,
            };
        },
    };
}
