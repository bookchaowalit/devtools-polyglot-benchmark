import { readFileSync } from "node:fs";

interface Item {
  id: number;
  name: string;
  price_cents: number;
  qty: number;
  tags: string[];
}

const records: Item[] = JSON.parse(readFileSync(process.argv[2], "utf8"));
const byTag: Record<string, number> = {};
let total = 0;
for (const r of records) {
  total += r.price_cents * r.qty;
  for (const t of r.tags) byTag[t] = (byTag[t] ?? 0) + 1;
}
const value = (r: Item) => r.price_cents * r.qty;
const ranked = [...records].sort((a, b) => value(b) - value(a) || a.id - b.id);
const sortedTags = Object.fromEntries(Object.keys(byTag).sort().map((k) => [k, byTag[k]]));
process.stdout.write(
  JSON.stringify({
    count: records.length,
    total_value_cents: total,
    by_tag: sortedTags,
    top5: ranked.slice(0, 5).map((r) => r.id),
  }) + "\n",
);
