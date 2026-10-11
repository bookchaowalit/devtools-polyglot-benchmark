// Shared by the Fastify and Hono servers so the two differ only in framework.
import { readFileSync } from "node:fs";
import pg from "pg";
import postgres from "postgres";

export const WORKERS = Number(process.env.BENCH_WORKERS ?? "1");
const TOTAL_CONNECTIONS = 10;
const POOL_SIZE = Math.floor(TOTAL_CONNECTIONS / WORKERS);

export function loadItems(): Map<number, unknown> {
  const items = new Map<number, unknown>();
  for (const r of JSON.parse(readFileSync(process.env.RECORDS_PATH!, "utf8"))) items.set(r.id, r);
  return items;
}

export interface Db {
  page(after: number, limit: number): Promise<unknown[]>;
}

export async function openDb(): Promise<Db | null> {
  const url = process.env.DATABASE_URL;
  if (!url) return null;
  if (process.env.BENCH_DB === "postgresjs") {
    const sql = postgres(url, { max: POOL_SIZE });
    // open every connection up front, as the other lanes do
    await Promise.all(Array.from({ length: POOL_SIZE }, () => sql`SELECT 1`));
    return {
      // postgres.js results are arrays; JSON serialization ignores their extra fields
      page: async (after, limit) =>
        (await sql`SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > ${after} ORDER BY id LIMIT ${limit}`) as unknown as unknown[],
    };
  }
  const pool = new pg.Pool({ connectionString: url, max: POOL_SIZE });
  const clients = await Promise.all(Array.from({ length: POOL_SIZE }, () => pool.connect()));
  clients.forEach((c) => c.release());
  const text = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2";
  return { page: async (after, limit) => (await pool.query(text, [after, limit])).rows };
}

const intParam = (raw: string | undefined, fallback: number) =>
  raw === undefined ? fallback : /^\d+$/.test(raw) ? Number(raw) : null;

export function parseDbQuery(rawAfter?: string, rawLimit?: string): { after: number; limit: number } | null {
  const after = intParam(rawAfter, 0);
  const limit = intParam(rawLimit, 50);
  if (after === null || limit === null || limit < 1 || limit > 100 || after > 2 ** 31 - 1) return null;
  return { after, limit };
}
