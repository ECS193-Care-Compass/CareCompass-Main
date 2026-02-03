"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createResourcesRouter = createResourcesRouter;
const express_1 = require("express");
const asyncHandler_1 = require("../middleware/asyncHandler");
const validate_1 = require("../middleware/validate");
const api_1 = require("../types/api");
function createResourcesRouter(resourcesService) {
    const router = (0, express_1.Router)();
    router.get("/", (0, validate_1.validateQuery)(api_1.resourcesQuerySchema), (0, asyncHandler_1.asyncHandler)(async (req, res) => {
        const resources = await resourcesService.getResources(req.query);
        res.json({ resources });
    }));
    return router;
}
