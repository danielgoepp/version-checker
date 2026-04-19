import requests
from .utils import print_error


def get_vault_version(instance, url):
    """Get HashiCorp Vault version from sys/health API endpoint.
    Vault returns non-2xx codes when sealed/standby but still includes version in the JSON body.
    """
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
