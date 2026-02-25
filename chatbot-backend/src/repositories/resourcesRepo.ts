import { Resource } from "../types/api";
import { MemoryResourcesRepo } from "./memory/memoryResourcesRepo";

export type ResourcesRepo = {
  list(): Promise<Resource[]>;
};

export function createResourcesRepo(): ResourcesRepo {
  return new MemoryResourcesRepo();
}
