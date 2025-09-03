# Version Check Module

## Overview
Excel-based software version monitoring system with multi-instance support for tracking various applications across the Goepp Lab infrastructure.

## Architecture
- **Language**: Python 3.13.7 with pandas, requests, paho-mqtt libraries
- **Excel Database**: "Goepp IT Master.xlsx" with Name/Instance structure
- **Modular Design**: Individual checkers in `checkers/` directory with shared utilities
- **CLI Interface**: `check_versions.py` for command-line operations
- **Virtual Environment**: Always use `source venv/bin/activate`

## Key Patterns

### Multi-Instance Support
Applications can have multiple instances tracked separately:
- **Home Assistant**: prod, morgspi, mudderpi
- **Kopia**: ssd, hdd, b2 (backup nodes)
- **Zigbee2MQTT**: zigbee11, zigbee15
- **Telegraf**: vm, graylog
- **Konnected**: car, workshop

### Check Methods
| Method | Description | Example Applications |
|--------|-------------|---------------------|
| `api_github` | API call + GitHub releases | Home Assistant, ESPHome |
| `kubectl_github` | Kubernetes exec + GitHub | Telegraf |
| `k8s_api_github` | Kubernetes API + GitHub | K3s |
| `mqtt_github` | MQTT subscription + GitHub | Zigbee2MQTT |
| `command_github` | Shell command + GitHub | Kopia |
| `api_custom` | Custom API logic | OPNsense |
| `project_version` | GitHub YAML project version | Konnected |

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
  - `checkers/utils.py`: Shared HTTP request helper

## Configuration Patterns

### URL Handling  
- **Excel stores complete URLs**: Full URLs with https:// protocols in URL column
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

### MQTT Version Discovery
- **Topic pattern**: `{instance}/bridge/info`
- **JSON payload**: Extract `version` field
- **Timeout**: 2-second wait for message

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
```

## Development Patterns

### Adding New Applications
1. Add entries to Excel with appropriate Check_Method and complete URL
2. Create or extend checker module in `checkers/` directory
3. Import and integrate checker function in `version_manager.py`
4. Test with `--app` flag

### Modular Development
- **New checker creation**: Add file to `checkers/` with focused functionality
- **Shared utilities**: Use `from .utils import http_get` for HTTP requests
- **Clean separation**: Keep service-specific logic in dedicated modules
- **Import pattern**: Import checker functions in `version_manager.py`

### Excel Structure Preservation
- Excel now uses "URL" column (renamed from "Endpoint") 
- Store complete URLs with protocols in Excel
- Always backup before structural changes
- Maintain Name/Instance column pattern

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
- **Code Organization**: Modular architecture with 451 total lines across all checker modules