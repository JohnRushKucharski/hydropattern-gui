# hydropattern-gui

Tkinter GUI for building Hydropattern TOML configs, previewing/saving them, and running
`hydropattern run` with live logs.

## Runtime compatibility (pinned set)

| Package | Pinned version |
|---|---|
| hydropattern-gui | 0.1.0 |
| hydropattern | 0.0.0 |
| climate-canvas | 0.1.0 |

Pinned in `pyproject.toml` + `uv.lock`. Current dev source mapping uses:
- `../hydropattern` (editable)
- `../climate-canvas` (editable)

## Install / bootstrap

```powershell
uv sync --dev
```

## Run GUI

```powershell
uv run hydropattern-gui
```

What to test in GUI now:
1. Open TOML -> fields hydrate.
2. Edit component rows (timing/magnitude/duration/rate_of_change/frequency) in chosen order.
3. Edit climate-canvas advanced fields.
4. Preview TOML -> reflects form.
5. Run -> live stdout/stderr log panel updates.
6. About -> shows runtime versions + pinned runtime set.

## Build single Windows executable

Option A:
```powershell
uv sync --dev
uv run pyinstaller --noconfirm --clean --windowed --onefile --name hydropattern-gui src\hydropattern_gui\__main__.py
```

Option B:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows-exe.ps1
```

Output:
- `dist\hydropattern-gui.exe`

## Validate before release

```powershell
uv run ruff check src tests
uv run mypy src
uv run pylint src\hydropattern_gui
uv run pytest
uv build
```

## Known limits

- GUI currently supports one component form target at time (row-based editor), but all 5
  characteristic types + ordering are supported.
- Validation focuses on hydropattern parser rules. Errors shown in status text.
- Hydropattern relative file paths resolve from process cwd; runner executes in selected
  working dir to avoid path mismatch.