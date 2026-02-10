import { config } from "dotenv";
config();

import { loadConfig } from "./config";
import { createServer } from "./server";

const app = createServer();
const { port } = loadConfig();

app.listen(port, () => {
  console.log(`Backend running on http://localhost:${port}`);
});
