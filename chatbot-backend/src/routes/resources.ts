import { Router } from "express";
import { asyncHandler } from "../middleware/asyncHandler";
import { validateQuery } from "../middleware/validate";
import { ResourcesService } from "../services/resourcesService";
import { resourcesQuerySchema } from "../types/api";

export function createResourcesRouter(resourcesService: ResourcesService) {
  const router = Router();

  router.get(
    "/",
    validateQuery(resourcesQuerySchema),
    asyncHandler(async (req, res) => {
      const resources = await resourcesService.getResources(req.query);
      res.json({ resources });
    })
  );

  return router;
}
