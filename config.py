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