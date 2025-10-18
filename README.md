# Goepp Homelab Version Manager

A comprehensive Python-based system for tracking software versions across your infrastructure using Excel for data management.

## Features

- **Excel Integration**: Uses Excel database with Name/Instance structure for data management
- **Multi-Instance Support**: Track multiple instances of the same application across environments
- **Modular Architecture**: Base classes (KubernetesChecker, APIChecker) for efficient code reuse
- **Dual Check Method Architecture**: 
  - **Current Version**: API calls, SSH connections, Kubernetes queries, MQTT subscriptions
  - **Latest Version**: GitHub releases/tags, Docker Hub, custom APIs, platform updates
- **Visual Status Indicators**: Emoji icons for quick status recognition (✅⚠️📋❓)
- **Automated Tracking**: Tracks current vs latest versions with timestamps
- **Flexible Interface**: Command-line and interactive modes

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

3. Update Excel file structure (if needed):
```bash
python3 update_excel.py
```

4. Update config.py with your credentials (based on existing pattern)

## Usage

### Command Line Interface

```bash
# Check all applications and instances
./check_versions.py --check-all

# Show summary with status icons
./check_versions.py --summary

# List all applications and instances
./check_versions.py --list

# Check specific application (checks all instances)
./check_versions.py --app "ApplicationName"  # Checks all instances

# Interactive mode (default)
./check_versions.py
```

### Interactive Mode

Run `./check_versions.py` without arguments for menu-driven interface:
- Check all applications
- Check single application
- Show summary
- Show all applications

## Excel Structure

The Excel file uses a single sheet with the following columns:

- **Name**: Application name (Home Assistant, Kopia, etc.)
- **Instance**: Specific instance (ssd, hdd, b2, prod, etc.)
- **Type**: Application type/category
- **Category**: Infrastructure category (set automatically for servers)
- **Target**: Connection endpoint (URLs, hostnames, etc.)
- **Repository**: Repository path for latest version checks (GitHub, Docker Hub, etc.)
- **Current_Version**: Currently running version
- **Latest_Version**: Latest available version
- **Status**: Up to Date, Update Available, etc.
- **Last_Checked**: Timestamp of last check
- **Check_Current**: How current versions are retrieved (api, ssh, kubectl, etc.)
- **Check_Latest**: How latest versions are retrieved (github_release, docker_hub, etc.)
- **Notes**: Additional information (auto-populated for some checks)

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
- Each instance gets its own row in the Excel file with individual version tracking
- Supports various instance types (production, staging, node-specific, environment-specific)
- Instance names are configurable and can represent servers, environments, or components

## Security Notes

- Uses existing config.py pattern for credentials
- Never commits actual credentials to git
- Follows your established authentication patterns (Bearer tokens, API keys, etc.)


## Files in Project:
- **`Goepp Homelab Master.xlsx`** - Excel database with Name/Instance structure for tracking
- **`version_manager.py`** - Core Python class handling all version checking logic
- **`check_versions.py`** - Command-line interface with multi-instance support
- **`update_excel.py`** - Script to update Excel structure while preserving data
- **`requirements.txt`** - Python dependencies
- **`config.py`** - Configuration and credentials (not committed to git)
- **`checkers/`** - Directory containing modular version checker modules
  - **`base.py`** - Base classes (KubernetesChecker, APIChecker) for modular version checking
  - **`github.py`** - GitHub release and tag API functions
  - **`kubectl.py`** - Kubernetes-based version checkers using modular base classes
  - **`utils.py`** - Shared utilities (HTTP requests, version parsing, error handling)
  - Additional specialized checkers for specific application types and platforms
- **`.venv/`** - Virtual environment (not committed to git)

## Quick Start Example:
```bash
# Activate virtual environment
source .venv/bin/activate

# Check all applications (including all Kopia instances)
./check_versions.py --check-all

# Show summary with visual status icons
./check_versions.py --summary
```

### Example Multi-Instance Output:
```
Starting version check for all applications...
==================================================
Checking Application-instance1...
  instance1: 1.2.3
  Status: ✅ Up to Date

Checking Application-instance2...
  instance2: 1.2.3  
  Status: ✅ Up to Date

Checking Application-instance3...
  instance3: 1.2.2
  Status: ⚠️ Update Available
```