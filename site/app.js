// Polyglot Benchmark Lab page: loads data/index.json (the run list), then data/runs/<id>.json for the run you open.
// Pure helpers are exported on window.PB for the Python smoke test's sake and for reading in the console.
// Same as DashTop in the Dashboard shell: keep --ds-top-height equal to the sticky bar (taller when it wraps with large
// text), so dashboard-shell.css's scroll-padding-top keeps focused controls clear of it.
(function () {
  var bar = document.querySelector(".ds-top");
  if (!bar || !window.ResizeObserver || !document.adoptedStyleSheets || typeof CSSStyleSheet !== "function") return;
  var sheet = new CSSStyleSheet();
  document.adoptedStyleSheets = document.adoptedStyleSheets.concat(sheet);
  new ResizeObserver(function () { sheet.replaceSync(":root{--ds-top-height:" + Math.ceil(bar.getBoundingClientRect().height) + "px}"); }).observe(bar);
})();
(function () {
  const WORKLOADS = [
    { id: "W1-json", title: "W1 · JSON transform", what: "Parse 10,000 records, aggregate, sort, serialize. Each run is a fresh process.",
      metrics: [{ key: "wall_ms", label: "Wall time (ms) — lower is better", fmt: (v) => v.toFixed(1) },
                { key: "peak_rss_mib", label: "Peak RSS (MiB) — lower is better", fmt: (v) => v.toFixed(1), single: true }] },
    { id: "W2-hash", title: "W2 · SHA-256 of 100 MiB", what: "Stream a file in 1 MiB chunks and hash it.",
      metrics: [{ key: "throughput_mib_s", label: "Throughput (MiB/s) — higher is better", fmt: (v) => v.toFixed(0) },
                { key: "peak_rss_mib", label: "Peak RSS (MiB) — lower is better", fmt: (v) => v.toFixed(1), single: true }] },
    { id: "W3-http-read", title: "W3 · HTTP read", what: "GET /items/{id} from an in-memory store, 50 concurrent connections.",
      metrics: [{ key: "rps", label: "Requests per second — higher is better", fmt: (v) => Math.round(v).toLocaleString("en-US") },
                { key: "p95_ms", label: "p95 latency (ms) — lower is better", fmt: (v) => v.toFixed(2) },
                { key: "peak_rss_mib", label: "Server peak RSS (MiB) — lower is better", fmt: (v) => v.toFixed(1), single: true }] },
    { id: "W4-http-db", title: "W4 · HTTP + PostgreSQL", what: "GET /db/items?after={id}&limit=50 — one indexed query per request, pool of 10 connections, 50 concurrent connections.",
      metrics: [{ key: "rps", label: "Requests per second — higher is better", fmt: (v) => Math.round(v).toLocaleString("en-US") },
                { key: "p95_ms", label: "p95 latency (ms) — lower is better", fmt: (v) => v.toFixed(2) },
                { key: "peak_rss_mib", label: "Server peak RSS (MiB) — lower is better", fmt: (v) => v.toFixed(1), single: true }] },
    { id: "W5-cold-start", title: "W5 · Cold start", what: "Process start to first 200 on /health. This matters for services that sleep when idle.",
      metrics: [{ key: "ready_ms", label: "Time to ready (ms) — lower is better", fmt: (v) => v.toFixed(0) }] },
  ];
  const DELTAS = [
    { wl: "W1-json", key: "wall_ms", label: "W1 wall time", higher: false },
    { wl: "W3-http-read", key: "rps", label: "W3 requests/s", higher: true },
    { wl: "W3-http-read", key: "p95_ms", label: "W3 p95 latency", higher: false },
    { wl: "W4-http-db", key: "rps", label: "W4 requests/s", higher: true },
    { wl: "W4-http-db", key: "p95_ms", label: "W4 p95 latency", higher: false },
    { wl: "W4-http-db", key: "peak_rss_mib", label: "W4 peak RSS", higher: false, single: true },
    { wl: "W5-cold-start", key: "ready_ms", label: "Cold start", higher: false },
  ];

  const el = (tag, attrs = {}, text) => { const n = document.createElement(tag); Object.assign(n, attrs); if (text !== undefined) n.textContent = text; return n; };
  const pill = (tone, text) => { const p = el("span", { className: "ds-pill" }, text); p.dataset.tone = tone; return p; };

  /** Compare a variant with its parent: the change in percent and a word, so better/worse never rests on colour. */
  function verdict(parent, variant, higherIsBetter) {
    const pct = (variant / parent - 1) * 100;
    if (Math.abs(pct) < 3) return { pct, word: "same", tone: "grey" };
    const better = higherIsBetter ? pct > 0 : pct < 0;
    return { pct, word: better ? "better" : "worse", tone: better ? "green" : "red" };
  }

  function metricOf(run, lane, d) {
    const r = run.results.find((x) => x.lane === lane && x.workload === d.wl && x.metrics);
    if (!r) return undefined;
    const v = r.metrics[d.key];
    return d.single ? v : v.median;
  }

  function panel(title, what) {
    const section = el("section", { className: "ds-panel" });
    const head = el("div", { className: "ds-panel-head" });
    const box = el("div");
    box.append(el("h2", {}, title));
    if (what) box.append(el("p", { className: "pb-what" }, what));
    head.append(box);
    section.append(head);
    return section;
  }

  function renderVariants(run) {
    const byLane = new Map(run.results.filter((r) => r.parent).map((r) => [r.lane, r]));
    const variants = (run.lanes || [...byLane.keys()]).filter((l) => byLane.has(l)).map((l) => byLane.get(l));
    if (!variants.length) return null;
    const card = panel("Variants vs parent", "Each variant changes one thing and runs on the same machine as its parent. Changes under 3% are within run-to-run noise and marked “same”.");
    for (const v of variants) {
      const block = el("div", { className: "pb-variant" });
      const name = el("h3", { className: "pb-lane" }, v.lane);
      block.append(name, el("p", {}, `${v.change || "One change"} · against ${v.parent}`));
      const list = el("ul", { className: "ds-rows" });
      for (const d of DELTAS) {
        const a = metricOf(run, v.parent, d), b = metricOf(run, v.lane, d);
        const row = el("li", { className: "ds-row" });
        row.append(el("span", { className: "ds-row-name" }, d.label));
        if (a === undefined || b === undefined) {
          row.append(el("span", { className: "ds-row-detail" }, "Not measured for both lanes"), el("span", { className: "ds-row-value" }, "—"));
        } else {
          const r = verdict(a, b, d.higher);
          const value = el("span", { className: "ds-row-value pb-verdict" }, `${r.pct > 0 ? "+" : ""}${r.pct.toFixed(0)}% `);
          value.append(pill(r.tone, r.word));
          row.append(el("span", { className: "ds-row-detail" }, `${a.toFixed(2)} → ${b.toFixed(2)}`), value);
        }
        list.append(row);
      }
      block.append(list);
      card.append(block);
    }
    return card;
  }

  function renderRun(run) {
    const cards = document.getElementById("cards");
    cards.replaceChildren();
    const r = run.runner;
    const status = document.getElementById("status");
    status.replaceChildren(el("strong", {}, `${run.group || "core"} · ${r.kind} runner`),
      el("span", {}, `${r.cpu_model || r.machine} · ${r.vcpu} vCPU · commit ${run.commit.slice(0, 7)} · ${run.settings.repeats} repeats · load generator ${run.load_generator}`));
    const variants = renderVariants(run);
    if (variants) cards.append(variants);

    for (const w of WORKLOADS) {
      const rows = run.results.filter((x) => x.workload === w.id);
      const card = panel(w.title, w.what);
      if (!rows.length) { card.append(el("p", { className: "pb-empty" }, "Not measured in this run.")); cards.append(card); continue; }
      for (const m of w.metrics) {
        card.append(el("h3", { className: "pb-metric" }, m.label));
        const vals = rows.filter((x) => x.metrics).map((x) => {
          const v = x.metrics[m.key];
          return m.single ? { lane: x.lane, v } : { lane: x.lane, v: v.median, lo: v.min, hi: v.max };
        });
        const max = Math.max(...vals.map((x) => x.hi ?? x.v));
        const list = el("ul", { className: "ds-rows" });
        for (const x of vals) {
          const row = el("li", { className: "ds-row" });
          const meter = el("span", { className: "ds-meter" });
          meter.setAttribute("aria-hidden", "true");
          const fill = el("span");
          fill.style.width = `${max > 0 ? Math.max(1, (x.v / max) * 100) : 0}%`;
          meter.append(fill);
          row.append(el("span", { className: "ds-row-name pb-lane" }, x.lane),
            el("span", { className: "ds-row-detail" }, x.lo !== undefined && x.hi > x.lo ? `median · range ${m.fmt(x.lo)}–${m.fmt(x.hi)}` : m.single ? "one value per run" : "median"),
            el("span", { className: "ds-row-value" }, m.fmt(x.v)), meter);
          list.append(row);
        }
        card.append(list);
        for (const x of rows.filter((y) => !y.metrics)) card.append(el("p", { className: "pb-empty" }, `${x.lane}: failed the contract, so it was not measured.`));
      }
      const d = el("details", { className: "pb-record" });
      const pre = el("pre", {}, JSON.stringify(rows.map((x) => ({ lane: x.lane, runtime: x.runtime, contract_passed: x.contract_passed, metrics: x.metrics })), null, 2));
      pre.tabIndex = 0;
      d.append(el("summary", {}, "Run record (raw JSON)"), pre);
      card.append(d);
      cards.append(card);
    }
  }

  function showMessage(title, text) {
    document.getElementById("status").replaceChildren(el("strong", {}, title), el("span", {}, text));
    document.getElementById("cards").replaceChildren();
  }

  async function openRun(meta) {
    showMessage("Loading run…", `${meta.started_at.slice(0, 16).replace("T", " ")} UTC · ${meta.group || "core"}`);
    try {
      const res = await fetch(`data/runs/${encodeURIComponent(meta.id)}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      renderRun(await res.json());
    } catch (error) {
      showMessage("This run could not be loaded", `${error.message}. Try another run or reload the page.`);
    }
  }

  async function start() {
    const select = document.getElementById("run");
    try {
      const res = await fetch("data/index.json");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const runs = (await res.json()).runs.slice().reverse();
      select.replaceChildren();
      if (!runs.length) { showMessage("No published runs yet", "Results appear here after the first benchmark run is published."); return; }
      runs.forEach((run, i) => select.append(el("option", { value: String(i) }, `${run.started_at.slice(0, 16).replace("T", " ")} UTC · ${run.group || "core"} (${run.runner.kind})`)));
      select.disabled = false;
      select.addEventListener("change", () => openRun(runs[Number(select.value)]));
      await openRun(runs[0]);
    } catch (error) {
      select.replaceChildren(el("option", {}, "No runs"));
      showMessage("The run list could not be loaded", `${error.message}. Reload the page to try again.`);
    }
  }

  window.PB = { verdict };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
