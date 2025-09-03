import requests

def http_get(url, auth=None, headers=None, timeout=10):
    """Helper method for HTTP GET requests"""
    try:
        response = requests.get(url, auth=auth, headers=headers, timeout=timeout, verify=True)
        response.raise_for_status()
        return response.json() if 'json' in response.headers.get('content-type', '') else response.text
    except requests.RequestException:
        return None

def print_error(instance, message):
    """Standardized error message printing"""
    print(f"  {instance}: {message}")

def print_version(instance, version):
    """Standardized version printing"""
    print(f"  {instance}: {version}")

def handle_timeout_error(instance, operation="operation"):
    """Standard timeout error handling"""
    print_error(instance, f"Timeout during {operation}")
    return None

def handle_generic_error(instance, error, operation="version check"):
    """Standard generic error handling"""
    print_error(instance, f"Error during {operation}: {error}")
    return None