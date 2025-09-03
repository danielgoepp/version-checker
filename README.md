# Goepp Homelab Version Manager

A comprehensive Python-based system for tracking software versions across your infrastructure using Excel for data management.

## Features

- **Excel Integration**: Uses "Goepp Homelab Master.xlsx" with Name/Instance structure
- **Multi-Instance Support**: Track multiple instances of the same application (e.g., Kopia nodes)
- **Multiple Check Methods**: 
  - GitHub API for latest releases
  - Local API calls (Home Assistant, Kubernetes)
  - MQTT messaging (Zigbee2MQTT)
  - Command execution (Kopia backup servers)
- **Visual Status Indicators**: Emoji icons for quick status recognition (✅⚠️📋❓)
- **Automated Tracking**: Tracks current vs latest versions with timestamps
- **Flexible Interface**: Command-line and interactive modes

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
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
./check_versions.py --app "Kopia"  # Checks ssd, hdd, b2
./check_versions.py --app "Home Assistant"  # Single instance

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

The Excel file contains three sheets:

### Version_Tracking
- **Name**: Application name (Home Assistant, Kopia, etc.)
- **Instance**: Specific instance (ssd, hdd, b2, or "default" for single instances)
- **Category**: Type (Home Automation, Monitoring, etc.)
- **Type**: Check method (API, GitHub, MQTT, etc.)  
- **URL/Endpoint**: Connection details
- **GitHub_Repo**: Repository for latest version checks
- **Current_Version**: Currently running version
- **Latest_Version**: Latest available version
- **Status**: Up to Date, Update Available, etc.
- **Last_Checked**: Timestamp of last check
- **Check_Method**: How versions are retrieved
- **Notes**: Additional information

### Summary
- Category-based counting and status

### Config
- Settings like API tokens, check intervals, notifications

## Supported Applications

Based on your existing scripts:
- **Home Assistant** (API + GitHub) - Single instance
- **K3s** (Kubernetes API + GitHub) - Single cluster
- **Zigbee2MQTT** (MQTT + GitHub) - Single instance  
- **Kopia** (Command + GitHub) - **Multi-instance: ssd, hdd, b2 nodes**
- **ESPHome** (GitHub only) - Single instance
- **Konnected** (GitHub only) - Single instance
- **OPNsense** (Web scraping) - Single instance
- **Telegraf** (GitHub only) - Single instance
- **VictoriaMetrics** (GitHub only) - Single instance
- **Traefik** (API + GitHub) - **Multi-instance: prod, mudderpi, morgspi**

### Multi-Instance Applications
Applications like Kopia and Traefik that run on multiple servers are tracked separately:
- **Kopia-ssd**: kopia-ssd.goepp.net:51515
- **Kopia-hdd**: kopia-hdd.goepp.net:51515  
- **Kopia-b2**: kopia-b2.goepp.net:51515
- **Traefik-prod**: traefik-prod.goepp.net
- **Traefik-mudderpi**: traefik-mudderpi.goepp.net
- **Traefik-morgspi**: traefik-morgspi.goepp.net

Each instance gets its own row in the Excel file with individual version tracking.

## Security Notes

- Uses existing config.py pattern for credentials
- Never commits actual credentials to git
- Follows your established authentication patterns (Bearer tokens, API keys, etc.)


## Files in Project:
- **`Goepp Homelab Master.xlsx`** - Excel file with Name/Instance structure for tracking
- **`version_manager.py`** - Core Python class handling all version checking logic
- **`check_versions.py`** - Command-line interface with multi-instance support
- **`update_excel.py`** - Script to update Excel structure while preserving data
- **`requirements.txt`** - Python dependencies  
- **`activate.sh`** - Helper script for virtual environment activation
- **`venv/`** - Virtual environment (not committed to git)

## Quick Start Example:
```bash
# Activate virtual environment
source venv/bin/activate

# Check all applications (including all Kopia instances)
./check_versions.py --check-all

# Show summary with visual status icons
./check_versions.py --summary
```

### Example Multi-Instance Output:
```
Starting version check for all applications...
==================================================
Checking Kopia-ssd...
  ssd: 0.21.1
  Status: ✅ Up to Date

Checking Kopia-hdd...
  hdd: 0.21.1  
  Status: ✅ Up to Date

Checking Kopia-b2...
  b2: 0.21.1
  Status: ✅ Up to Date
```