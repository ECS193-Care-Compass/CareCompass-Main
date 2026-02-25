import { ResourcesRepo } from "../repositories/resourcesRepo";
import { Resource, ResourceCategory } from "../types/api";

export type ResourcesFilter = {
  zip?: string;
  category?: ResourceCategory;
};

export type ResourcesService = {
  getResources(filter: ResourcesFilter): Promise<Resource[]>;
};

export function createResourcesService(repo: ResourcesRepo): ResourcesService {
  return {
    async getResources(filter: ResourcesFilter): Promise<Resource[]> {
      const all = await repo.list();

      return all.filter((resource) => {
        const categoryOk = filter.category ? resource.category === filter.category : true;

        const zipOk = filter.zip
          ? !resource.zipPrefixes?.length || resource.zipPrefixes.some((prefix) => filter.zip?.startsWith(prefix))
          : true;

        return categoryOk && zipOk;
      });
    },
  };
}
