import requests

import config
from .utils import print_error


def check_awx_current_version(instance, target_url):
    """Check current AWX version via REST API"""
    
    # Get API token for this instance
    instance_key = instance.lower()
    api_token = config.AWX_API_TOKENS.get(instance) or config.AWX_API_TOKENS.get(instance_key)
    if not api_token:
        configured = ", ".join(sorted(config.AWX_API_TOKENS.keys())) or "none"
        print_error(
            instance,
            f"No API token configured for AWX instance '{instance}' (configured: {configured})",
        )
        return None
    
    # Create headers with Bearer token
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Accept': 'application/json',
    }
    
    # Build the full URL
    url = f"{target_url.rstrip('/')}/api/v2/config/"
    
    verify_ssl = getattr(config, 'AWX_VERIFY_SSL', True)

    try:
        # Make the API call
        response = requests.get(url, headers=headers, timeout=15, verify=verify_ssl)
        if response.status_code == 401:
            print_error(instance, "Unauthorized (check AWX API token)")
            return None
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and 'version' in data:
            return data['version']

        print_error(instance, "Could not get version from API response")
        return None

    except requests.exceptions.SSLError as e:
        print_error(instance, f"SSL verification failed for AWX API: {e}")
        return None
    except requests.RequestException as e:
        print_error(instance, f"Error calling AWX API: {e}")
        return None
