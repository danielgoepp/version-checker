# Version Check Module

## Overview
Obsidian-based software version monitoring system with multi-instance support for tracking various applications across the Goepp Lab infrastructure.

Note: This is for my specific infrastructure only, not a general purpose app. The only reason I make this a public repository is for reference only. If one were to take this code and try to make it work for them, significant changes would be needed to customize it. Unless of course you run the exact tech stack in the exact same way I do.

## Architecture
- **Language**: Python
- **Database**: Obsidian vault markdown notes in `OBSIDIAN_VAULT_FOLDER` (default: `/Users/dang/Documents/Goeppedia/Software`)
- **Note Format**: Each application is a `.md` file with YAML frontmatter containing all version data
- **Modular Design**: Individual checkers in `src/checkers/` directory with shared utilities
- **CLI Interface**: `check_versions.py` for command-line operations
- **Virtual Environment**: Always use `source .venv/bin/activate`
- **Unified Kernel Checking**: Single `linux_kernel.py` handles all Linux distributions
- **API Caching**: LRU caching on GitHub and Docker Hub API calls for ~383,000x speedup on repeated calls
- **Security**: No shell=True in subprocess calls - all commands use list-based construction to prevent command injection
- **Concurrent Execution**: ThreadPoolExecutor for parallel version checking with thread-safe note writes

## Obsidian Note Structure

### YAML Frontmatter Fields
Each `.md` note in the vault uses these frontmatter keys (snake_case):

| YAML Key | PascalCase (code) | Description |
| -------- | ----------------- | ----------- |
| `name` | `Name` | Application identifier (lowercase, hyphenated) |
| `enabled` | `Enabled` | Boolean to enable/disable from checks |
| `context` | `Context` | kubectl context override |
| `namespace` | `Namespace` | Kubernetes namespace override |
| `instance` | `Instance` | Instance name (e.g., prod, morgspi) |
| `type` | `Type` | Application type |
| `category` | `Category` | Category grouping |
| `version_pin` | `Version_Pin` | `latest` = no manifest pin; `pinned` = version hardcoded in manifest; other = channel pin (e.g. `beta`, `18-standard-trixie`) |
| `upgrade` | `Upgrade` | Upgrade method: `ansible-manifest` (update manifest + AWX), `ansible-helm` (AWX only), `ansible-apt` (apt via AWX) |
| `awx` | `AWX` | Boolean — gates whether AWX is triggered during `--upgrade`. Set `false` for apps not in k3s_applications.yml |
| `target` | `Target` | Full URL (`https://hostname:port`) |
| `esphome key` | `Esphome_Key` | ESPHome Noise PSK (base64-encoded) for encrypted API connections |
| `github` | `GitHub` | GitHub repo path (owner/repo) |
| `dockerhub` | `DockerHub` | Docker Hub repo path (org/image) |
| `current_version` | `Current_Version` | Detected current version |
| `latest_version` | `Latest_Version` | Latest available version |
| `status` | `Status` | Status string (see Status Icons) |
| `last_checked` | `Last_Checked` | Timestamp of last check |
| `last_upgraded` | `Last_Upgraded` | Timestamp of last successful AWX upgrade |
| `check_current` | `Check_Current` | Method for current version detection |
| `check_latest` | `Check_Latest` | Method for latest version lookup |

### Field Name Mapping
The codebase uses PascalCase internally; YAML frontmatter uses snake_case. The `FIELD_MAP` dict in `version_manager.py` handles bidirectional translation. Always use snake_case in note frontmatter.

### Note Example
```yaml
---
name: homeassistant
enabled: true
instance: prod
type: application
category: home-automation
version_pin: pinned
upgrade: ansible-manifest
awx: true
target: https://homeassistant.goepp.net
github: home-assistant/core
dockerhub: homeassistant/home-assistant
current_version: 2025.1.0
latest_version: 2025.1.2
status: Update Available
last_checked: '2025-01-15 10:30:00'
check_current: api
check_latest: docker_hub
---
```

### Note Naming Convention
- Note files are named `{name}-{instance}.md` (e.g. `homeassistant-prod.md`)
- The `name` field must be lowercase with no hyphens where possible (e.g. `homeassistant` not `home-assistant`)
- The AWX app_name key is constructed as `{name}-{instance}` and **must match** the corresponding key in `k3s_applications.yml`

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

### Check Methods (Split Architecture)
The system uses two separate fields for version checking:

#### Current Version Methods (`check_current`)
| Method | Description | Example Applications |
|--------|-------------|---------------------|
| `api` | REST API calls for version info | Web-based applications with API endpoints |
| `ssh` | SSH connections showing OS + kernel | Remote servers and systems |
| `kubectl` | Kubernetes operations (pod queries, node info) | Containerized applications in Kubernetes |
| `command` | Shell commands | Applications with command-line version output |
| `mqtt` | MQTT subscription | Applications publishing version via MQTT |

#### Latest Version Methods (`check_latest`)
| Method | Description | Example Applications |
|--------|-------------|---------------------|
| `github_release` | GitHub releases API | Open source projects with GitHub releases |
| `github_tag` | GitHub tags API | Projects using Git tags for versioning |
| `docker_hub` | Docker Hub/container tags | Containerized applications on Docker Hub |
| `ssh_apt` | SSH apt update checking | Linux systems with APT package manager |
| `proxmox` | Proxmox-specific API | Proxmox virtualization platforms |
| `opnsense` | OPNsense firmware update logic | OPNsense firewall systems |
| `tailscale` | Tailscale device update tracking | Tailscale VPN networks |
| `helm_chart` | Helm chart app version | Applications distributed via Helm |
| `unifi_protect_rss` | UniFi Protect RSS feed | UniFi Protect firmware |
| `unifi_network_rss` | UniFi Network RSS feed | UniFi Network firmware |
| `unifi_os_nvr_rss` | UniFi OS NVR RSS feed | UniFi OS NVR firmware |
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
- **Separate fields**: GitHub and DockerHub repository paths in dedicated frontmatter keys
- **GitHub field**: `owner/repository-name` format
- **DockerHub field**: `organization/image-name` format
- **Direct usage**: Field values used by checkers based on `check_latest` method without hardcoding

### URL Handling
- **Notes store complete URLs**: Full URLs with https:// protocols in `target` field
- **Direct usage**: URLs passed directly to HTTP request functions
- **Format**: `https://hostname.domain.com` or `https://ip-address:port`

### Configuration Management
- **config.py**: Centralized configuration and credential storage (loads `.env` file)
- **Obsidian Vault**: `config.OBSIDIAN_VAULT_FOLDER` (env: `OBSIDIAN_VAULT_FOLDER`, default: `/Users/dang/Documents/Goeppedia/Software`)
- **MQTT**: `config.MQTT_BROKER`, `config.MQTT_USERNAME`, `config.MQTT_PASSWORD`
- **Home Assistant**: `config.HA_TOKENS` dictionary by instance
- **OPNsense**: `config.OPNSENSE_API_KEY`, `config.OPNSENSE_API_SECRET`
- **AWX**: `config.AWX_API_TOKENS` dict by instance (env: `AWX_API_TOKEN_PROD`, etc.)
- **k3s-config**: `config.K3S_CONFIG_FOLDER` (env: `K3S_CONFIG_FOLDER`, default: `/Users/dang/Documents/Development/k3s-config`) — root of the k3s manifest repository used for pinned-version upgrades
- **GitHub API**: `config.GITHUB_API_TOKEN` for rate limit avoidance (60/hour unauthenticated vs 5,000/hour authenticated)
- **Tailscale**: `config.TAILSCALE_API_KEY`, `config.TAILSCALE_TAILNET`
- **Graylog**: `config.GRAYLOG_TOKENS` dict by instance, `config.GRAYLOG_USERNAME`/`config.GRAYLOG_PASSWORD`
- **UniFi Protect**: `config.UNIFI_PROTECT_API_KEY`
- **UniFi Network**: `config.UNIFI_NETWORK_API_KEY`
- **Syncthing**: `config.SYNCTHING_API_KEYS` dict by instance
- **Uptime Kuma**: `config.UPTIME_KUMA_USERNAME`, `config.UPTIME_KUMA_PASSWORD`

### AWX Upgrade Integration
- **AWX base URL**: `https://awx-prod.goepp.net`, job template ID: 32
- **app_name key**: Constructed as `{name}-{instance}` (e.g. `homeassistant-prod`) — **must match** the key in `k3s_applications.yml`
- **extra_vars**: Sent as a JSON string: `{"extra_vars": "{\"app_name\": \"homeassistant-prod\"}"}`
- **AWX survey**: Uses free `text` type — no hardcoded allowlist, accepts any app_name
- **`awx: true`** frontmatter field required to trigger AWX; set `false` for apps not in k3s_applications.yml
- **`ansible-manifest`** upgrade method: updates the manifest file in k3s-config repo (git add/commit/push), then triggers AWX
- **`ansible-helm`** upgrade method: triggers AWX directly (no manifest update)
- **`--force`** flag: skips version comparison and manifest file update, goes straight to AWX trigger
- **k3s_applications.yml**: All entries are individual `manifest` or `helm` entries — no `manifest-multi` looping. Each entry is `{name}-{instance}` keyed independently

### Kubernetes Integration
- **Context-aware**: kubectl context per application via `context` frontmatter field
- **Namespace-aware**: Namespace per application via `namespace` frontmatter field
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
- **No apt update**: Uses `apt list --upgradable` without refreshing package lists

## Shell Autocomplete
Tab completion for `--app` and `--instance` is provided via `argcomplete`. The registration line lives in `~/.oh-my-zsh/custom/shortcuts.zsh`:
```zsh
eval "$(/Users/dang/Documents/Development/version-checker/.venv/bin/register-python-argcomplete check_versions.py)"
```
`--instance` completions are filtered to the selected `--app` when both are provided.

## Command Interface
```bash
# Check all applications
./check_versions.py --check-all

# Check all with custom worker count
./check_versions.py --check-all --workers 20

# Show summary with status counts
./check_versions.py --summary

# List all applications in table format
./check_versions.py --list

# List only applications with updates available
./check_versions.py --updates

# Check specific application (all instances)
./check_versions.py --app "homeassistant"
./check_versions.py --app "kopia"
./check_versions.py --app "cnpg"
./check_versions.py --app "grafana"
./check_versions.py --app "vault"

# Check specific application, specific instance
./check_versions.py --app "homeassistant" --instance prod

# Use a custom vault folder
./check_versions.py --vault /path/to/vault/Software --check-all

# Upgrade an application (use --app with --upgrade flag)
# - version_pin='latest': triggers AWX job directly
# - version_pin='pinned': updates k3s manifest, then triggers AWX (if awx: true)
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
1. Create a new `.md` file in the vault Software folder with appropriate YAML frontmatter
2. Name the file `{name}-{instance}.md`; use lowercase no-hyphen `name` (e.g. `homeassistant` not `home-assistant`)
3. Set `check_current` and `check_latest` fields plus `target` URL
4. Populate both `github` and `dockerhub` fields when available (Docker Hub preferred automatically)
5. If the app uses AWX upgrade: add a matching `{name}-{instance}` entry in `k3s_applications.yml` with the correct deployment method and manifest/helm details; set `awx: true` in the note
6. Create or extend checker module in `src/checkers/` if needed
7. Import and wire up checker function in `version_manager.py`
8. Test with `--app` flag

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
4. **Note validation**: Check frontmatter timestamps and version fields after a check

## Technical Notes
- **Python Version**: Requires Python 3.13.7+ for clean operation (no urllib3 warnings)
- **Virtual Environment**: Recreate with new Python versions for optimal compatibility (~50MB smaller without pandas)
- **SSL/TLS**: Uses system OpenSSL with urllib3 v2.5.0+ for secure HTTPS requests
- **Code Organization**: Modular architecture with optimized checker modules
- **Note Persistence**: Notes are written individually after each check (no single save-all operation); `save_workbook()` is a no-op stub for interface compatibility
- **API Efficiency**: GitHub and Docker Hub API calls are cached using @lru_cache for massive performance improvement on multi-instance apps
- **Security**: All subprocess calls use list-based command construction to prevent command injection vulnerabilities
- **Concurrency**: ThreadPoolExecutor enables parallel version checking with thread-safe note writes via threading.Lock()
- **Kubernetes Integration**: Uses kubectl JSON output parsing instead of shell pipes for better performance and security
- **Thread-safe Output**: Concurrent checks buffer stdout per thread and flush atomically to avoid interleaved output

## Critical Note Handling Rules
- **NEVER use pandas or openpyxl**: The system has migrated to Obsidian markdown notes
- **Note files are plain text**: Read with `path.read_text(encoding="utf-8")`
- **YAML frontmatter**: Fields are snake_case; code uses PascalCase via `FIELD_MAP`
- **Write back with yaml.dump**: Use `sort_keys=False` and `allow_unicode=True`
- **Note body preserved**: `_write_note()` currently writes only frontmatter (body is empty for version notes)
- **Vault folder**: Set via `OBSIDIAN_VAULT_FOLDER` env var; default is `/Users/dang/Documents/Goeppedia/Software`