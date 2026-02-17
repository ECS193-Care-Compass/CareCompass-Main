"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createResourcesRepo = createResourcesRepo;
const memoryResourcesRepo_1 = require("./memory/memoryResourcesRepo");
function createResourcesRepo() {
    return new memoryResourcesRepo_1.MemoryResourcesRepo();
}
