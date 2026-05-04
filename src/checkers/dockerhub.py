from functools import lru_cache
from .utils import http_get
from datetime import datetime
import re


@lru_cache(maxsize=128)
def _get_dockerhub_latest_version_cached(repository, version_pattern_str, exclude_tags_tuple):
    version_pattern = re.compile(version_pattern_str) if version_pattern_str else None
    exclude_tags = list(exclude_tags_tuple) if exclude_tags_tuple else None
    return _get_dockerhub_latest_version_impl(repository, version_pattern, exclude_tags)


def _get_dockerhub_latest_version_impl(repository, version_pattern=None, exclude_tags=None):
    try:
        url = f"https://registry.hub.docker.com/v2/repositories/{repository}/tags/?page_size=100"
        data = http_get(url, timeout=15)

        if not (data and isinstance(data, dict) and 'results' in data):
            return None

        if version_pattern is None:
            version_pattern = re.compile(r'^v?(\d+\.\d+(?:\.\d+)?)(?:-[a-z][a-z0-9]*)?$')

        if exclude_tags is None:
            exclude_tags = [
                'latest', 'edge', 'dev', 'devel', 'develop', 'main', 'master',
                'edge-ubuntu', 'edge-alpine', 'edge-debian',
                'nightly', 'unstable', 'beta', 'alpha', 'rc'
            ]

        versions = []

        for tag in data['results']:
            tag_name = tag.get('name', '')

            if tag_name in exclude_tags or any(excluded in tag_name.lower() for excluded in ['rc', 'beta', 'alpha', 'dev', 'nightly', 'unstable']):
                continue

            if isinstance(version_pattern, str):
                version_pattern = re.compile(version_pattern)

            match = version_pattern.match(tag_name)
            if match:
                version = match.group(1) if match.groups() else match.group(0)
                versions.append(version)

        if versions:
            def version_key(v):
                # MinIO uses date-based tags (YYYY-MM-DDTHH-MM-SSZ) instead of semver
                if 'T' in v and 'Z' in v:
                    try:
                        date_part = v.replace('-', ':', 2).replace('-', ':', 1)
                        date_part = date_part.replace(':', '-', 2)
                        return datetime.strptime(date_part, "%Y-%m-%dT%H:%M:%SZ")
                    except (ValueError, AttributeError):
                        return v
                else:
                    try:
                        parts = v.split('.')
                        return tuple(int(part) for part in parts)
                    except (ValueError, AttributeError):
                        return v

            versions.sort(key=version_key, reverse=True)
            return versions[0]

        return None

    except Exception as e:
        print(f"  Error getting latest version from Docker Hub ({repository}): {e}")
        return None


def get_dockerhub_latest_version(repository, version_pattern=None, exclude_tags=None):
    version_pattern_str = version_pattern.pattern if hasattr(version_pattern, 'pattern') else (version_pattern if isinstance(version_pattern, str) else None)
    exclude_tags_tuple = tuple(exclude_tags) if exclude_tags else None
    return _get_dockerhub_latest_version_cached(repository, version_pattern_str, exclude_tags_tuple)


@lru_cache(maxsize=128)
def get_dockerhub_latest_tag(repository, include_prereleases=False):
    try:
        url = f"https://registry.hub.docker.com/v2/repositories/{repository}/tags/?page_size=10"
        data = http_get(url, timeout=15)

        if not (data and isinstance(data, dict) and 'results' in data):
            return None

        for tag in data['results']:
            tag_name = tag.get('name', '')

            if tag_name == 'latest':
                continue

            if not include_prereleases:
                if any(prerelease in tag_name.lower() for prerelease in ['rc', 'beta', 'alpha', 'edge', 'nightly']):
                    continue

            return tag_name

        return None

    except Exception as e:
        print(f"  Error getting latest tag from Docker Hub ({repository}): {e}")
        return None


def get_dockerhub_latest_beta(repository):
    try:
        url = f"https://registry.hub.docker.com/v2/repositories/{repository}/tags/?page_size=100"
        data = http_get(url, timeout=15)

        if not (data and isinstance(data, dict) and 'results' in data):
            return None

        pattern = re.compile(r'^(\d+\.\d+\.\d+)-beta\.(\d+)$')
        versions = []

        for tag in data['results']:
            tag_name = tag.get('name', '')
            match = pattern.match(tag_name)
            if match:
                base = tuple(int(p) for p in match.group(1).split('.'))
                beta_num = int(match.group(2))
                versions.append((base, beta_num, tag_name))

        if versions:
            versions.sort(reverse=True)
            return versions[0][2]

        return None

    except Exception as e:
        print(f"  Error getting latest beta from Docker Hub ({repository}): {e}")
        return None
