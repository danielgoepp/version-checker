import requests
import json
from .utils import http_get, print_error, handle_generic_error
from .github import get_github_latest_version

def get_tailscale_api_devices(api_key, tailnet):
    try:
        url = f"https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        response = http_get(url, headers=headers, timeout=15)
        if response and isinstance(response, dict):
            return response.get('devices', [])
        return []
    except Exception as e:
        print_error("tailscale-api", f"Failed to get devices from API: {e}")
        return []

def check_tailscale_versions(api_key=None, tailnet=None):
    results = {
        'devices_needing_updates': 0,
        'devices_up_to_date': 0,
        'total_devices': 0,
        'device_details': []
    }

    if not api_key or not tailnet:
        print_error("tailscale", "API key and tailnet required for Tailscale checking")
        return results

    print("  Using Tailscale API to get device update status...")
    devices = get_tailscale_api_devices(api_key, tailnet)

    if not devices:
        print_error("tailscale", "No devices found")
        return results

    print(f"  Found {len(devices)} Tailscale devices")
    results['total_devices'] = len(devices)

    for device in devices:
        hostname = device.get('name', 'unknown')
        os_type = device.get('os', 'unknown')
        current_version = device.get('clientVersion', '')
        update_available = device.get('updateAvailable', False)

        if current_version:
            if '-' in current_version:
                current_version = current_version.split('-')[0]
            current_version = current_version.strip()

        if update_available:
            results['devices_needing_updates'] += 1
            status = "⚠️ Update available"
        else:
            results['devices_up_to_date'] += 1
            status = "✅ Up to date"

        results['device_details'].append({
            'name': hostname,
            'os': os_type,
            'version': current_version,
            'update_available': update_available
        })

        print(f"    {hostname} ({os_type}): {current_version} - {status}")

    print(f"  Summary: {results['devices_up_to_date']} up-to-date, {results['devices_needing_updates']} need updates")

    return results
