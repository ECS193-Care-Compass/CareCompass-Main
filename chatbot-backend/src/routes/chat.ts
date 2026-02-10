import { Router } from "express";
import { asyncHandler } from "../middleware/asyncHandler";
import { validateBody } from "../middleware/validate";
import { ChatService } from "../services/chatService";
import { chatRequestSchema } from "../types/api";

export function createChatRouter(chatService: ChatService) {
  const router = Router();

  router.post(
    "/",
    validateBody(chatRequestSchema),
    asyncHandler(async (req, res) => {
      const response = await chatService.handleChat(req.body);
      res.json(response);
    })
  );

  return router;
}
