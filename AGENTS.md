# AGENTS.md

## Purpose
This file keeps a lightweight record of how we work in this repository and what matters most when making changes.

## Repository Snapshot
- **Project**: Excel-based software version monitoring system for Goepp Lab infrastructure.
- **Language**: Python 3.13.7.
- **Entry point**: `check_versions.py`.
- **Excel source of truth**: Path from `config.EXCEL_FILE_PATH` (do not assume local filename).
- **Excel rules**: Use **openpyxl only**; never use pandas.

## Files of Record
- **`CLAUDE.md`**: Canonical architecture + rules. Keep this aligned with any code changes.
- **`README.md`**: General documentation only (no local infrastructure specifics).
- **`config.py`**: Centralized configuration and credentials (no secrets committed).

## Key Working Agreements
- **No pandas**: All Excel operations must use openpyxl to preserve formatting.
- **Sheet name**: Always use `Sheet1`.
- **No fallback methods**: Implement one intended method per checker; fail cleanly if it breaks.
- **No shell=True**: All subprocess calls must be list-based.
- **Prefer Docker Hub** when both GitHub and DockerHub fields exist.
- **Keep changes modular**: Put service-specific logic in `checkers/` and wire in `version_manager.py`.
- **Docs timing**: Do not update `README.md` on every change; only update docs when explicitly asked or during final commit prep.

## Common Workflows
- **Run all checks**: `./check_versions.py --check-all`
- **Summary**: `./check_versions.py --summary`
- **List apps**: `./check_versions.py --list`
- **Single app**: `./check_versions.py --app "name"`
- **Virtual env**: `source .venv/bin/activate`

## Adding a New Checker
1. Add entries in Excel with `Check_Current` and `Check_Latest` + full `Target` URL.
2. Populate both GitHub and DockerHub repo fields when available.
3. Create or update a module in `checkers/`.
4. Import and connect in `version_manager.py`.
5. Test with `--app`.

## Testing Notes
- Prefer app-level testing first (`--app`) before full run.
- Use `--summary` and `--list` to confirm status updates.
