from .esphome_device import get_esphome_device_info
from .utils import http_get, print_error


def get_konnected_current_version(instance, url=None, encryption_key=None):
    return get_esphome_device_info(instance, url, encryption_key)


def get_konnected_version(instance, url=None, github_repo=None):
    if not github_repo:
        print_error(instance, "No GitHub repository configured")
        return None

    github_url = f"https://raw.githubusercontent.com/{github_repo}/master/garage-door-GDOv2-Q.yaml"
    yaml_content = http_get(github_url)
    if yaml_content and isinstance(yaml_content, str):
        for line in yaml_content.split('\n'):
            if line.strip().startswith('project_version:'):
                return line.split(':', 1)[1].strip().strip('"\'')

    print_error(instance, "Could not get project version")
    return None
