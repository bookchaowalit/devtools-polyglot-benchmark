# Dashboard shell

The shared calm, Apple-like look for read-only data pages and small calculators. Started
2026-11-15 with this app as the pilot; on 2026-11-16 it moved to status, uptime-monitor,
link-analytics, seo-analyzer and real-estate (all `*.bookchaowalit.com`). It is the fourth shell after the
Workbench (devtools), the sales page and the App shell (list apps). Each app is its own repo,
so the shell is copied in, not installed: take `app/dashboard-shell.css` and
`components/dashboard-shell.tsx`.

## Rules

- **One question per page**, asked by the `h1` ("Electricity load"). The line under it says
  the period, the unit, and a `Sample data` pill when the numbers are not real.
- **One period switch** (segmented control) at the top right; it changes every figure on the page.
  Its options wrap to a new row with large text (flex wrap, no fixed widths).
  Leave it out when the data has no periods (status) rather than show a switch that does nothing.
- **At most four stat tiles**: label, value with its unit, and one line of context ("at 13:00").
  On phones they become one grouped card with the value on the right, wrapping under the label
  when the text is enlarged.
- **One main chart**, with a `Show table` switch so every value can be read without the drawing.
  The switch is a native `<details>` in the panel head's flex row (its name stays `Show table`, the
  browser announces open or closed), sized by its own text so it wraps under the title with large text;
  the table opens without JavaScript and CSS (`:has`) hides the chart while it is open. A browser
  without `:has()` shows both and hides the switch (`@supports not selector(:has(*))`).
  The SVG only draws; axis labels are HTML, so they never stretch. Each x label is capped at the
  room its neighbours leave (`labelRoom`, from the real tick gaps; phones need twice the room) and cut
  with an ellipsis, inner labels that would still collide are left out (never the first or last one passed), so pass short `tickLabels`.
  When each value counts a time bucket, pass `buckets`: points sit at bucket centres, ticks on bucket edges.
  The y scale tops out at four round grid gaps (two significant digits) that reach `max`, and the
  line uses the same top, so each label is the value of its grid line. The chart's `aria-label` says what it shows (low, peak).
- **Breakdown list** beside the chart: name, one line of detail, value and a share bar. When a
  row selects something it is a button with `aria-pressed`, and a callout under the list says
  what the selection means.
- **Inputs, when the page is a calculator** (SEO check, rental yield): labelled `ds-field`s in a
  panel, at most one filled `ds-button`, a `ds-range` slider with its value printed beside the label.
- **Static rows** (`<li class="ds-row">`) for lists you only read, such as services or checks; the
  state goes in a `Pill` with a word (Up, Down, Pass, Fail).
- **Colour is never the only signal**: dots sit next to names, the peak is named in text.
- **Say where the data comes from** in a note under the panels (sample, live, how fresh).
- **Floor:** text ≥ 12px, controls ≥ 44px, 3px focus ring, 4.5:1 text contrast (placeholders
  included) and 3:1 for chart lines, grid lines and input edges in light and dark, no horizontal
  scroll at 320px. A selected row shows the accent bar, not only a tint; in forced colors
  the bar is a real `Highlight` left border and the chart drops its area fill.

## Pieces

| Piece | Where |
|---|---|
| Tokens `--ds-*` (light + dark, same palette as the App shell), top bar, head, segmented control, stat tiles, panels, line chart, table, breakdown rows (button or static), share bar, callout, form fields, slider, filled button, pills, footer | `app/dashboard-shell.css` |
| `DashTop`, `DashFoot`, `Stat`, `Pill`, `Segmented` (render it from a client component: it takes an `onChange`), re-exporting `ChartPanel`, `chartTop`, `axisSteps`, `linePoints`, `pointAt`, `tickAt` and `labelRoom` (all server-safe) | `components/dashboard-shell.tsx` |
| `ChartPanel` (chart + `<details>` table switch, optional short `tickLabels`, repeated ticks drawn once), `chartTop`, `axisSteps`, `linePoints`, `pointAt`, `tickAt`, `labelRoom`, `buckets` mode; no state, so no `"use client"` | `components/dashboard-chart.tsx` |
| Tests for the shell itself, so an app that uses only part of it still covers all of it | `tests/dashboard-shell.test.tsx` |

Put the font variable on `<html>` (not `<body>`): the tokens are defined on `:root`, so a font
variable set lower down never reaches them.

## Moving an app onto the shell

1. Copy the five files (CSS, `dashboard-shell.tsx`, `dashboard-chart.tsx`, shell test, this file); import `./dashboard-shell.css` from `globals.css` and drop the old theme.
2. Keep the app's `lib/` maths; add small helpers for the stats (total, low, share) there.
3. Rebuild the page as top bar → head (title, period line, period switch) → stat tiles →
   chart panel + breakdown panel → data note → footer.
4. Add `components/**/*.tsx` to the coverage `include` and write mounted (happy-dom) tests for
   the period switch, the table view and the breakdown selection.
5. Screenshot 320 / 375 / 500 / 768 / 1440 in light and dark, once with the table view open
   (500px is where an auto-fit grid quietly turns back into two columns).
