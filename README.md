# Goepp Homelab Version Manager

A comprehensive Python-based system for tracking software versions across your infrastructure using a local SQLite database for data management.

## Features

- **SQLite-Backed**: Application state and full upgrade history stored in a local SQLite database
- **Multi-Instance Support**: Track multiple instances of the same application across environments
- **Modular Architecture**: Base classes (KubernetesChecker, APIChecker) for efficient code reuse
- **Dual Check Method Architecture**:
  - **Current Version**: API calls, SSH connections, Kubernetes queries, MQTT subscriptions
  - **Latest Version**: GitHub releases/tags, Docker Hub, custom APIs, platform updates
- **Automated Upgrades**: Trigger AWX-based upgrades for applications with pinned or latest version tracking
- **Visual Status Indicators**: Emoji icons for quick status recognition (✅⚠️📋❓)
- **Automated Tracking**: Tracks current vs latest versions with timestamps
- **Performance Optimizations**:
  - API caching for GitHub and Docker Hub requests (~383,000x speedup on repeated calls)
  - Efficient kubectl JSON parsing instead of shell pipes
- **Security Hardening**: No shell=True in subprocess calls - all commands use list-based construction
- **Selective Checking**: Enable/disable field to skip applications without removing the row
- **Transaction History**: Every triggered upgrade is logged to a `transactions` table (method, from/to version, timestamp) instead of only keeping a single overwritten "last upgraded" value

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
# Or use the helper script:
# source activate.sh
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Update config.py with your credentials (based on existing pattern)

## Usage

### Command Line Interface

```bash
# Check all applications and instances
./check_versions.py --check-all

# Show summary with status icons
./check_versions.py --summary

# List all applications and instances
./check_versions.py --list

# List only applications needing updates
./check_versions.py --updates

# Check specific application (all instances)
./check_versions.py --app "appname"

# Check specific application, specific instance only
./check_versions.py --app "appname" --instance prod

# Upgrade an application (triggers AWX job)
# - version_pin=latest: triggers AWX directly
# - version_pin=pinned: updates manifest file first, then triggers AWX
./check_versions.py --app "appname" --upgrade

# Upgrade a specific instance only
./check_versions.py --app "appname" --instance prod --upgrade

# Dry-run: show what would happen without making changes
./check_versions.py --app "appname" --upgrade --dry-run

# Force AWX trigger even if already up to date
./check_versions.py --app "appname" --upgrade --force

# Use a custom database file
./check_versions.py --db /path/to/version_checker.db --check-all
```

### Terminal UI

```bash
./check_versions.py --tui
```

Launches a full-screen, keyboard-driven interface (built with [Textual](https://textual.textualize.io/)) for browsing and upgrading applications. It starts in "Updates" mode, listing only applications with an available update.

| Key | Action |
| --- | ------ |
| `↑` / `↓` | Move the cursor through the list |
| `Space` | Toggle selection of the highlighted application |
| `a` | Select/deselect all visible applications |
| `v` | Toggle between "Updates" view and "All Applications" view |
| `c` | Run a check-all across every enabled application |
| `Shift+C` | Recheck just the selected (or highlighted) application(s) — no full check-all needed |
| `u` | Upgrade all selected applications (with confirmation prompt); automatically rechecks each afterward |
| `e` | Edit every field of the highlighted application in a form |
| `r` | Refresh the list from current data |
| `q` | Quit |

The TUI is a view/control layer on top of the same `VersionManager` used by the CLI — it does not change any existing check or upgrade behavior.

## Database Structure

State lives in a SQLite database (default `data/version_checker.db`, path configurable via `DATABASE_PATH`). See `src/db.py` for the full schema.

### `applications` table
One row per `(name, instance)` pair:

- **`name`**: Application name (lowercase, e.g. `homeassistant`, `grafana`)
- **`enabled`**: Boolean field to enable/disable checking (skips disabled apps for efficiency)
- **`instance`**: Specific instance (ssd, hdd, b2, prod, etc.)
- **`type`**: Application type/category
- **`category`**: Infrastructure category
- **`version_pin`**: `latest` = no manifest pin; `pinned` = version hardcoded in manifest; other = channel pin (e.g. `beta`)
- **`upgrade`**: Upgrade method (`ansible-manifest`, `ansible-helm`, `ansible-apt`, `ansible-cr`, `ansible-esphome`, `ansible-llm`)
- **`target`**: Full URL connection endpoint (`https://hostname:port`)
- **`github`**: GitHub repository path (owner/repo format)
- **`dockerhub`**: Docker Hub repository path (org/image format)
- **`current_version`**: Currently running version
- **`latest_version`**: Latest available version
- **`status`**: Up to Date, Update Available, etc.
- **`last_checked`**: Timestamp of last check
- **`last_upgraded`**: Timestamp of last successful upgrade
- **`check_current`**: How current versions are retrieved (api, ssh, kubectl, etc.)
- **`check_latest`**: How latest versions are retrieved (github_release, docker_hub, etc.)
- **`esphome_key`**: ESPHome Noise PSK for encrypted API connections

### `transactions` table
One row per upgrade actually triggered — `name`, `instance`, `upgrade_method`, `from_version`, `to_version`, `timestamp`, `detail` — giving a full audit trail instead of a single overwritten `last_upgraded` value. Written by `VersionManager.log_transaction()`.

### Migrating from the old Obsidian vault
`migrate_vault_to_sqlite.py` is a one-time, read-only importer for anyone still on the legacy markdown-notes storage: `./migrate_vault_to_sqlite.py --vault /path/to/vault/Software`. It never modifies the `.md` files and is safe to re-run.

## Supported Check Methods

### Current Version Methods (`Check_Current`)
- **`api`**: REST API calls for web-based applications with API endpoints
- **`ssh`**: SSH connections to remote servers and systems (shows OS + kernel info)
- **`kubectl`**: Kubernetes operations for containerized applications (pod queries, node info)
- **`command`**: Shell commands for applications with command-line version output
- **`mqtt`**: MQTT subscription for applications publishing version via MQTT

### Latest Version Methods (`Check_Latest`)
- **`github_release`**: GitHub releases API for open source projects with GitHub releases
- **`github_tag`**: GitHub tags API for projects using Git tags for versioning
- **`docker_hub`**: Docker Hub/container tags for containerized applications on Docker Hub
- **`ssh_apt`**: SSH apt update checking for Linux systems with APT package manager
- **`proxmox`**: Proxmox-specific API for Proxmox virtualization platforms
- **`opnsense`**: OPNsense firmware update logic for OPNsense firewall systems
- **`tailscale`**: Tailscale device update tracking for Tailscale VPN networks
- **`none`**: No latest version checking for applications without available update sources

### Application Types Supported
- **Web Applications** - Applications with REST API endpoints
- **Containerized Applications** - Kubernetes-deployed applications with pod monitoring
- **Backup Software** - Multi-node backup systems with instance tracking
- **Network Infrastructure** - Reverse proxies, load balancers, and networking components
- **IoT Platforms** - Device management and automation platforms
- **Database Systems** - Document databases, time-series databases, and operators
- **Monitoring & Logging** - Metrics collection, log processing, and visualization platforms
- **Security Systems** - Firewalls, VPN networks, and access control systems
- **Virtualization Platforms** - Hypervisors and cluster management systems
- **Linux Systems** - Server and device kernel monitoring with package management

### Multi-Instance Support
Applications that run across multiple environments are tracked separately by instance:
- Each instance gets its own database row with individual version tracking
- Supports various instance types (production, staging, node-specific, environment-specific)
- Instance names are configurable and can represent servers, environments, or components

## Security Notes

- Uses existing config.py pattern for credentials
- Never commits actual credentials to git
- Follows your established authentication patterns (Bearer tokens, API keys, etc.)


## Files in Project

- **`version_manager.py`** - Core Python class handling all version checking logic
- **`check_versions.py`** - Command-line interface with multi-instance support
- **`migrate_vault_to_sqlite.py`** - One-time, read-only importer from the legacy Obsidian vault into SQLite
- **`requirements.txt`** - Python dependencies (requests, paho-mqtt, PyYAML, textual)
- **`config.py`** - Configuration and credentials (not committed to git)
- **`src/db.py`** - SQLite schema and connection helper
- **`src/tui/`** - Interactive terminal UI (Textual app), launched via `--tui`
- **`src/checkers/`** - Directory containing modular version checker modules
  - **`base.py`** - Base classes (KubernetesChecker, APIChecker) with secure subprocess handling
  - **`github.py`** - GitHub release and tag API functions with LRU caching
  - **`dockerhub.py`** - Docker Hub version checking with LRU caching
  - **`kubectl.py`** - Kubernetes-based version checkers using JSON output parsing
  - **`upgrade.py`** - AWX job triggering and manifest version update logic
  - **`utils.py`** - Shared utilities (HTTP requests, version parsing, error handling)
  - Additional specialized checkers for specific application types and platforms
- **`data/`** - SQLite database file lives here by default (not committed to git)
- **`.venv/`** - Virtual environment (not committed to git)

## Quick Start Example:
```bash
# Activate virtual environment
source .venv/bin/activate

# Check all applications
./check_versions.py --check-all

# Show summary with visual status icons
./check_versions.py --summary

# Upgrade a specific application
./check_versions.py --app "grafana" --upgrade

# Dry-run an upgrade to see what would happen
./check_versions.py --app "grafana" --upgrade --dry-run
```
