# Version Check Module

## Overview
SQLite-based software version monitoring system with multi-instance support for tracking various applications across the Goepp Lab infrastructure.

Note: This is for my specific infrastructure only, not a general purpose app. The only reason I make this a public repository is for reference only. If one were to take this code and try to make it work for them, significant changes would be needed to customize it. Unless of course you run the exact tech stack in the exact same way I do.

## Architecture
- **Language**: Python
- **Database**: SQLite file at `config.DATABASE_PATH` (env: `DATABASE_PATH`, default: `data/version_checker.db` inside the repo) — two tables, `applications` and `transactions` (see `src/db.py`)
- **Modular Design**: Individual checkers in `src/checkers/` directory with shared utilities
- **CLI Interface**: `check_versions.py` for command-line operations
- **Terminal UI**: `check_versions.py --tui` launches a full-screen interactive view (`src/tui/app.py`, built with Textual) on top of the same `VersionManager` — no separate data path or business logic
- **Virtual Environment**: Always use `source .venv/bin/activate`
- **Unified Kernel Checking**: Single `linux_kernel.py` handles all Linux distributions
- **API Caching**: LRU caching on GitHub and Docker Hub API calls for ~383,000x speedup on repeated calls
- **Security**: No shell=True in subprocess calls - all commands use list-based construction to prevent command injection
- **Concurrent Execution**: ThreadPoolExecutor for parallel version checking with thread-safe row writes

## Database Schema

### `applications` table
One row per `{name, instance}` pair (`UNIQUE(name, instance)`). Columns (snake_case) map to PascalCase in code via `FIELD_MAP` in `version_manager.py`:

| Column | PascalCase (code) | Description |
| ------ | ----------------- | ----------- |
| `name` | `Name` | Application identifier (lowercase, hyphenated) |
| `enabled` | `Enabled` | Boolean (stored as 0/1) to enable/disable from checks |
| `context` | `Context` | kubectl context override |
| `namespace` | `Namespace` | Kubernetes namespace override |
| `instance` | `Instance` | Instance name (e.g., prod, morgspi) |
| `type` | `Type` | Application type |
| `category` | `Category` | Category grouping |
| `version_pin` | `Version_Pin` | `latest` = no manifest pin; `pinned` = version hardcoded in manifest; other = channel pin (e.g. `beta`, `18-standard-trixie`) |
| `upgrade` | `Upgrade` | Upgrade method: `ansible-manifest` (update manifest + AWX), `ansible-helm` (AWX only), `ansible-apt` (apt via AWX), `ansible-cr` (update manifest + kubectl apply), `ansible-esphome` (ESPHome device OTA via AWX) |
| `extra_manifests` | `Extra_Manifests` | JSON-encoded list of extra manifest paths (relative to k3s-config root) updated alongside the main manifest during `ansible-cr` upgrades |
| `target` | `Target` | Full URL (`https://hostname:port`) |
| `esphome_key` | `Esphome_Key` | ESPHome Noise PSK (base64-encoded) for encrypted API connections |
| `github` | `GitHub` | GitHub repo path (owner/repo) |
| `dockerhub` | `DockerHub` | Docker Hub repo path (org/image) |
| `current_version` | `Current_Version` | Detected current version |
| `latest_version` | `Latest_Version` | Latest available version |
| `status` | `Status` | Status string (see Status Icons) |
| `last_checked` | `Last_Checked` | Timestamp of last check |
| `last_upgraded` | `Last_Upgraded` | Timestamp of last successful upgrade (also recorded per-event in `transactions`) |
| `check_current` | `Check_Current` | Method for current version detection |
| `check_latest` | `Check_Latest` | Method for latest version lookup |
| `library_github` | `Library_GitHub` | GitHub repo path for the ESPHome project library (e.g. `konnected-io/konnected-esphome`) — used by airgradient and konnected to track library version separately from ESPHome version |
| `current_library_version` | `Current_Library_Version` | Current version of the ESPHome project library running on the device |
| `latest_library_version` | `Latest_Library_Version` | Latest available version of the ESPHome project library |
| `notes` | `Notes` | Free-text notes field (e.g. set to "Firmware update available" for OPNsense) |

### `transactions` table
One row per upgrade actually triggered (mirrors every `Last_Upgraded` write in `upgrade_application()`), giving full history instead of a single overwritten timestamp:

| Column | Description |
| ------ | ----------- |
| `id` | Autoincrement primary key |
| `application_id` | FK to `applications.id` |
| `name`, `instance` | Denormalized so history survives even if the app row is later edited/removed |
| `upgrade_method` | The concrete method used (`ansible-manifest`, `ansible-helm`, `ansible-apt`, `ansible-cr`, `ansible-esphome`, `ansible-llm`) |
| `from_version`, `to_version` | `Current_Version`/`Latest_Version` at the moment the upgrade was triggered |
| `timestamp` | When the upgrade was triggered |
| `detail` | Optional free text (e.g. "covered by shared vault upgrade workflow") |

`VersionManager.log_transaction()` writes these rows; only real (non-dry-run), successfully-triggered upgrades are logged — not every version check. `VersionManager.get_transaction_history(limit=40, name="", instance="", fuzzy_name=False)` reads them back (most recent first, hard-capped at 40 by default). `name`/`instance` match exactly (case-insensitive), matching the semantics of `find_application_rows_by_name` — except `fuzzy_name=True`, which switches `name` to a substring (`LIKE`) match; used by the TUI's live filter box so a partial app name narrows results while typing instead of requiring the exact name. `VersionManager.show_history()` prints the CLI table view.

### Field Name Mapping
The codebase uses PascalCase internally; the database uses snake_case columns. The `FIELD_MAP` dict in `version_manager.py` handles bidirectional translation via `get_row_data()`/`update_row_data()`.

### Adding a New Application Row
- `name` should be lowercase with no hyphens where possible (e.g. `homeassistant` not `home-assistant`)
- The AWX app_name key is constructed as `{name}-{instance}` and **must match** the corresponding key in `k3s_applications.yml`
- New rows can be inserted directly via `sqlite3` (e.g. `INSERT OR REPLACE INTO applications (...) VALUES (...)`) — there is currently no TUI/CLI "create" flow, only `e` (edit) for existing rows

## Key Patterns

### Multi-Instance Support
Applications can have multiple instances tracked separately (one note per instance):
- **Home Assistant**: prod, morgspi, mudderpi
- **Kopia**: ssd, hdd, b2 (backup nodes)
- **Zigbee2MQTT**: zigbee11, zigbee15
- **Telegraf**: vm, graylog
- **Konnected**: car, workshop
- **Traefik**: prod, mudderpi, morgspi
- **PostgreSQL**: grafana-prod, hertzbeat-prod, homeassistant-prod (CNPG clusters)
- **UniFi Network**: application (Network Application version), uos (UniFi OS Server firmware version)
- **BLE Proxy**: bedroom, garage, greatroom, studio-a, workshop

### Check Methods (Split Architecture)
The system uses two separate fields for version checking:

#### Current Version Methods (`check_current`)
| Method | Description | Example Applications |
| ------ | ----------- | -------------------- |
| `api` | REST API calls for version info | Web-based applications with API endpoints |
| `ssh` | SSH connections showing OS + kernel | Remote servers and systems |
| `kubectl` | Kubernetes operations (pod queries, node info) | Containerized applications in Kubernetes |
| `command` | Shell commands | Applications with command-line version output |
| `mqtt` | MQTT subscription | Applications publishing version via MQTT |

#### Latest Version Methods (`check_latest`)
| Method | Description | Example Applications |
| ------ | ----------- | -------------------- |
| `github_release` | GitHub releases API | Open source projects with GitHub releases |
| `github_tag` | GitHub tags API | Projects using Git tags for versioning |
| `docker_hub` | Docker Hub/container tags | Containerized applications on Docker Hub |
| `ssh_apt` | SSH apt update checking | Linux systems with APT package manager |
| `proxmox` | Proxmox-specific API | Proxmox virtualization platforms |
| `opnsense` | OPNsense firmware update logic | OPNsense firewall systems |
| `tailscale` | Tailscale device update tracking | Tailscale VPN networks |
| `helm_chart` | Helm chart app version | Applications distributed via Helm |
| `unifi_network` | UniFi Network community GraphQL API | UniFi Network Application |
| `unifi_os_server` | UniFi Network community GraphQL API | UniFi OS Server firmware |
| `graylog_compat` | Graylog compatibility matrix | OpenSearch version compatible with Graylog |
| `none` | No latest version checking | Applications without available update sources |

#### Source Preference Logic
- **Docker Hub Priority**: When both GitHub and DockerHub fields are populated, system prefers Docker Hub for latest version
- **Automatic Fallback**: Falls back to GitHub if Docker Hub check fails or returns no result
- **Repository Flexibility**: Both GitHub and DockerHub fields can be populated regardless of `check_latest` method

### Status Icons & Meanings
- **✅ Up to Date**: Current matches latest
- **⚠️ Update Available**: Current behind latest
- **📋 Latest Available**: Only latest known (no current)
- **📌 Current Version**: Only current known (no comparison)
- **❓ Unknown**: Unable to determine

## Modular Architecture

### Checker Organization
- **Individual modules**: Each service type has its own file in `src/checkers/`
- **Shared utilities**: Common HTTP helper functions in `src/checkers/utils.py`
- **Clean imports**: Main manager imports from modular checkers
- **Key modules**:
  - `src/checkers/base.py`: Base classes (KubernetesChecker, APIChecker)
  - `src/checkers/github.py`: GitHub release and tag API functions
  - `src/checkers/kubectl.py`: Kubernetes-based version checkers
  - `src/checkers/dockerhub.py`: Docker Hub tag lookups (with beta support)
  - `src/checkers/utils.py`: Shared utilities (HTTP requests, version parsing, error handling)

## Configuration Patterns

### Repository Field Management
- **Separate fields**: GitHub and DockerHub repository paths in dedicated columns
- **GitHub field**: `owner/repository-name` format
- **DockerHub field**: `organization/image-name` format
- **Direct usage**: Field values used by checkers based on `check_latest` method without hardcoding

### URL Handling
- **Rows store complete URLs**: Full URLs with https:// protocols in `target` column
- **Direct usage**: URLs passed directly to HTTP request functions
- **Format**: `https://hostname.domain.com` or `https://ip-address:port`

### Configuration Management
- **config.py**: Centralized configuration and credential storage (loads `.env` file)
- **Database**: `config.DATABASE_PATH` (env: `DATABASE_PATH`, default: `data/version_checker.db` inside the repo)
- **MQTT**: `config.MQTT_BROKER`, `config.MQTT_USERNAME`, `config.MQTT_PASSWORD`
- **Home Assistant**: `config.HA_TOKENS` dictionary by instance
- **OPNsense**: `config.OPNSENSE_API_KEY`, `config.OPNSENSE_API_SECRET`
- **AWX**: `config.AWX_API_TOKENS` dict by instance (env: `AWX_API_TOKEN_PROD`, etc.)
- **k3s-config**: `config.K3S_CONFIG_FOLDER` (env: `K3S_CONFIG_FOLDER`, default: `/Users/dang/Documents/Development/k3s-config`) — root of the k3s manifest repository used for pinned-version upgrades
- **GitHub API**: `config.GITHUB_API_TOKEN` for rate limit avoidance (60/hour unauthenticated vs 5,000/hour authenticated)
- **Tailscale**: `config.TAILSCALE_ACCESS_TOKEN`, `config.TAILSCALE_TAILNET`
- **Graylog**: `config.GRAYLOG_TOKENS` dict by instance, `config.GRAYLOG_USERNAME`/`config.GRAYLOG_PASSWORD`
- **UniFi Network**: `config.UNIFI_NETWORK_API_KEY`
- **Syncthing**: `config.SYNCTHING_API_KEYS` dict by instance
- **Uptime Kuma**: `config.UPTIME_KUMA_USERNAME`, `config.UPTIME_KUMA_PASSWORD`

### AWX Upgrade Integration
- **AWX base URL**: `https://awx-prod.goepp.net`, k3s job template ID: 32, ESPHome job template ID: 31
- **app_name key**: Constructed as `{name}-{instance}` (e.g. `homeassistant-prod`) — **must match** the key in `k3s_applications.yml`
- **extra_vars**: Sent as a JSON string: `{"extra_vars": "{\"app_name\": \"homeassistant-prod\"}"}`
- **AWX survey**: Uses free `text` type — no hardcoded allowlist, accepts any app_name
- **AWX trigger**: Automatic when `upgrade` is `ansible-manifest` or `ansible-helm`; no separate `awx` field needed
- **`ansible-manifest`** upgrade method: updates the manifest file in k3s-config repo (git add/commit/push), then triggers AWX
- **`ansible-helm`** upgrade method: triggers AWX directly (no manifest update)
- **`ansible-esphome`** upgrade method: triggers AWX job template 31 with `target_pattern=<app_name>`; fires once for all instances (does not wait for job completion due to long compile times)
- **`ansible-apt`** upgrade method: triggers AWX job template 47 (server apt upgrade). For k3s servers (`category: Kubernetes`), a **kernel-only** pending update (`latest_version` == `0 packages + kernel`) is skipped — those nodes reboot for kernel upgrades via separate orchestration, and a plain `apt upgrade` holds back the new kernel anyway. k3s servers still upgrade when real packages are pending (`N packages` or `N packages + kernel`). `--force` bypasses this skip.
- **`--force`** flag: skips version comparison and manifest file update, goes straight to AWX trigger
- **k3s_applications.yml**: All entries are individual `manifest` or `helm` entries — no `manifest-multi` looping. Each entry is `{name}-{instance}` keyed independently

### Kubernetes Integration
- **Context-aware**: kubectl context per application via `context` column
- **Namespace-aware**: Namespace per application via `namespace` column
- **Pod discovery**: `kubectl get pods` with JSON output parsing
- **Command execution**: `kubectl exec` for version commands

## Version Parsing Patterns

### GitHub Releases
- Remove 'v' prefix: `v1.5.0` → `1.5.0`
- Use `tag_name` from latest release API

### Application-Specific Parsing
- **Telegraf**: `Telegraf 1.35.4 (git: HEAD@c93eb6a0)` → `1.35.4`
- **K3s**: `v1.33.2+k3s1` → `1.33.2+k3s1`
- **Kopia**: Strip build info after version number
- **ESPHome**: JSON response with version field
- **pgAdmin**: `REL-9_8` → `9.8` (GitHub tag format conversion)
- **PostgreSQL**: `PostgreSQL 17.2 (Debian...)` → `17.2` (SQL query parsing)
- **CloudNativePG**: `ghcr.io/cloudnative-pg/cloudnative-pg:1.25.0` → `1.25.0` (container image tag)
- **Grafana**: `{"version":"12.0.2",...}` → `12.0.2` (internal health API JSON parsing)
- **Vault**: `{"version":"1.18.4",...}` → `1.18.4` (sys/health API JSON parsing)

### MQTT Version Discovery
- **Topic pattern**: `{instance}/bridge/info`
- **JSON payload**: Extract `version` field
- **Timeout**: 2-second wait for message

### SSH-based Kernel Checking (ssh_apt method)
- **current_version**: Shows "OS Name - Kernel Version" (e.g. "Ubuntu 24.04.3 LTS - 6.8.0-79-generic")
- **latest_version**: Shows "No updates" or "Update available"
- **Unified Logic**: Single `linux_kernel.py` handles Ubuntu and Raspberry Pi
- **Package Detection**: Checks `linux-image-generic` (Ubuntu) and `raspberrypi-kernel` (RPi)
- **apt update**: Runs `apt-get update -q > /dev/null 2>&1` silently before `apt list --upgradable` to ensure fresh package data

## Shell Autocomplete
Tab completion for `--app` and `--instance` is provided via `argcomplete`. The registration line lives in `~/.oh-my-zsh/custom/shortcuts.zsh`:
```zsh
eval "$(/Users/dang/Documents/Development/version-checker/.venv/bin/register-python-argcomplete check_versions.py)"
```
`--instance` completions are filtered to the selected `--app` when both are provided.

## Terminal UI
`check_versions.py --tui` launches a full-screen Textual app (`src/tui/app.py`) that wraps `VersionManager` — it calls the exact same `check_all_applications()` / `upgrade_application()` methods the CLI uses, no parallel logic. It starts in an "Updates" view (only apps with `status: Update Available`), which is a read filter over `vm.notes`, not a separate data source.
- **Navigation**: `↑`/`↓` moves the DataTable cursor; `Space` toggles selection (marked with `✓`) on the highlighted row; `a` selects/deselects all currently visible rows
- **`v`**: toggles between "Updates" view and "All Applications" view
- **`c`**: runs a full check-all (`vm.check_all_applications()`) in a background thread; stdout from the manager is redirected into the on-screen `RichLog` panel via `contextlib.redirect_stdout`
- **`C`** (Shift+C): rechecks only the selected rows (or the highlighted row if nothing is selected) via `vm.check_single_application(idx)` per row — avoids a full check-all just to see whether one app changed. Bound as literal `"C"`, not `"shift+c"` — most terminals send a bare capital letter for Shift+(any letter) rather than a distinct modifier combo, and Textual's `"shift+c"` binding only matches terminals using an extended keyboard protocol (e.g. Kitty), so it silently never fires in a normal terminal
- **`u`**: upgrades every selected row — for each, calls `vm.upgrade_application(name, instance=instance)` (no `force`, so existing skip logic for "already up to date" / kernel-only apt updates still applies); requires confirmation via a modal dialog before running (upgrades can commit/push to the k3s-config repo and trigger AWX jobs, so confirmation is deliberate). After all upgrades are triggered, each affected row is automatically rechecked — since AWX upgrades run asynchronously, this recheck may still show the pre-upgrade version if the job hasn't rolled out yet; use `C` later to check again
- **`e`**: opens `EditScreen`, a modal form (`src/tui/app.py`) with every field from `vm.get_row_data(idx)` on the single highlighted row (`Enabled` is a `Switch`, everything else an `Input`; `Extra_Manifests` is edited as one manifest path per line). Save diffs the form against the original values and calls `vm.update_row_data(idx, updates)` with only the changed fields; Cancel/Escape discards. This is a synchronous DB write with no network/subprocess calls, so it runs on the main thread — not through `_run_background()`
- **`h`**: opens `HistoryScreen`, a full-screen modal listing rows from the `transactions` table (most recent first, hard-capped at 40 — `HISTORY_LIMIT` in `src/tui/app.py`) via `vm.get_transaction_history()` — Timestamp, Name, Instance, Method, From, To, Detail columns. Focus starts in a filter `Input` at the top; typing live-narrows results by app name (substring match, `fuzzy_name=True`) via `on_input_changed`, re-querying and clearing/repopulating the table on every keystroke. Read-only; `Escape` closes it. Not scoped to the row highlighted in the main table — it always starts unfiltered
- **`r`**: refreshes the visible list from current in-memory row state
- Long-running operations (`c`, `C`, `u`) run via `App.run_worker(..., thread=True)` since the underlying checks/upgrades are blocking network/subprocess calls; UI updates from the worker thread go through `call_from_thread`
- **Confirm dialog default**: the upgrade confirmation modal defaults focus to "Cancel" (not the destructive action) so pressing Enter without deliberately tabbing to "Upgrade" is safe
- **Background work always clears busy state**: Textual widgets treat `disabled or loading` as "non-interactive", so `table.loading = True` while a background op runs also blocks arrow-key/selection input on the DataTable. All background work goes through `_run_background()`, which wraps the call in `try/except` (logging any exception into the RichLog instead of losing it) and a `finally` that guarantees `_on_background_done()` — and therefore `table.loading = False` — always runs, even if `vm.check_single_application()` / `vm.upgrade_application()` raises. Without this, any exception (a real possibility against live infra — timeouts, unexpected API responses) permanently freezes the table with no visible error
- **Focus must be explicitly restored after background work**: Textual's `Widget.focusable` excludes any widget with `loading = True`, so during a long-running check/upgrade the DataTable becomes unfocusable and focus can drift elsewhere (e.g. to the `RichLog`, which is also focusable). Textual does not automatically restore focus once `loading` clears, so a long real-world wait (AWX jobs can poll for minutes) can leave focus stranded off the table — arrow keys then get consumed by whatever now has focus (or nothing) instead of moving the table cursor, while unrelated app-level bindings (`v`, `c`, `q`) keep working since they don't depend on which widget is focused. `_on_background_done()` explicitly calls `self.query_one(DataTable).focus()` to make the restoration deterministic instead of relying on Textual's focus-chain behavior
- **Live progress lines**: some checker code (e.g. `wait_for_awx_job` in `upgrade.py`) uses `print(..., end="")` to append dots to the same terminal line while polling. `RichLog.write()` has no such concept — every call adds a new line — so `_LogWriter` buffers any text with no trailing newline and shows it in a separate one-line `#status` `Static` widget that gets updated in place; only completed (newline-terminated) lines get appended to the scrolling `RichLog`
- **`_LogWriter` thread-safety**: `redirect_stdout` patches `sys.stdout` process-wide, not per-thread, so a stray `print()` on the app's own thread during a background operation must fall back to a direct widget write instead of `call_from_thread` (which raises if called from the app's own thread)

## Command Interface
```bash
# Check all applications
./check_versions.py --check-all

# Check all with custom worker count
./check_versions.py --check-all --workers 20

# Launch the interactive terminal UI (starts in Updates view)
./check_versions.py --tui

# Show summary with status counts
./check_versions.py --summary

# List all applications in table format
./check_versions.py --list

# List only applications with updates available
./check_versions.py --updates

# Show upgrade history (most recent 40 transactions)
./check_versions.py --history

# Show upgrade history filtered to one app (and optionally one instance) — reuses --app/--instance
./check_versions.py --history --app "grafana"
./check_versions.py --history --app "homeassistant" --instance prod

# Check specific application (all instances)
./check_versions.py --app "homeassistant"
./check_versions.py --app "kopia"
./check_versions.py --app "cnpg"
./check_versions.py --app "grafana"
./check_versions.py --app "vault"

# Check specific application, specific instance
./check_versions.py --app "homeassistant" --instance prod

# Use a custom database file
./check_versions.py --db /path/to/version_checker.db --check-all

# Upgrade an application (use --app with --upgrade flag)
# - version_pin='latest': triggers AWX job directly (if upgrade is ansible-manifest or ansible-helm)
# - version_pin='pinned': updates k3s manifest, then triggers AWX (if upgrade is ansible-manifest)
./check_versions.py --app "grafana" --upgrade
./check_versions.py --app "victoriametrics" --upgrade

# Upgrade a specific instance only
./check_versions.py --app "homeassistant" --instance prod --upgrade

# Dry-run upgrade (shows what would change without modifying anything)
./check_versions.py --app "grafana" --upgrade --dry-run

# Force AWX trigger even if already up to date or manifest unchanged
# For pinned: skips manifest update and goes straight to AWX
./check_versions.py --app "grafana" --upgrade --force
./check_versions.py --app "homeassistant" --instance prod --upgrade --force
```

## Development Patterns

### Adding New Applications
1. Insert a new row into the `applications` table via `sqlite3` directly (e.g. `INSERT OR REPLACE`); use lowercase no-hyphen `name` (e.g. `homeassistant` not `home-assistant`)
2. Set `check_current` and `check_latest` columns plus `target` URL
3. Populate both `github` and `dockerhub` columns when available (Docker Hub preferred automatically)
4. If the app uses AWX upgrade: set `upgrade: ansible-manifest` or `upgrade: ansible-helm`, and add a matching `{name}-{instance}` entry in `k3s_applications.yml`
5. Create or extend checker module in `src/checkers/` if needed
6. Import and wire up checker function in `version_manager.py`
7. Test with `--app` flag

### Repository Field Strategy
- **Populate Both**: Add both GitHub and DockerHub repositories when available
- **Docker Hub Preference**: System automatically prefers Docker Hub for containerized applications
- **Fallback Safety**: GitHub used as backup if Docker Hub fails
- **Method Independence**: `check_latest` can be `github_release`/`github_tag` while still preferring Docker Hub when both are populated

### Modular Development
- **New checker creation**: Add file to `src/checkers/` with focused functionality
- **Shared utilities**: Use `from .utils import http_get` for HTTP requests
- **Clean separation**: Keep service-specific logic in dedicated modules
- **Import pattern**: Import checker functions in `version_manager.py`
- **Unified approach**: `linux_kernel.py` handles all Linux distributions

### No Fallback Methods Rule
- **Single method implementation**: Once a working method is identified, implement only that method with proper error handling
- **No alternative approaches**: Avoid fallback logic that tries multiple methods when the primary fails
- **Clean failure**: If the intended method fails, let it fail cleanly rather than masking issues with fallbacks
- **Explicit behavior**: Makes debugging easier and keeps code focused on the intended approach

### Error Handling
- Print descriptive error messages with instance context
- Return None for failed version checks
- Use try/except with specific error types where possible
- Set reasonable timeouts (10-15 seconds)
- All subprocess calls use list-based command construction (never shell=True)
- Thread-safe note writes using threading.Lock() for concurrent operations

## Security Considerations
- **No hardcoded credentials** in version checking logic
- **config.py pattern** for credential centralization
- **Environment variables recommended** for production (.env.example provided)
- **Never commit actual credentials** to repository

## Testing Workflow
1. **Individual app testing**: `--app "name"`
2. **Full system test**: `--check-all`
3. **Status verification**: `--summary` and `--list`
4. **Row validation**: Check timestamps and version columns via `sqlite3 data/version_checker.db` after a check

## Technical Notes
- **Python Version**: Requires Python 3.13.7+ for clean operation (no urllib3 warnings)
- **Virtual Environment**: Recreate with new Python versions for optimal compatibility (~50MB smaller without pandas)
- **SSL/TLS**: Uses system OpenSSL with urllib3 v2.5.0+ for secure HTTPS requests
- **Code Organization**: Modular architecture with optimized checker modules
- **Row Persistence**: Rows are written individually after each check (no single save-all operation); `save_workbook()` is a no-op stub for interface compatibility
- **API Efficiency**: GitHub and Docker Hub API calls are cached using @lru_cache for massive performance improvement on multi-instance apps
- **Security**: All subprocess calls use list-based command construction to prevent command injection vulnerabilities
- **Concurrency**: ThreadPoolExecutor enables parallel version checking with thread-safe row writes via threading.Lock()
- **Kubernetes Integration**: Uses kubectl JSON output parsing instead of shell pipes for better performance and security
- **Thread-safe Output**: Concurrent checks buffer stdout per thread and flush atomically to avoid interleaved output

## Critical Database Handling Rules
- **NEVER use pandas or openpyxl**: The system uses a SQLite database (`src/db.py`)
- **Column mapping**: DB columns are snake_case; code uses PascalCase via `FIELD_MAP` in `version_manager.py`, translated by `get_row_data()`/`update_row_data()`
- **`enabled`** is stored as `0`/`1`, converted to/from `bool` on read/write
- **`extra_manifests`** is stored as JSON text, converted to/from a `list` on read/write
- **In-memory shape**: `VersionManager.notes` is `[{"id": <row id>, "frontmatter": {...}}, ...]` — the TUI reads `vm.notes[idx]["frontmatter"]` directly, so this shape must be preserved by any future storage change
- **Database path**: Set via `DATABASE_PATH` env var; default is `data/version_checker.db` inside the repo (gitignored)
