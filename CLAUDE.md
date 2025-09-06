# Version Check Module

## Overview
Excel-based software version monitoring system with multi-instance support for tracking various applications across the Goepp Lab infrastructure.


Note: This is for my specific infrastructure only, not a general purpose app. The only reason I make this a public repository is for reference only. If one were to take this code an try to make it work for them, significant changes would be needed to customize it. Unless of course you run the exact tech stack in the extact same way I do. If you are interested and want a copy of the Excel doc that goes with this, let me know and I would be happy to provide it.

## Architecture
- **Language**: Python 3.13.7 with pandas, requests, paho-mqtt libraries
- **Excel Database**: "Goepp Homelab Master.xlsx" with Name/Instance structure and GitHub/DockerHub repository fields
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
| `api` | REST API calls for version info | Web-based applications with API endpoints |
| `ssh` | SSH connections showing OS + kernel | Remote servers and systems |
| `kubectl` | Kubernetes operations (pod queries, node info) | Containerized applications in Kubernetes |
| `command` | Shell commands | Applications with command-line version output |
| `mqtt` | MQTT subscription | Applications publishing version via MQTT |

#### Latest Version Methods (`Check_Latest`)
| Method | Description | Example Applications |
|--------|-------------|---------------------|
| `github_release` | GitHub releases API | Open source projects with GitHub releases |
| `github_tag` | GitHub tags API | Projects using Git tags for versioning |
| `docker_hub` | Docker Hub/container tags | Containerized applications on Docker Hub |
| `ssh_apt` | SSH apt update checking | Linux systems with APT package manager |
| `proxmox` | Proxmox-specific API | Proxmox virtualization platforms |
| `opnsense` | OPNsense firmware update logic | OPNsense firewall systems |
| `tailscale` | Tailscale device update tracking | Tailscale VPN networks |
| `none` | No latest version checking | Applications without available update sources |

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
  - `checkers/base.py`: Base classes (KubernetesChecker, APIChecker) for modular version checking
  - `checkers/github.py`: GitHub release and tag API functions
  - `checkers/kubectl.py`: Kubernetes-based version checkers using modular base classes
  - `checkers/utils.py`: Shared utilities (HTTP requests, version parsing, error handling)

## Configuration Patterns

### Repository Field Management
- **Separate fields**: GitHub and DockerHub repository paths in dedicated columns
- **GitHub field**: GitHub repository paths in `owner/repository-name` format  
- **DockerHub field**: Docker Hub repository paths in `organization/image-name` format
- **Direct usage**: Field values used by checkers based on Check_Latest method without hardcoding

### URL Handling  
- **Excel stores complete URLs**: Full URLs with https:// protocols in Target column
- **Direct usage**: URLs used directly by API checkers without modification
- **Examples**:
  - Format: `https://hostname.domain.com` or `https://ip-address:port`
  - Usage: Passed directly to HTTP request functions

### Configuration Management
- **Config.py**: Centralized configuration and credential storage
- **Excel File Path**: `config.EXCEL_FILE_PATH` (configurable via EXCEL_FILE_PATH env var, defaults to 'Goepp Homelab Master.xlsx')
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
2. Populate GitHub or DockerHub field based on the Check_Latest method used
3. Create or extend checker module in `checkers/` directory
4. Import and integrate checker function in `version_manager.py`
5. Test with `--app` flag

### Modular Development
- **New checker creation**: Add file to `checkers/` with focused functionality
- **Shared utilities**: Use `from .utils import http_get` for HTTP requests
- **Clean separation**: Keep service-specific logic in dedicated modules
- **Import pattern**: Import checker functions in `version_manager.py`
- **Unified approach**: linux_kernel.py handles all Linux distributions (57 lines vs 220 lines previously)

### Excel Structure Preservation
- **Column Structure**: Name, Instance, Type, Category, Target, GitHub, DockerHub, Current_Version, Latest_Version, Status, Last_Checked, Check_Current, Check_Latest
- **Target Column**: Store complete URLs with protocols in Excel
- **GitHub Column**: Store GitHub repository paths (owner/repo format)
- **DockerHub Column**: Store Docker Hub repository paths (org/image format)
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
- **Excel File Location**: Use EXCEL_FILE_PATH from config.py (set in .env file) to know where the Excel file is located, don't assume it's in current directory

## Documentation
- **README.md**: Keep things general, do not include specific details about the local specific environment.
- **Auto-update requirement**: ALWAYS update README.md and other documentation files to reflect code changes before any git commit and push operation