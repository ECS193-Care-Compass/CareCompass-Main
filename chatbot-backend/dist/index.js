"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const dotenv_1 = require("dotenv");
(0, dotenv_1.config)();
const config_1 = require("./config");
const server_1 = require("./server");
const app = (0, server_1.createServer)();
const { port } = (0, config_1.loadConfig)();
app.listen(port, () => {
    console.log(`Backend running on http://localhost:${port}`);
});
