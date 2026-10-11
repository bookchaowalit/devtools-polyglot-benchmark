import { readFileSync } from "node:fs";
import Fastify from "fastify";
import pg from "pg";

const items = new Map<number, unknown>();
for (const r of JSON.parse(readFileSync(process.env.RECORDS_PATH!, "utf8"))) items.set(r.id, r);

const POOL_SIZE = 10;
const DB_QUERY = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2";
const pool = process.env.DATABASE_URL ? new pg.Pool({ connectionString: process.env.DATABASE_URL, max: POOL_SIZE }) : null;
if (pool) {
  // open every connection up front, as the other lanes do
  const clients = await Promise.all(Array.from({ length: POOL_SIZE }, () => pool.connect()));
  clients.forEach((c) => c.release());
}

const app = Fastify({ logger: false });

app.get("/health", async () => ({ status: "ok" }));

app.get<{ Params: { id: string } }>("/items/:id", async (req, reply) => {
  const record = /^\d+$/.test(req.params.id) ? items.get(Number(req.params.id)) : undefined;
  if (record === undefined) return reply.code(404).send({ error: "not_found" });
  return record;
});

const intParam = (raw: string | undefined, fallback: number) =>
  raw === undefined ? fallback : /^\d+$/.test(raw) ? Number(raw) : null;

app.get<{ Querystring: { after?: string; limit?: string } }>("/db/items", async (req, reply) => {
  if (!pool) return reply.code(503).send({ error: "no_database" });
  const after = intParam(req.query.after, 0);
  const limit = intParam(req.query.limit, 50);
  if (after === null || limit === null || limit < 1 || limit > 100) {
    return reply.code(400).send({ error: "bad_request" });
  }
  const { rows } = await pool.query(DB_QUERY, [after, limit]);
  return { items: rows };
});

await app.listen({ host: "127.0.0.1", port: Number(process.env.PORT) });
