"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createResourcesService = createResourcesService;
function createResourcesService(repo) {
    return {
        async getResources(filter) {
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
