import requests
import re
import json


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


# Version parsing utilities
def clean_version(version_string):
    """Remove common prefixes and suffixes from version strings"""
    if not version_string:
        return None
        
    # Remove 'v' prefix
    if version_string.startswith('v'):
        version_string = version_string[1:]
    
    # Handle build suffixes (like Kopia's "build:" suffix)
    if "build:" in version_string:
        version_string = version_string.split("build:")[0].strip()
        
    return version_string


def extract_semantic_version(text, pattern=r'v?(\d+\.\d+\.\d+)'):
    """Extract semantic version from text using regex"""
    if not text:
        return None
        
    match = re.search(pattern, text)
    return match.group(1) if match else None


def parse_json_version(json_text, version_field='version'):
    """Parse version from JSON text with support for nested field paths"""
    try:
        data = json.loads(json_text) if isinstance(json_text, str) else json_text
        
        # Handle nested field paths like "version.number"
        if '.' in version_field:
            field_parts = version_field.split('.')
            current_data = data
            for part in field_parts:
                if isinstance(current_data, dict) and part in current_data:
                    current_data = current_data[part]
                else:
                    return None
            return current_data
        else:
            # Simple field access
            return data.get(version_field)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_image_version(image_string, image_pattern, version_pattern=r"v?(\d+\.\d+(?:\.\d+)?)"):
    """Extract version from container image string with flexible version pattern"""
    if not image_string:
        return None
        
    # Create full pattern: image_pattern followed by colon and version
    full_pattern = rf"{image_pattern}:{version_pattern}"
    version_match = re.search(full_pattern, image_string)
    return version_match.group(1) if version_match else None