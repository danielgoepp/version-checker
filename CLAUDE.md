# Version Check Module

## Overview
Excel-based software version monitoring system with multi-instance support for tracking various applications across the Goepp Lab infrastructure.

## Architecture
- **Language**: Python 3.13.7 with pandas, requests, paho-mqtt libraries
- **Excel Database**: "Goepp Homelab Master.xlsx" with Name/Instance structure and Repository field
- **Modular Design**: Individual checkers in `checkers/` directory with shared utilities
- **CLI Interface**: `check_versions.py` for command-line operations
- **Virtual Environment**: Always use `source venv/bin/activate`
- **Unified Kernel Checking**: Single linux_kernel.py handles all Linux distributions

## Key Patterns

### Multi-Instance Support
Applications can have multiple instances tracked separately:
- **Home Assistant**: prod, morgspi, mudderpi
- **Kopia**: ssd, hdd, b2 (backup nodes)
- **Zigbee2MQTT**: zigbee11, zigbee15
- **Telegraf**: vm, graylog
- **Konnected**: car, workshop
- **Traefik**: prod, mudderpi, morgspi
- **PostgreSQL**: grafana-prod, hertzbeat-prod, homeassistant-prod (CNPG clusters)

### Check Methods (Split Architecture)
The system uses two separate columns for version checking:

#### Current Version Methods (`Check_Current`)
| Method | Description | Example Applications |
|--------|-------------|---------------------|
| `api` | REST API calls for version info | Home Assistant, ESPHome, Traefik, OPNsense |
| `ssh` | SSH connections showing OS + kernel | Raspberry Pi, Ubuntu servers |
| `kubectl` | Kubernetes operations (pod queries, node info) | Telegraf, VictoriaMetrics, Mosquitto, K3s, Calico, MetalLB, Alertmanager, CloudNativePG, PostgreSQL, pgAdmin, Grafana |
| `command` | Shell commands | Kopia |
| `mqtt` | MQTT subscription | Zigbee2MQTT |

#### Latest Version Methods (`Check_Latest`)
| Method | Description | Example Applications |
|--------|-------------|---------------------|
| `github_release` | GitHub releases API | Home Assistant, ESPHome, Traefik, K3s, Calico, MetalLB, Alertmanager, Grafana |
| `github_tag` | GitHub tags API | Konnected project versions, Mosquitto, pgAdmin |
| `docker_hub` | Docker Hub/container tags | Graylog |
| `ssh_apt` | SSH apt update checking | Ubuntu servers, Raspberry Pi |
| `proxmox` | Proxmox-specific API | Proxmox VE |
| `opnsense` | OPNsense firmware update logic | OPNsense |
| `tailscale` | Tailscale device update tracking | Tailscale |
| `none` | No latest version checking | Legacy method |

### Status Icons & Meanings
- **✅ Up to Date**: Current matches latest
- **⚠️ Update Available**: Current behind latest
- **📋 Latest Available**: Only latest known (no current)
- **📌 Current Version**: Only current known (no comparison)
- **❓ Unknown**: Unable to determine

## Modular Architecture

### Checker Organization
- **Individual modules**: Each service type has its own file in `checkers/`
- **Shared utilities**: Common HTTP helper functions in `checkers/utils.py`
- **Clean imports**: Main manager imports from modular checkers
- **Examples**:
  - `checkers/github.py`: GitHub release API functions
  - `checkers/home_assistant.py`: Home Assistant API integration
  - `checkers/kubectl.py`: Kubernetes pod version extraction
  - `checkers/postgres.py`: CloudNativePG operator and PostgreSQL database versions
  - `checkers/grafana.py`: Grafana version via internal API using kubectl exec
  - `checkers/traefik.py`: Traefik API endpoint version checking
  - `checkers/utils.py`: Shared HTTP request helper

## Configuration Patterns

### Repository Field Management
- **Excel stores repository paths**: Repository paths for GitHub, Docker Hub, etc. in Repository column  
- **Direct usage**: No hardcoding in docker_hub method
- **Examples**:
  - Excel Repository: `Graylog2/graylog-docker` 
  - Code: Uses Repository field value directly

### URL Handling  
- **Excel stores complete URLs**: Full URLs with https:// protocols in Target column
- **Direct usage**: No protocol manipulation needed in code
- **Examples**:
  - Excel: `https://homeassistant-prod.goepp.net`
  - Code: Direct usage without modification

### Credentials Management
- **Config.py**: Centralized credential storage
- **MQTT**: `config.MQTT_BROKER`, `config.MQTT_USERNAME`, `config.MQTT_PASSWORD`
- **Home Assistant**: `config.HA_TOKENS` dictionary by instance
- **OPNsense**: `config.OPNSENSE_API_KEY`, `config.OPNSENSE_API_SECRET`

### Kubernetes Integration
- **Namespace-aware**: Telegraf pods in `telegraf` namespace
- **Pod discovery**: `kubectl get pods` with grep filtering
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

### MQTT Version Discovery
- **Topic pattern**: `{instance}/bridge/info`
- **JSON payload**: Extract `version` field
- **Timeout**: 2-second wait for message

### SSH-based Kernel Checking (ssh_apt method)
- **Current_Version**: Shows "OS Name - Kernel Version" (e.g. "Ubuntu 24.04.3 LTS - 6.8.0-79-generic")
- **Latest_Version**: Shows "No updates" or "Update available"  
- **Unified Logic**: Single linux_kernel.py handles Ubuntu and Raspberry Pi
- **Package Detection**: Checks `linux-image-generic` (Ubuntu) and `raspberrypi-kernel` (RPi)
- **No apt update**: Uses `apt list --upgradable` without refreshing package lists

## Command Interface
```bash
# Check all applications
./check_versions.py --check-all

# Show summary with status counts
./check_versions.py --summary

# List all applications in table format
./check_versions.py --list

# Check specific application (all instances)
./check_versions.py --app "home assistant"
./check_versions.py --app "kopia"
./check_versions.py --app "CloudNativePG"
./check_versions.py --app "PostgreSQL"
./check_versions.py --app "pgAdmin"
./check_versions.py --app "Grafana"
```

## Development Patterns

### Adding New Applications
1. Add entries to Excel with appropriate `Check_Current` and `Check_Latest` methods plus complete URL
2. Create or extend checker module in `checkers/` directory
3. Import and integrate checker function in `version_manager.py`
4. Test with `--app` flag

### Modular Development
- **New checker creation**: Add file to `checkers/` with focused functionality
- **Shared utilities**: Use `from .utils import http_get` for HTTP requests
- **Clean separation**: Keep service-specific logic in dedicated modules
- **Import pattern**: Import checker functions in `version_manager.py`
- **Unified approach**: linux_kernel.py handles all Linux distributions (57 lines vs 220 lines previously)

### Excel Structure Preservation
- **Column Structure**: Name, Instance, Type, Category, Target, Repository, Current_Version, Latest_Version, Status, Last_Checked, Check_Current, Check_Latest
- **Target Column**: Store complete URLs with protocols in Excel
- **Repository Column**: Store repository paths (GitHub org/repo, Docker Hub paths, etc.)
- **Name/Instance Pattern**: Maintain consistent naming structure
- **Check Methods**: Use `Check_Current` for version retrieval method, `Check_Latest` for latest version source

### Error Handling
- Print descriptive error messages with instance context
- Return None for failed version checks
- Use try/except with specific error types where possible
- Set reasonable timeouts (10-15 seconds)

## Security Considerations
- **No hardcoded credentials** in version checking logic
- **Config.py pattern** for credential centralization
- **Environment variables recommended** for production (.env.example provided)
- **Never commit actual credentials** to repository

## Testing Workflow
1. **Individual app testing**: `--app "name"`
2. **Full system test**: `--check-all`
3. **Status verification**: `--summary` and `--list`
4. **Excel data validation**: Check timestamps and version updates

## Technical Notes
- **Python Version**: Requires Python 3.13.7+ for clean operation (no urllib3 warnings)
- **Virtual Environment**: Recreate with new Python versions for optimal compatibility
- **SSL/TLS**: Uses system OpenSSL with urllib3 v2.5.0+ for secure HTTPS requests
- **Code Organization**: Modular architecture with optimized checker modules (unified linux_kernel.py reduced complexity)
- **Excel File Access**: NEVER try to read .xlsx files directly with Read tool - they are binary files. Always use pandas with virtual environment: `source venv/bin/activate && python3 -c "import pandas as pd; df = pd.read_excel('filename')"`

## Documentation
- **README.md**: Keep things general, do not include specific details about the local specific environment.
- always automatically update md files before git commit and push