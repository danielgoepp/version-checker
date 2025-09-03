from .utils import http_get, print_version, print_error


def get_traefik_version(instance, url):
    """Get Traefik version from API endpoint"""
    try:
        # Append /api/version to the base URL
        api_url = f"{url.rstrip('/')}/api/version"
        
        # Make API request
        response = http_get(api_url, timeout=15)
        if response is None:
            print_error(instance, "Could not connect to Traefik API")
            return None
        
        # Parse version from JSON response
        version = response.get("Version")
        if version:
            print_version(instance, version)
            return version
        else:
            print_error(instance, "Version field not found in API response")
            return None
            
    except Exception as e:
        print_error(instance, f"Error getting version - {e}")
        return None