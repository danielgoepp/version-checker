from .utils import http_get
import re
import config

def get_mongodb_latest_version():
    headers = {}
    if config.GITHUB_API_TOKEN:
        headers['Authorization'] = f'token {config.GITHUB_API_TOKEN}'

    data = http_get("https://api.github.com/repos/mongodb/mongo/tags?per_page=100", headers=headers)
    if data and isinstance(data, list):
        series_versions = {}

        for tag in data:
            tag_name = tag["name"]
            if re.match(r'^r\d+\.\d+\.\d+$', tag_name):
                version = tag_name[1:]
                version_parts = version.split('.')

                if len(version_parts) == 3:
                    series_key = f"{version_parts[0]}.{version_parts[1]}"

                    if series_key not in series_versions:
                        series_versions[series_key] = []
                    series_versions[series_key].append(version)

        if not series_versions:
            return None

        stable_series = max(series_versions.keys(), key=lambda k: len(series_versions[k]))

        def version_key(v):
            return tuple(map(int, v.split('.')))

        stable_versions = series_versions[stable_series]
        stable_versions.sort(key=version_key, reverse=True)

        print(f"  MongoDB: Found {len(stable_versions)} releases in {stable_series} series (stable)")
        return stable_versions[0]

    return None
