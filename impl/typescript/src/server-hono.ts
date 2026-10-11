// typescript-hono variant: same data access and validation as server.ts
// (common.ts), Hono on @hono/node-server instead of Fastify.
import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { loadItems, openDb, parseDbQuery } from "./common.js";

const items = loadItems();
const db = await openDb();
const app = new Hono();

app.get("/health", (c) => c.json({ status: "ok" }));

app.get("/items/:id", (c) => {
  const id = c.req.param("id");
  const record = /^\d+$/.test(id) ? items.get(Number(id)) : undefined;
  if (record === undefined) return c.json({ error: "not_found" }, 404);
  return c.json(record);
});

app.get("/db/items", async (c) => {
  if (!db) return c.json({ error: "no_database" }, 503);
  const q = parseDbQuery(c.req.query("after"), c.req.query("limit"));
  if (!q) return c.json({ error: "bad_request" }, 400);
  return c.json({ items: await db.page(q.after, q.limit) });
});

serve({ fetch: app.fetch, hostname: "127.0.0.1", port: Number(process.env.PORT) });
