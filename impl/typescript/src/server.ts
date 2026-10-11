import { readFileSync } from "node:fs";
import Fastify from "fastify";

const items = new Map<number, unknown>();
for (const r of JSON.parse(readFileSync(process.env.RECORDS_PATH!, "utf8"))) items.set(r.id, r);

const app = Fastify({ logger: false });

app.get("/health", async () => ({ status: "ok" }));

app.get<{ Params: { id: string } }>("/items/:id", async (req, reply) => {
  const record = /^\d+$/.test(req.params.id) ? items.get(Number(req.params.id)) : undefined;
  if (record === undefined) return reply.code(404).send({ error: "not_found" });
  return record;
});

await app.listen({ host: "127.0.0.1", port: Number(process.env.PORT) });
