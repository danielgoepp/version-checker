import requests
import re
import json
import subprocess


def http_get(url, auth=None, headers=None, timeout=10):
    try:
        response = requests.get(url, auth=auth, headers=headers, timeout=timeout, verify=True)
        response.raise_for_status()
        return response.json() if 'json' in response.headers.get('content-type', '') else response.text
    except requests.RequestException:
        return None


def print_error(instance, message):
    print(f"  {instance}: {message}")


def print_version(instance, version):
    pass


def handle_timeout_error(instance, operation="operation"):
    print_error(instance, f"Timeout during {operation}")
    return None


def handle_generic_error(instance, error, operation="version check"):
    print_error(instance, f"Error during {operation}: {error}")
    return None


def clean_version(version_string):
    if not version_string:
        return None
    if version_string.startswith('v'):
        version_string = version_string[1:]
    if "build:" in version_string:
        version_string = version_string.split("build:")[0].strip()
    return version_string


def extract_semantic_version(text, pattern=r'v?(\d+\.\d+\.\d+)'):
    if not text:
        return None
    match = re.search(pattern, text)
    return match.group(1) if match else None


def parse_json_version(json_text, version_field='version'):
    try:
        data = json.loads(json_text) if isinstance(json_text, str) else json_text
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
            return data.get(version_field)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_image_version(image_string, image_pattern, version_pattern=r"v?(\d+\.\d+(?:\.\d+)?)"):
    if not image_string:
        return None
    full_pattern = rf"{image_pattern}:{version_pattern}"
    version_match = re.search(full_pattern, image_string)
    return version_match.group(1) if version_match else None


def ssh_get_version(instance, hostname, command):
    try:
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            hostname, command
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            if result.stderr.strip():
                print(f"  {instance}: SSH command '{command}' stderr: {result.stderr.strip()}")
            return None
    except subprocess.TimeoutExpired:
        print_error(instance, f"SSH command timed out: {command}")
        return None


def ssh_get_login_message(instance, hostname):
    try:
        # 'true' triggers MOTD without running anything
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            hostname, 'true'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        # MOTD can appear in either stdout or stderr depending on the system
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


def get_helm_chart_version(chart_repo, chart_name, value_path):
    import yaml
    url = f"https://raw.githubusercontent.com/{chart_repo}/main/charts/{chart_name}/values.yaml"
    response = http_get(url, timeout=10)
    if not response:
        return None
    yaml_data = yaml.safe_load(response)
    keys = value_path.split('.')
    current = yaml_data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return str(current) if current is not None else None


def get_helm_chart_app_version(chart_repo, chart_name):
    import yaml
    url = f"https://raw.githubusercontent.com/{chart_repo}/main/charts/{chart_name}/Chart.yaml"
    response = http_get(url, timeout=10)
    if not response:
        return None
    yaml_data = yaml.safe_load(response)
    app_version = yaml_data.get('appVersion')
    return str(app_version) if app_version is not None else None


def get_helm_search_app_version(chart_name, instance=""):
    try:
        result = subprocess.run(
            ["helm", "search", "repo", chart_name, "--output", "json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            print_error(instance, f"helm search repo failed: {result.stderr.strip()}")
            return None

        data = json.loads(result.stdout)
        if not data:
            print_error(instance, f"No results from helm search repo {chart_name}")
            return None

        app_version = data[0].get("app_version", "")
        return app_version if app_version else None

    except subprocess.TimeoutExpired:
        print_error(instance, "helm search repo timed out")
        return None
    except Exception as e:
        print_error(instance, f"helm search repo error: {e}")
        return None
