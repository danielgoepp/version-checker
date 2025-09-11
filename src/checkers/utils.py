import requests
import re
import json
import subprocess


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


def ssh_get_version(instance, hostname, command):
    """Execute SSH command and return the output"""
    try:
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            hostname, command
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            # Log stderr for debugging but don't treat as fatal error
            if result.stderr.strip():
                print(f"  {instance}: SSH command '{command}' stderr: {result.stderr.strip()}")
            return None
            
    except subprocess.TimeoutExpired:
        print_error(instance, f"SSH command timed out: {command}")
        return None
    except Exception as e:
        print_error(instance, f"SSH command failed: {e}")
        return None


def ssh_get_login_message(instance, hostname):
    """Connect via SSH and capture login message (MOTD) without running commands"""
    try:
        # Use 'true' command which does nothing but will trigger MOTD display
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            hostname, 'true'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        # For login messages, we want to capture both stdout and stderr
        # as MOTD can appear in either stream depending on the system
        full_output = ""
        if result.stdout.strip():
            full_output += result.stdout.strip()
        if result.stderr.strip():
            if full_output:
                full_output += "\n"
            full_output += result.stderr.strip()
        
        return full_output if full_output else None
            
    except subprocess.TimeoutExpired:
        print_error(instance, "SSH connection timed out")
        return None
    except Exception as e:
        print_error(instance, f"SSH connection failed: {e}")
        return None


def get_helm_chart_version(chart_repo, chart_name, value_path):
    """Get version from Helm chart values.yaml file on GitHub
    
    Args:
        chart_repo: GitHub repository (e.g., 'mongodb/helm-charts')
        chart_name: Name of the chart (e.g., 'community-operator')
        value_path: YAML path to the version (e.g., 'operator.version')
    """
    try:
        # Construct URL to the values.yaml file
        url = f"https://raw.githubusercontent.com/{chart_repo}/main/charts/{chart_name}/values.yaml"
        
        import yaml
        
        # Fetch the YAML content
        response = http_get(url, timeout=10)
        if not response:
            return None
        
        # Parse YAML
        try:
            yaml_data = yaml.safe_load(response)
        except yaml.YAMLError:
            return None
        
        # Navigate to the version using dot notation
        keys = value_path.split('.')
        current = yaml_data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return str(current) if current is not None else None
        
    except Exception:
        return None


def get_helm_chart_app_version(chart_repo, chart_name):
    """Get appVersion from Helm chart Chart.yaml file on GitHub
    
    Args:
        chart_repo: GitHub repository (e.g., 'fluent/helm-charts')
        chart_name: Name of the chart (e.g., 'fluent-bit')
    """
    try:
        # Construct URL to the Chart.yaml file
        url = f"https://raw.githubusercontent.com/{chart_repo}/main/charts/{chart_name}/Chart.yaml"
        
        import yaml
        
        # Fetch the YAML content
        response = http_get(url, timeout=10)
        if not response:
            return None
        
        # Parse YAML
        try:
            yaml_data = yaml.safe_load(response)
        except yaml.YAMLError:
            return None
        
        # Get appVersion from Chart.yaml
        app_version = yaml_data.get('appVersion')
        return str(app_version) if app_version is not None else None
        
    except Exception:
        return None