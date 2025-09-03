from .utils import http_get, print_error, print_version

def get_konnected_version(instance, url=None, github_repo=None):
    if not github_repo:
        print_error(instance, "No GitHub repository configured")
        return None
    
    github_url = f"https://raw.githubusercontent.com/{github_repo}/master/garage-door-GDOv2-Q.yaml"
    yaml_content = http_get(github_url)
    if yaml_content and isinstance(yaml_content, str):
        for line in yaml_content.split('\n'):
            if line.strip().startswith('project_version:'):
                version = line.split(':', 1)[1].strip().strip('"\'')
                print_version(instance, version)
                return version
    
    print_error(instance, "Could not get project version")
    return None