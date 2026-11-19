// Drives site/app.js in a tiny fake DOM with a fetch the test resolves by hand, to check that only the run
// picked last reaches the page. Run by tests/test_site.py; prints one JSON line.
import { readFileSync } from "node:fs";
import vm from "node:vm";

class El {
  constructor(tag) { this.tag = tag; this.children = []; this.text = ""; this.dataset = {}; this.style = {}; this.listeners = {}; }
  set textContent(v) { this.text = String(v); this.children = []; }
  get textContent() { return this.text + this.children.map((c) => c.textContent).join(" "); }
  append(...kids) { this.children.push(...kids); }
  replaceChildren(...kids) { this.text = ""; this.children = kids; }
  setAttribute() {}
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatch(type) { for (const fn of this.listeners[type] || []) fn({}); }
}

const nodes = { run: new El("select"), status: new El("div"), cards: new El("div") };
const pending = new Map();
const settle = (url, ok, body) => { const d = pending.get(url); pending.delete(url); ok ? d.resolve({ ok: true, json: async () => body }) : d.reject(new Error("network down")); };
const fetch = (url) => new Promise((resolve, reject) => pending.set(url, { resolve, reject }));
const tick = () => new Promise((r) => setTimeout(r, 0));
const run = (id, group) => ({ id, group, started_at: "2026-11-19T10:00:00Z", runner: { kind: "github" } });
const record = (group) => ({ group, runner: { kind: "github", cpu_model: "cpu", vcpu: 4 }, commit: "abcdef123456", settings: { repeats: 3 }, load_generator: "oha", results: [] });

const document = { readyState: "complete", createElement: (t) => new El(t), getElementById: (id) => nodes[id], querySelector: () => null };
const ctx = vm.createContext({ document, fetch, console, setTimeout, Map, Promise, JSON, Math, Number, String, Error, encodeURIComponent });
ctx.window = ctx;
vm.runInContext(readFileSync(new URL("../site/app.js", import.meta.url), "utf8"), ctx);

const out = {};
// The list is newest last; the page shows newest first, so "typescript" opens on load and "python" is option 1.
await tick();
settle("data/index.json", true, { runs: [run("go", "go"), run("py", "python"), run("ts", "typescript")] });
await tick(); await tick();
nodes.run.value = "1"; nodes.run.dispatch("change");       // pick python while typescript is still loading
settle("data/runs/py.json", true, record("python"));
await tick(); await tick();
settle("data/runs/ts.json", true, record("typescript"));    // the stale answer arrives last
await tick(); await tick();
out.late_success = nodes.status.textContent;
nodes.run.value = "2"; nodes.run.dispatch("change");       // pick go, then python again before go answers
nodes.run.value = "1"; nodes.run.dispatch("change");
settle("data/runs/py.json", true, record("python"));
await tick(); await tick();
settle("data/runs/go.json", false);                          // the stale request fails last
await tick(); await tick();
out.late_failure = nodes.status.textContent;
console.log(JSON.stringify(out));
