import resourcesSample from "../../data/resources.sample.json";
import { ResourcesRepo } from "../resourcesRepo";
import { Resource } from "../../types/api";

export class MemoryResourcesRepo implements ResourcesRepo {
  async list(): Promise<Resource[]> {
    return resourcesSample as Resource[];
  }
}
