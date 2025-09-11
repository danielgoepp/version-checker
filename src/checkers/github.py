from .utils import http_get
import config

def _get_github_headers():
    """Get GitHub API headers with authentication if token is available"""
    headers = {}
    if config.GITHUB_API_TOKEN:
        headers['Authorization'] = f'token {config.GITHUB_API_TOKEN}'
    return headers

def get_github_latest_version(repo):
    headers = _get_github_headers()
    data = http_get(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers)
    if data and 'tag_name' in data:
        tag_name = data["tag_name"]
        return tag_name[1:] if tag_name.startswith("v") else tag_name
    return None

def get_github_latest_tag(repo):
    headers = _get_github_headers()
    data = http_get(f"https://api.github.com/repos/{repo}/tags", headers=headers)
    if data and isinstance(data, list) and data:
        latest_tag = data[0]["name"]
        return latest_tag[1:] if latest_tag.startswith("v") else latest_tag
    return None