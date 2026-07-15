from functools import lru_cache
from .utils import http_get
import re

_PRERELEASE_MARKERS = ('rc', 'beta', 'alpha', 'dev', 'nightly', 'unstable', 'edge')


def _is_prerelease(tag_name):
    # Component-based so e.g. "1.2.3-arch" isn't excluded by the 'rc' substring
    return any(
        part.startswith(marker)
        for part in re.split(r'[-._]', tag_name.lower())
        for marker in _PRERELEASE_MARKERS
    )


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
            exclude_tags = ['latest', 'main', 'master']

        versions = []

        for tag in data['results']:
            tag_name = tag.get('name', '')

            if tag_name in exclude_tags or _is_prerelease(tag_name):
                continue

            match = version_pattern.match(tag_name)
            if match:
                version = match.group(1) if match.groups() else match.group(0)
                versions.append(version)

        if versions:
            def version_key(v):
                try:
                    return tuple(int(part) for part in v.split('.'))
                except (ValueError, AttributeError):
                    # Unparseable versions sort last instead of crashing the
                    # mixed tuple/str comparison
                    return (-1,)

            versions.sort(key=version_key, reverse=True)
            return versions[0]

        return None

    except Exception as e:
        print(f"  Error getting latest version from Docker Hub ({repository}): {e}")
        return None


def clear_cache():
    """Reset the per-run tag caches (see check_all_applications)."""
    _get_dockerhub_latest_version_cached.cache_clear()
    get_dockerhub_latest_tag.cache_clear()


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

            if not include_prereleases and _is_prerelease(tag_name):
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
