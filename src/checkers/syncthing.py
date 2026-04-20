import config
from .base import APIChecker
from .utils import print_error, http_get


def check_syncthing_current_version(instance, target_url):
    api_key = config.SYNCTHING_API_KEYS.get(instance)
    if not api_key:
        print_error(instance, f"No API key configured for Syncthing instance '{instance}'")
        return None

    headers = {'X-API-Key': api_key}
    url = f"{target_url.rstrip('/')}/rest/system/version"

    try:
        data = http_get(url, headers=headers, timeout=15)

        if data and isinstance(data, dict) and 'version' in data:
            version = data['version']
            if version.startswith('v'):
                version = version[1:]
            return version
        else:
            print_error(instance, "Could not get version from API response")
            return None

    except Exception as e:
        print_error(instance, f"Error calling Syncthing API: {e}")
        return None
