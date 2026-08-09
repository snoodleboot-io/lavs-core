# LAVS UI Concept — "Constellation"

> The version dashboard, reinvented. Not a table of rows — a living sky-map of how
> independent component timelines **align** into a product release.

See also: [ARCHITECTURE.md](./ARCHITECTURE.md) · [ROADMAP.md](../planning/ROADMAP.md) ·
Interactive mockup: [`frontend/ui/mockups/constellation.html`](../../frontend/ui/mockups/constellation.html)

---

## 1. Why not "vanilla"

Every version/artifact tool on the market renders the same thing: a **table**. Rows of
`name | version | date`, a filter bar, a "New" button. It is legible and forgettable, and
it actively hides LAVS's entire reason to exist — the *relationship* between many
independently-moving component versions and the single product version derived from them.

A table cannot show convergence. LAVS is fundamentally about **time** (each component
advances on its own) and **alignment** (a release is a vertical cut across all of them).
So the interface should be **spatial and temporal**, not tabular.

## 2. The core metaphor: an aligning sky

Think **observatory** — a transit-map of component timelines read like the night sky, where
a release is the rare moment everything lines up.

- **Time flows left → right.** The right edge is "now."
- **Each component is a stream** — a horizontal lane with its own color, like a subway line.
- **Each version is a star (station)** — a node on its stream, labeled by semver.
- **A release is a meridian** — a draggable vertical line that sweeps across every stream
  and **pins exactly one version per component**: the latest star at or before the
  meridian. The pinned stars light up and connect into a **constellation** — the shape of
  that release.
- **The product version is derived at the meridian** — shown in a heads-up readout that
  updates live as you scrub. Drop the meridian where you like and **"Cut Release"** to
  freeze that constellation into a named, immutable product release.

This makes the product's defining operation — *integrating component versions into one
coherent release* — a direct, physical gesture: **drag, watch them align, cut.**

```
component streams                    ┊ meridian (release cut)
                                     ┊
 api      ●───●─────●────────●───────◆        api    2.4.0  ◀ pinned
 ui       ──●────●──────●────────────◆        ui     1.9.2  ◀ pinned
 helm     ●─────────●─────────●──────◆        helm   0.7.0  ◀ pinned
 cli      ────●──────────●───────────◆        cli    1.1.0  ◀ pinned
                                     ┊
 time ─────────────────────────────▶ now      ⇒ product  "Aurora 5.0"
```

## 3. Design language — "Observatory"

A calm, dark, instrument-panel aesthetic — you are watching software move through time.

- **Mood:** deep space / observatory. Near-black canvas, luminous streams, glow on the
  active alignment. Restraint everywhere except the meridian, which is the one bright actor.
- **Color:** each component owns a hue (the only saturated color on screen); everything
  else is greyscale. A release meridian glows in a signature cyan/amber.
- **Motion is meaningful, never decorative:** stations gently pulse when freshly created;
  the constellation animates as the meridian moves; a release "cut" plays a brief
  crystallize/snap.
- **Typography:** a humanist sans for chrome; a mono for versions and IDs (versions are
  data — treat them like code).
- **Keyboard-first:** a `⌘K` command palette is the primary navigation; the meridian
  scrubs with `←/→`; `C` cuts a release. Mouse is fully supported but power users never
  need it.
- **Accessibility:** color is never the only signal (streams carry labels + patterns);
  full keyboard operation; reduced-motion mode collapses animation to instant state.

## 4. Primary views

| View | What it is | The non-vanilla move |
|------|-----------|----------------------|
| **Constellation** (home) | The stream/meridian timeline for a product | Scrub time, watch versions converge, cut a release by gesture |
| **Release ledger** | History of cut releases | Each release re-opens as the exact constellation it pinned — a frozen meridian |
| **Component focus** | One stream zoomed | Version stations with status (active/superseded/rolled_back) as a lifeline |
| **Product galaxy** | All products at a glance | Products as systems; health/recency as luminosity — not a grid of cards |

## 5. Signature interactions

1. **Scrub-to-derive** — dragging the meridian recomputes the pinned set and the derived
   product version in real time. The product version is an *output you discover*, not a
   field you type.
2. **Cut Release** — lock the current alignment into an immutable, named snapshot; the
   meridian crystallizes and joins the ledger.
3. **Rollback as rewind** — a component's `rolled_back` station visibly recedes (dimmed,
   struck) while the previous station re-illuminates — history is never erased, just
   re-lit. This mirrors the immutable-version model in [ARCHITECTURE.md](./ARCHITECTURE.md#4-domain-model).
4. **Diff two meridians** — drop a second, ghosted meridian to compare two releases; the
   streams highlight exactly which components changed between them.

## 6. How it maps to the domain & API

| UI element | Domain concept | API (target) |
|------------|----------------|--------------|
| Stream | Component | `GET /components?product=` |
| Station | Version (immutable) | `GET /versions?component=` |
| Meridian (live) | Candidate release | derived client-side from versions |
| Cut Release | Release + ReleaseComponent | `POST /releases` |
| Ledger entry | Release | `GET /releases`, `GET /releases/{id}` |
| Readout | Derived product version | from the release manifest |

The UI never invents truth: streams and stations come straight from the API; the meridian
is a *client-side projection*, and **Cut Release** is the only write — it persists the
alignment the user is already looking at.

## 7. Build notes (P4)

- Stack: **TypeScript 6 / React / pnpm / vitest** in `frontend/ui` (per `.prompticorn.yaml`).
- Rendering: **SVG** for streams/stations/meridian (crisp, animatable, accessible,
  inspectable); virtualize long timelines.
- State: the meridian position + selected product; everything else derives.
- Start from the static mockup in
  [`frontend/ui/mockups/constellation.html`](../../frontend/ui/mockups/constellation.html), which
  already implements scrub-to-derive and Cut Release against seeded data.

## 8. Open questions

- Time axis: real timestamps vs. ordinal "release ticks"? (Mockup uses ordinal for clarity.)
- How to render pre-release/build metadata on a station without clutter.
- Product-version derivation rule when components disagree (max? policy-driven? named?).
