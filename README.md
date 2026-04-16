# Goepp Homelab Version Manager

A comprehensive Python-based system for tracking software versions across your infrastructure using Obsidian vault markdown notes for data management.

## Features

- **Obsidian Integration**: Uses Obsidian vault markdown notes with YAML frontmatter for data management
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
  - Concurrent version checking using ThreadPoolExecutor
  - Efficient kubectl JSON parsing instead of shell pipes
- **Security Hardening**: No shell=True in subprocess calls - all commands use list-based construction
- **Selective Checking**: Enable/disable field to skip applications without removing from vault

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

# Check all with custom concurrent worker count
./check_versions.py --check-all --workers 20

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
```

## Obsidian Note Structure

Each application is stored as a `.md` file in the Obsidian vault with YAML frontmatter fields:

- **`name`**: Application name (lowercase, e.g. `homeassistant`, `grafana`)
- **`enabled`**: Boolean field to enable/disable checking (skips disabled apps for efficiency)
- **`instance`**: Specific instance (ssd, hdd, b2, prod, etc.)
- **`type`**: Application type/category
- **`category`**: Infrastructure category
- **`version_pin`**: `latest` = no manifest pin; `pinned` = version hardcoded in manifest; other = channel pin (e.g. `beta`)
- **`upgrade`**: Upgrade method (`ansible-manifest`, `ansible-helm`, `ansible-apt`)
- **`awx`**: Boolean — whether to trigger an AWX job during `--upgrade`
- **`target`**: Full URL connection endpoint (`https://hostname:port`)
- **`github`**: GitHub repository path (owner/repo format)
- **`dockerhub`**: Docker Hub repository path (org/image format)
- **`current_version`**: Currently running version
- **`latest_version`**: Latest available version
- **`status`**: Up to Date, Update Available, etc.
- **`last_checked`**: Timestamp of last check
- **`check_current`**: How current versions are retrieved (api, ssh, kubectl, etc.)
- **`check_latest`**: How latest versions are retrieved (github_release, docker_hub, etc.)
- **`key`**: Unique identifier or API key for the application instance

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
- Each instance gets its own markdown note file with individual version tracking
- Supports various instance types (production, staging, node-specific, environment-specific)
- Instance names are configurable and can represent servers, environments, or components

## Security Notes

- Uses existing config.py pattern for credentials
- Never commits actual credentials to git
- Follows your established authentication patterns (Bearer tokens, API keys, etc.)


## Files in Project

- **`version_manager.py`** - Core Python class handling all version checking logic with concurrent execution
- **`check_versions.py`** - Command-line interface with multi-instance support
- **`requirements.txt`** - Python dependencies (requests, paho-mqtt, PyYAML)
- **`config.py`** - Configuration and credentials (not committed to git)
- **`src/checkers/`** - Directory containing modular version checker modules
  - **`base.py`** - Base classes (KubernetesChecker, APIChecker) with secure subprocess handling
  - **`github.py`** - GitHub release and tag API functions with LRU caching
  - **`dockerhub.py`** - Docker Hub version checking with LRU caching
  - **`kubectl.py`** - Kubernetes-based version checkers using JSON output parsing
  - **`upgrade.py`** - AWX job triggering and manifest version update logic
  - **`utils.py`** - Shared utilities (HTTP requests, version parsing, error handling)
  - Additional specialized checkers for specific application types and platforms
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
