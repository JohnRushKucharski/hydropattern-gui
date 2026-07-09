# Copilot Cloud Agent Onboarding (hydropattern-gui)

## What this repository is
- **Project type:** Python package (early-stage GUI scaffold).
- **Purpose:** `hydropattern-gui` is intended to provide a GUI for creating/loading Hydropattern TOML configs and running Hydropattern workflows.  
  Current implementation is minimal (`hydropattern_gui.main()` prints a hello message).
- **Languages/runtime:** Python, packaged with `uv`/PEP 621 (`pyproject.toml`), build backend `uv_build`.
- **Scale:** Very small app code (`src/hydropattern_gui/__init__.py`), plus a large `.github/skills/` tree (agent skill content, not app runtime code).

## Always-follow environment rules
1. **Always run commands from repo root.**
2. **Always use `uv` for reproducible runs** (`uv sync`, `uv run`, `uv build`) because:
   - `.python-version` pins **Python 3.12**.
   - Host Python may differ (validated host had Python 3.13.1).
   - `uv run` used Python 3.12.8 from the managed environment.
3. **Always bootstrap before validation/build:** `uv sync --dev`.
4. **Hydropattern dependency source is local editable by default:** `../hydropattern` (and transitive `../climate-canvas`).
5. **Trust this file first**; only search the repo if instructions here are incomplete or proven wrong.

## Verified command matrix (Windows PowerShell)

### Bootstrap
- **Command:** `uv sync --dev`
- **Result:** works.
- **Validated time:** ~0.09s (warm cache).
- **Precondition:** run at repo root.
- **Postcondition:** dev tools available in `.venv`.
- **Important:** this repo currently expects sibling repos at `../hydropattern` and `../climate-canvas`.

### Run application entrypoint
- **Command:** `uv run hydropattern-gui`
- **Result:** works; prints `Hello from hydropattern-gui!`.
- **Validated time:** ~0.30s.

### Hydropattern CLI availability
- **Command:** `uv run hydropattern --help`
- **Result:** works.
- **Validated time:** ~10s on first call.

### Build package artifacts
- **Command:** `uv build`
- **Result:** works; builds sdist and wheel in `dist\`.
- **Validated time:** ~0.11s.
- **Postcondition:** `dist\hydropattern_gui-0.1.0.tar.gz` and wheel exist.

### Lint
- **Do not run:** `uv run ruff check .` (fails in this repo state).
  - **Observed failure:** lint errors from `.github/skills/matplotlib/scripts/*.py` (non-product files).
- **Use instead for product code:** `uv run ruff check src`
- **Result:** works; all checks passed.
- **Validated time:** ~0.55s.

### Type check
- **Command:** `uv run mypy src`
- **Result:** works; no issues in current source.
- **Validated time:** ~1.06s to ~2.73s.

### Tests
- **Command:** `uv run pytest`
- **Current result:** works; test suite runs from `tests/`.

### Optional executable packaging smoke test
- **Command:** `uv run pyinstaller --onefile src\hydropattern_gui\__init__.py --name hydropattern-gui-smoke`
- **Result:** works.
- **Validated time:** ~13.79s.
- **Postcondition:** exe emitted to `dist\`.

### Climate-canvas CLI note
- **Command:** `uv run climate-canvas --help`
- **Current result:** fails (`RuntimeError: Type not yet supported: float | None` in Typer command parsing).
- **Impact:** GUI should call `hydropattern` CLI and/or climate-canvas plotting API via hydropattern flow; do not depend on standalone climate-canvas CLI help as a validation step for this repo.

## Clean and rerun sequence (validated)
Use this before a fresh validation pass:

```powershell
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
Get-ChildItem -Filter *.spec | Remove-Item -Force
uv sync --dev
uv run ruff check src
uv run mypy src
uv run hydropattern-gui
uv run hydropattern --help
uv build
```

No command timeouts were observed during validation.

## Hydropattern integration caveat (important for runner implementation)
- Hydropattern currently resolves relative input paths from the **process working directory**, not from the TOML file location.
- Example:
  - Running from this repo with `..\hydropattern\examples\minimal.toml` fails because TOML references `examples/single_timeseries.csv` relatively.
  - Running from `..\hydropattern` root with `examples\minimal.toml` works.
- **Always run `hydropattern run <toml>` with `cwd` set to the TOML parent directory** (or normalize all TOML paths to absolute paths before execution).

## Repository layout and where to edit

### Root files/directories
- `.python-version` (pins Python 3.12)
- `pyproject.toml` (project metadata, dependencies, scripts, build backend)
- `tests/` (pytest suite)
- `uv.lock` (locked dependency graph)
- `src/hydropattern_gui/__init__.py` (current app entrypoint)
- `issues/README.md` (implementation roadmap and acceptance ideas)
- `README.md` (currently empty)
- `.github/skills/` (agent skill assets; not product runtime)

### Key architecture facts
- Package uses **src layout** (`src/hydropattern_gui`).
- Console script:
  - `hydropattern-gui = "hydropattern_gui:main"` in `pyproject.toml`.
- Runtime dependency: `tomli-w`.
- Runtime dependencies include `hydropattern` and `psutil`.
- Dev dependencies include `mypy`, `pyinstaller`, `pytest`, `pytest-timeout`, `ruff`.
- No `CONTRIBUTING.md` found.
- No `.github/workflows/` CI workflow files found in this repository snapshot.
- `tool.uv.sources` currently binds `hydropattern` to local editable `../hydropattern`.
- Attempting to pin hydropattern directly from GitHub currently fails due its transitive
  climate-canvas dependency metadata (`#subdirectory=..\\climate-canvas`).

### Contents of key docs/source (for quick orientation)
- `README.md`: currently empty.
- `issues/README.md`: implementation roadmap with five staged tracer bullets:
  1. TOML round-trip core.
  2. Runner service around `hydropattern run <toml>`.
  3. Tkinter shell (timeseries/output/metric).
  4. Component editor + climate-canvas advanced panel.
  5. Windows executable packaging + release docs.
- `src/hydropattern_gui/__init__.py`: currently only:
  - `main()` -> `print("Hello from hydropattern-gui!")`.

## Validation guidance before opening PR
For code changes in product code, run this minimum sequence:

```powershell
uv sync --dev
uv run ruff check src
uv run mypy src
uv run hydropattern-gui
uv run hydropattern --help
uv build
```

Run tests before PR:

```powershell
uv run pytest
```
