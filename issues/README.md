# hydropattern-gui Complete Agent Context 

Purpose: single, complete handoff for agents building `hydropattern-gui`.

This file contains locked decisions, constraints, architecture, backlog, acceptance criteria, and execution/testing expectations.

---

## 1) Product goal

Build a small, organized GUI for hydropattern that:
- creates valid TOML configs,
- runs hydropattern through the CLI using those TOML files,
- preserves reproducibility and parity with CLI/library usage,
- can be distributed as a Windows executable.

---

## 2) Locked decisions (already made; do not reopen unless user asks)

1. **Repository boundary**
   - GUI is in its own repo: `hydropattern-gui`.
   - Not inside `hydropattern`.
   - Reason: reduce brittleness risk for hydropattern CLI/library users.

2. **UI technology**
   - Tkinter + ttk.

3. **Run contract**
   - GUI always writes TOML.
   - GUI always runs subprocess CLI: `hydropattern run <toml>`.
   - No direct hydropattern internal execution path for production runs.

4. **TOML output modes**
   - Default: **complete explicit TOML** (reproducibility-first).
   - Optional: **minimal TOML** (readability).

5. **Run sequence**
   - Quick test run first.
   - Then normal run.

6. **Packaging target**
   - Windows-first executable via PyInstaller.

7. **Dependency bundling**
   - Bundle pinned `hydropattern` and compatible `climate-canvas` in exe.

8. **Versioning policy**
   - Each GUI release pins one compatible hydropattern/climate-canvas set.
   - No floating latest in release builds.

9. **v1 UX must include**
   - live log pane (stdout/stderr stream),
   - cancel button (terminate run),
   - final status + open-output-folder link,
   - About panel with versions (gui/hydropattern/climate-canvas),
   - Open existing TOML and hydrate form.

10. **Delivery approach**
    - 5 vertical AFK slices, TDD style.

---

## 3) Domain vocabulary (keep naming consistent)

From hydropattern CONTEXT:

- **Scenario**: one data column/run evaluated independently.
- **Scenario grid**: scenario set named with `_x_y` pattern.
- **Precipitation delta**: first numeric token in scenario-grid name (x-axis).
- **Temperature delta**: second numeric token (y-axis).
- **Metric**: scalar per scenario for z-axis (`portion`, `percentage`, `return_period`).

Use these terms in labels/docs/tests to avoid ambiguity.

---

## 4) Reproducibility/parity requirements (non-negotiable)

1. Run path must use CLI contract (`hydropattern run`), not alternate execution semantics.
2. Generated TOML used for run must be saved with outputs.
3. Save run artifacts:
   - TOML used,
   - command used,
   - stdout/stderr logs,
   - versions metadata.
4. Validation should rely on real CLI behavior where possible.
5. GUI defaults must align with hydropattern parser defaults.

---

## 5) Functional scope for v1

### Included
- Author/edit config via structured forms:
  - timeseries section,
  - output/metric section,
  - component editor for characteristics,
  - climate-canvas advanced controls.
- Preview TOML (complete/minimal modes).
- Save TOML.
- Open/import TOML and hydrate UI.
- Execute run (test run then normal run).
- Live logs.
- Cancel run.
- Open output folder.
- About/version display.
- Windows executable packaging.

### Excluded (for v1)
- Heavy GUI automation framework.
- Rich in-app plotting/report visualization beyond logs/status.
- Non-Windows packaging as required deliverable (can be later).

---

## 6) Architecture blueprint (recommended module boundaries)

Use these boundaries to keep code testable and stable:

- `src/hydropattern_gui/domain/`
  - dataclasses/value objects for GUI state/config model
  - normalization and validation-neutral structures

- `src/hydropattern_gui/toml_io/`
  - serializer/deserializer
  - stable key ordering
  - complete/minimal rendering policy
  - TOML import mapping to domain model

- `src/hydropattern_gui/runner/`
  - subprocess command builder
  - process lifecycle
  - streaming log dispatcher
  - cancel/terminate implementation
  - run result/status model

- `src/hydropattern_gui/ui/`
  - Tkinter frames/widgets
  - presentation/controller logic
  - minimal business logic

- `src/hydropattern_gui/versioning/` (optional)
  - expose and render pinned dependency versions

- `tests/unit/`
  - domain + TOML + runner units

- `tests/integration/`
  - real CLI smoke runs with fixtures

- `packaging/`
  - PyInstaller spec/build scripts

---

## 7) UX behavior details

### 7.1 Run screen behavior
- Run action disabled while run active.
- Log pane appends incremental stdout/stderr lines with source tags.
- Cancel immediately requests termination; status transitions to cancelling/cancelled.
- On success/failure/cancel:
  - show explicit status,
  - offer open output folder,
  - preserve logs.

### 7.2 TOML modes
- Toggle between complete/minimal.
- Complete mode default on startup.
- Preview panel always reflects current mode.
- Save action writes mode-selected TOML.

### 7.3 TOML import
- Parse existing TOML and map all known fields to UI.
- Unknown/unsupported fields:
  - preserve in model where feasible, or
  - warn explicitly before saving if data loss possible.

### 7.4 Climate-canvas advanced options
Expose all keys:
- `interpolate`
- `show`
- `title`
- `xlabel`
- `ylabel`
- `zlabel`
- `threshold`
- `color_map`
- `color_map_ticks`

---

## 8) Error handling requirements

- Do not silently swallow subprocess errors.
- Show exact CLI stderr/stdout in logs.
- Map common failures to clear top-level message while keeping raw log accessible.
- Cancellation must be explicit state, not generic failure.

---

## 9) Windows process cancellation guidance

Implement robust termination for child process tree on Windows:
- do not only kill parent PID if child processes can survive.
- ensure run state resolves deterministically after cancel request.

---

## 10) Testing strategy (approved)

### Unit tests
- TOML round-trip (GUI model -> TOML -> model).
- Complete vs minimal TOML mode behavior.
- Stable key order checks.
- Runner command construction.
- Runner state transitions (idle/running/succeeded/failed/cancelled).
- Log streaming callback behavior.

### Integration smoke tests
- Execute real `hydropattern run` with fixture TOML.
- Success case and failure case.
- Quick-test-then-normal-run flow.

### Lint/type/test gates
- `ruff`
- `mypy`
- `pytest`

---

## 11) Anti-patterns (do not do)

1. Direct internal hydropattern API execution as main run path.
2. Hidden generated TOML.
3. GUI defaults diverging from parser semantics.
4. Missing cancel implementation.
5. Floating/unpinned core dependencies in shipped executable.
6. Thick UI layer containing business logic.

---

## 12) Backlog (5 vertical slices, AFK, TDD)

### Slice 1 — Tracer bullet: TOML round-trip core
**Type:** AFK  
**Blocked by:** None

**What to build**
- Domain config model + TOML writer/reader.
- Path: GUI state -> TOML -> GUI state.

**Acceptance criteria**
- [ ] Complete mode writes full explicit TOML with stable key ordering.
- [ ] Minimal mode omits defaults correctly.
- [ ] Importing generated TOML restores equivalent config state.
- [ ] Unit tests cover round-trip and mode differences.

---

### Slice 2 — Runner service: CLI execution contract
**Type:** AFK  
**Blocked by:** Slice 1

**What to build**
- Subprocess runner for `hydropattern run <toml>`.
- Live logs, cancel support, deterministic run result model.
- Quick test run then normal run flow.

**Acceptance criteria**
- [ ] Deterministic command built from config.
- [ ] Incremental stdout/stderr streaming to UI callbacks.
- [ ] Cancel terminates process tree cleanly on Windows.
- [ ] Run status transitions deterministic and test-covered.
- [ ] Integration smoke test succeeds with fixture TOML.

---

### Slice 3 — Core UI shell (timeseries/output/metric)
**Type:** AFK  
**Blocked by:** Slices 1 and 2

**What to build**
- Tkinter UI for core sections.
- Load/save/preview TOML.
- Run wiring to runner service.

**Acceptance criteria**
- [ ] User can author timeseries/output/metric without raw TOML editing.
- [ ] Open existing TOML hydrates form correctly.
- [ ] Preview TOML reflects current form state and selected mode.
- [ ] Run UI shows status/log and output-folder action.

---

### Slice 4 — Component editor + climate-canvas advanced panel
**Type:** AFK  
**Blocked by:** Slice 3

**What to build**
- Structured component/characteristic editor.
- Advanced panel for full climate-canvas options.

**Acceptance criteria**
- [ ] Supports characteristic rows: timing, magnitude, duration, rate_of_change, frequency.
- [ ] Supports ordering and per-component `verbose` + `success_pattern`.
- [ ] Supports climate-canvas keys:
  - `interpolate`, `show`, `title`, `xlabel`, `ylabel`, `zlabel`,
  - `threshold`, `color_map`, `color_map_ticks`.
- [ ] Validation errors shown before run with field mapping clarity.

---

### Slice 5 — Windows executable packaging + release docs
**Type:** AFK  
**Blocked by:** Slice 4

**What to build**
- PyInstaller packaging.
- Release docs and compatibility table.

**Acceptance criteria**
- [ ] Reproducible single Windows executable build.
- [ ] Bundled pinned `hydropattern` + `climate-canvas`.
- [ ] About panel displays version set.
- [ ] Release docs include install, run, known limits, compatibility matrix.

---

## 13) TDD workflow contract per slice

For every slice:
1. RED: one behavior test first.
2. GREEN: minimal code to pass.
3. REFACTOR: improve design without behavior drift.
4. VERIFY: run relevant unit/integration tests + lint/type checks.

Prefer many thin tracer bullets over thick horizontal work.

---

## 14) Initial setup notes (known state)

`hydropattern-gui` local repo already initialized with `uv`, including:
- runtime: `tomli-w`
- dev: `pytest`, `ruff`, `mypy`, `pyinstaller`

Baseline commands expected:
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy src`

---

## 15) Definition of done (v1)

v1 complete when:
- all 5 slices accepted,
- CLI-based run path stable and observable,
- TOML import/export round-trip reliable,
- Windows executable built and smoke-tested,
- docs sufficient for end-user install/run/troubleshooting.

