import { Router } from "express";
import { asyncHandler } from "../middleware/asyncHandler";
import { validateBody } from "../middleware/validate";
import { ConsentService } from "../services/consentService";
import { consentSchema } from "../types/api";

export function createConsentRouter(consentService: ConsentService) {
  const router = Router();

  router.post(
    "/",
    validateBody(consentSchema),
    asyncHandler(async (req, res) => {
      await consentService.saveConsent(req.body);
      res.status(200).json({ ok: true });
    })
  );

  return router;
}
