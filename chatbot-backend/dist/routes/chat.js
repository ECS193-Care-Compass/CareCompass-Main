"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createChatRouter = createChatRouter;
const express_1 = require("express");
const asyncHandler_1 = require("../middleware/asyncHandler");
const validate_1 = require("../middleware/validate");
const api_1 = require("../types/api");
function createChatRouter(chatService) {
    const router = (0, express_1.Router)();
    router.post("/", (0, validate_1.validateBody)(api_1.chatRequestSchema), (0, asyncHandler_1.asyncHandler)(async (req, res) => {
        const response = await chatService.handleChat(req.body);
        res.json(response);
    }));
    return router;
}
