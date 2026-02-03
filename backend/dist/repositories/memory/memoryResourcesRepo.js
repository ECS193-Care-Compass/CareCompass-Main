"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryResourcesRepo = void 0;
const resources_sample_json_1 = __importDefault(require("../../data/resources.sample.json"));
class MemoryResourcesRepo {
    async list() {
        return resources_sample_json_1.default;
    }
}
exports.MemoryResourcesRepo = MemoryResourcesRepo;
