import requests
from .utils import print_error


def get_vault_version(instance, url):
    try:
        endpoint = f"{url.rstrip('/')}/v1/sys/health"
        response = requests.get(endpoint, timeout=15, verify=True)
        data = response.json()
        version = data.get("version")
        if version:
            return version
        print_error(instance, "No version field in sys/health response")
        return None
    except Exception as e:
        print_error(instance, f"Error getting Vault version: {e}")
        return None
