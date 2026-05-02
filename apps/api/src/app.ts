import { Hono } from "hono";
import { env } from "./env.js";

const app = new Hono();

app.get(`${env.API_BASE_PATH}/health`, (c) =>
  c.json({ message: "hello world", service: "api" })
);

export default app;
