// typescript-fastify lane and its variants.
//
// The baseline uses no BENCH_* flags. Each variant lane sets exactly one
// flag (see runner/lanes.py), so a result difference has one cause:
//
//   BENCH_DB=postgresjs   postgres.js instead of node-postgres (pg)
//   BENCH_WORKERS=2       node:cluster with 2 processes; the 10 connections are split between them
//
// The Bun variant runs this same compiled file with `bun` instead of `node`,
// and the Hono variant swaps the framework in server-hono.ts.
import cluster from "node:cluster";
import Fastify from "fastify";
import { loadItems, openDb, parseDbQuery, WORKERS } from "./common.js";

if (WORKERS > 1 && cluster.isPrimary) {
  for (let i = 0; i < WORKERS; i++) cluster.fork();
} else {
  const items = loadItems();
  const db = await openDb();
  const app = Fastify({ logger: false });

  app.get("/health", async () => ({ status: "ok" }));

  app.get<{ Params: { id: string } }>("/items/:id", async (req, reply) => {
    const record = /^\d+$/.test(req.params.id) ? items.get(Number(req.params.id)) : undefined;
    if (record === undefined) return reply.code(404).send({ error: "not_found" });
    return record;
  });

  app.get<{ Querystring: { after?: string; limit?: string } }>("/db/items", async (req, reply) => {
    if (!db) return reply.code(503).send({ error: "no_database" });
    const q = parseDbQuery(req.query.after, req.query.limit);
    if (!q) return reply.code(400).send({ error: "bad_request" });
    return { items: await db.page(q.after, q.limit) };
  });

  await app.listen({ host: "127.0.0.1", port: Number(process.env.PORT) });
}
