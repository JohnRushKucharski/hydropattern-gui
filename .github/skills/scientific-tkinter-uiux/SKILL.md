---
name: scientific-tkinter-uiux
description: UI/UX and architecture guidance for building or extending the hydropattern-gui Tkinter desktop shell. Use when creating/editing anything under src/hydropattern_gui/ui/, wiring the runner service (live logs, cancel, status) to the UI, or reviewing GUI code for layout, responsiveness, or scientific-input ergonomics.
license: MIT
---

# Scientific Tkinter UI/UX (hydropattern-gui)

## Overview

hydropattern-gui is a Tkinter desktop shell for authoring TOML configs and
running `hydropattern run <toml>` as a subprocess. This skill gives concrete,
repo-consistent rules for layout, styling, responsiveness, and scientific
input ergonomics so the UI stays modern, testable, and non-blocking.

**Read `issues/README.md` first.** It contains locked product decisions
(architecture boundaries, run contract, v1 scope). This skill must not
contradict it. Do not reopen locked decisions unless the user asks.

## Locked constraint: Tkinter + ttk, not customtkinter

`issues/README.md` locks the UI technology as **Tkinter + ttk** (not
`customtkinter`). `customtkinter` is not a project dependency, and adding it
would reopen a locked decision. Use `tkinter.ttk` with deliberate styling
instead:

```python
import tkinter as tk
from tkinter import ttk

style = ttk.Style()
style.theme_use("clam")  # cross-platform, most stylable built-in theme
style.configure("Card.TFrame", background="#f4f5f7", relief="flat")
style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
```

If a future ADR/issue explicitly unlocks a themed-widget library (e.g.
`ttkbootstrap`, `sv-ttk`), add it to `pyproject.toml` dependencies first and
note the decision change — don't silently introduce a new widget toolkit.

## Layout & information architecture

Structure GUI screens as a 2-panel split, matching the run-screen behavior
already specified in `issues/README.md` (7.1):

- **Sidebar (left, fixed width ~280-320px):** grouped parameter inputs in
  card-like `ttk.LabelFrame`/`ttk.Frame` sections, primary "Run" action,
  cancel action, progress/status indicator.
- **Main stage (right, expanding via `grid_columnconfigure(weight=1)`):**
  live log pane (tagged stdout/stderr), run status, "open output folder"
  link, TOML preview (complete/minimal toggle).

Use `grid` with weighted rows/columns for resizing, not `pack` for the
top-level layout. Keep consistent padding (`padx`/`pady` 10-15px) and group
related widgets inside a bordered frame rather than spacing loose widgets.

## Scientific input ergonomics

- Pair every numeric entry with a visible unit label
  (e.g. `cfs`, `mm`, `°C`) — never leave units implicit.
- Validate on `<FocusOut>` (or `validate="focusout"`), and give immediate
  visual feedback (e.g. red-tinted `ttk.Style` state) when a value is out of
  physical/config bounds — don't wait for a run attempt to surface bad input.
- Provide sensible defaults aligned with hydropattern's parser defaults
  (per `issues/README.md` §4.5) so forms open in a valid state.
- For the component/characteristic editor (timing, magnitude, duration,
  rate_of_change, frequency) and the climate-canvas advanced panel, prefer a
  `ttk.Treeview` or repeated card rows over a single giant form — density
  without clutter.

## Non-blocking execution (hard requirement)

The run contract always shells out to `hydropattern run <toml>`. Never block
`mainloop`:

- Launch the subprocess and any log-streaming from a `threading.Thread`
  (daemon) or `concurrent.futures`; never call blocking I/O on the main
  thread.
- Stream stdout/stderr incrementally into the log pane using a
  `queue.Queue` drained via `root.after(ms, ...)`, or schedule UI updates
  with `self.after(0, callback)` from the worker thread. Never touch Tk
  widgets directly from a background thread.
- Disable the Run button and show an indeterminate `ttk.Progressbar` (or a
  status label like "Running... step N") while a run is active; re-enable on
  completion, failure, or cancel.
- Cancel must terminate the full child process tree on Windows (not just the
  parent PID) and resolve run status deterministically to a
  cancelled/failed/succeeded state — this is an explicit v1 acceptance
  criterion, not optional polish.

## Status, logs, and feedback

- Give every run a visible state machine: idle → running →
  succeeded/failed/cancelled. Reflect it in both a status label and button
  enable/disable state.
- Log pane: append lines incrementally, tag by source (stdout/stderr) with
  distinct styling (e.g. `Text` tags), auto-scroll to bottom, and never
  truncate/silently swallow output — raw logs must stay accessible even when
  a friendlier top-level error message is shown (per §8 error handling).
- On completion, surface an explicit "open output folder" action next to the
  status, not buried in a menu.

## Matplotlib integration (only when plotting is in scope)

v1 explicitly excludes rich in-app plotting beyond logs/status
(`issues/README.md` §5). Don't add `matplotlib.backends.backend_tkagg`
canvases speculatively. If/when a later slice adds visualization:

- Embed via `FigureCanvasTkAgg`, matching figure background to the ttk
  surface color (`fig.patch.set_facecolor(...)`) and calling
  `fig.tight_layout()`.
- Embed `NavigationToolbar2Tk` below the canvas.
- Redraw only on new data (`canvas.draw()`), never on every widget event.

## Architecture fit

Keep the rules above consistent with the module boundaries in
`issues/README.md` §6:

- `ui/` holds only widgets, layout, and thin controller glue — no TOML
  serialization or subprocess logic.
- The runner's log-streaming/cancel/state-machine logic belongs in
  `runner/`; `ui/` only renders what the runner emits and calls its public
  API (start/cancel).
- Validate the domain model in `domain/`/`toml_io/`, not inline in widget
  callbacks — the UI should call a validation function and render its
  result.

## Quick review checklist

When reviewing or writing GUI code, check:

- [ ] No blocking calls (subprocess, file I/O, sleep) on the main thread.
- [ ] Run button disabled + progress shown while a run is active.
- [ ] Cancel works and reaches a deterministic terminal state.
- [ ] Every numeric input shows its unit and validates on focus-out.
- [ ] Layout uses `grid` with weights, consistent padding, and grouped cards.
- [ ] No `customtkinter` or other unapproved widget toolkit introduced.
- [ ] UI code contains no TOML/subprocess business logic.
