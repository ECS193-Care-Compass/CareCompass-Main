import { NextFunction, Request, RequestHandler, Response } from "express";
import { AnyZodObject, ZodTypeAny } from "zod";

export function validateBody(schema: AnyZodObject): RequestHandler {
  return (req: Request, _res: Response, next: NextFunction) => {
    req.body = schema.parse(req.body);
    next();
  };
}

export function validateQuery(schema: ZodTypeAny): RequestHandler {
  return (req: Request, _res: Response, next: NextFunction) => {
    req.query = schema.parse(req.query);
    next();
  };
}
