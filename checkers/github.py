from .utils import http_get

def get_github_latest_version(repo):
    data = http_get(f"https://api.github.com/repos/{repo}/releases/latest")
    if data and 'tag_name' in data:
        tag_name = data["tag_name"]
        return tag_name[1:] if tag_name.startswith("v") else tag_name
    return None

def get_github_latest_tag(repo):
    data = http_get(f"https://api.github.com/repos/{repo}/tags")
    if data and isinstance(data, list) and data:
        latest_tag = data[0]["name"]
        return latest_tag[1:] if latest_tag.startswith("v") else latest_tag
    return None