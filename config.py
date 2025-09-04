import os
import sys
from pathlib import Path

# Try to load .env file if it exists
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

def get_required_env(key, description):
    """Get required environment variable or exit with error"""
    value = os.getenv(key)
    if not value:
        print(f"ERROR: Required environment variable '{key}' not set")
        print(f"This should contain: {description}")
        print("Please check your .env file or set the environment variable")
        sys.exit(1)
    return value

def get_optional_env(key, default, description):
    """Get optional environment variable with default"""
    return os.getenv(key, default)

# Home Assistant tokens - REQUIRED
HA_TOKENS = {
    "prod": get_required_env('HA_TOKEN_PROD', 'Home Assistant production API token'),
    "morgspi": get_required_env('HA_TOKEN_MORGSPI', 'Home Assistant morgspi API token'), 
    "mudderpi": get_required_env('HA_TOKEN_MUDDERPI', 'Home Assistant mudderpi API token'),
}

# OPNsense API credentials - REQUIRED
OPNSENSE_API_KEY = get_required_env('OPNSENSE_API_KEY', 'OPNsense API key')
OPNSENSE_API_SECRET = get_required_env('OPNSENSE_API_SECRET', 'OPNsense API secret')

# MQTT credentials - with sensible defaults
MQTT_BROKER = get_optional_env('MQTT_BROKER', 'mosquitto-prod.goepp.net', 'MQTT broker hostname')
MQTT_USERNAME = get_required_env('MQTT_USERNAME', 'MQTT username')
MQTT_PASSWORD = get_required_env('MQTT_PASSWORD', 'MQTT password')

# Proxmox API credentials - REQUIRED
PROXMOX_API_TOKEN = get_required_env('PROXMOX_API_TOKEN', 'Proxmox API token (format: user@realm!tokenid=uuid)')

# Tailscale API credentials - REQUIRED for Tailscale checking
TAILSCALE_API_KEY = get_optional_env('TAILSCALE_API_KEY', None, 'Tailscale API key for device management')
TAILSCALE_TAILNET = get_optional_env('TAILSCALE_TAILNET', None, 'Tailscale tailnet name (e.g., example.com)')

# Graylog API credentials - OPTIONAL (fallback to basic auth if not provided)
GRAYLOG_TOKENS = {}
# Individual instance tokens can be set in environment variables
graylog_prod_token = get_optional_env('GRAYLOG_TOKEN_PROD', None, 'Graylog production API token')
if graylog_prod_token:
    GRAYLOG_TOKENS['graylog-prod'] = graylog_prod_token

# Fallback basic auth credentials for Graylog
GRAYLOG_USERNAME = get_optional_env('GRAYLOG_USERNAME', None, 'Graylog username for basic auth')
GRAYLOG_PASSWORD = get_optional_env('GRAYLOG_PASSWORD', None, 'Graylog password for basic auth')