"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createConsentRouter = createConsentRouter;
const express_1 = require("express");
const asyncHandler_1 = require("../middleware/asyncHandler");
const validate_1 = require("../middleware/validate");
const api_1 = require("../types/api");
function createConsentRouter(consentService) {
    const router = (0, express_1.Router)();
    router.post("/", (0, validate_1.validateBody)(api_1.consentSchema), (0, asyncHandler_1.asyncHandler)(async (req, res) => {
        await consentService.saveConsent(req.body);
        res.status(200).json({ ok: true });
    }));
    return router;
}
