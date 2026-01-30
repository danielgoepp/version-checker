from functools import lru_cache
from .utils import http_get, extract_semantic_version
import config

def _get_github_headers():
    """Get GitHub API headers with authentication if token is available"""
    headers = {}
    if config.GITHUB_API_TOKEN:
        headers['Authorization'] = f'token {config.GITHUB_API_TOKEN}'
    return headers

@lru_cache(maxsize=128)
def get_github_latest_version(repo):
    """Get latest GitHub release version (cached to avoid redundant API calls)"""
    headers = _get_github_headers()
    data = http_get(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers)
    if data and 'tag_name' in data:
        tag_name = data["tag_name"]
        if tag_name.startswith("v"):
            return tag_name[1:]
        return extract_semantic_version(tag_name) or tag_name
    return None

@lru_cache(maxsize=128)
def get_github_latest_tag(repo):
    """Get latest GitHub tag (cached to avoid redundant API calls)"""
    headers = _get_github_headers()
    data = http_get(f"https://api.github.com/repos/{repo}/tags", headers=headers)
    if data and isinstance(data, list) and data:
        latest_tag = data[0]["name"]
        if latest_tag.startswith("v"):
            return latest_tag[1:]
        return extract_semantic_version(latest_tag) or latest_tag
    return None