from .utils import http_get
import re


def get_dockerhub_latest_version(repository, version_pattern=None, exclude_tags=None):
    """
    Get latest version from Docker Hub API
    
    Args:
        repository: Docker Hub repository (e.g., 'boky/postfix')
        version_pattern: Regex pattern to match version tags (default: semantic versioning)
        exclude_tags: List of tag names to exclude (default: common non-version tags)
    
    Returns:
        Latest version string or None
    """
    try:
        # Docker Hub API endpoint for repository tags
        url = f"https://registry.hub.docker.com/v2/repositories/{repository}/tags/?page_size=100"
        
        data = http_get(url, timeout=15)
        
        if not (data and isinstance(data, dict) and 'results' in data):
            return None
        
        # Default version pattern for semantic versioning
        if version_pattern is None:
            version_pattern = re.compile(r'^v?(\d+\.\d+(?:\.\d+)?)$')
        
        # Default exclusion list
        if exclude_tags is None:
            exclude_tags = [
                'latest', 'edge', 'dev', 'devel', 'develop', 'main', 'master',
                'edge-ubuntu', 'edge-alpine', 'edge-debian', 
                'nightly', 'unstable', 'beta', 'alpha', 'rc'
            ]
        
        versions = []
        
        for tag in data['results']:
            tag_name = tag.get('name', '')
            
            # Skip excluded tags
            if tag_name in exclude_tags or any(excluded in tag_name.lower() for excluded in ['rc', 'beta', 'alpha']):
                continue
                
            if isinstance(version_pattern, str):
                version_pattern = re.compile(version_pattern)
                
            match = version_pattern.match(tag_name)
            if match:
                # Use the first capture group if available, otherwise the full match
                version = match.group(1) if match.groups() else match.group(0)
                versions.append(version)
        
        if versions:
            # Sort versions numerically and return the highest
            def version_key(v):
                # Handle MinIO's date format (YYYY-MM-DDTHH-MM-SSZ)
                if 'T' in v and 'Z' in v:
                    # Parse MinIO date format for sorting
                    try:
                        from datetime import datetime
                        # Convert format like "2025-07-23T15-54-02Z" to datetime for sorting
                        date_part = v.replace('-', ':', 2).replace('-', ':', 1)  # Fix time format
                        date_part = date_part.replace(':', '-', 2)  # Keep date format
                        return datetime.strptime(date_part, "%Y-%m-%dT%H:%M:%SZ")
                    except:
                        # If parsing fails, fall back to string sorting
                        return v
                else:
                    # Handle standard semantic versions like "1.2.3" or "1.2"
                    try:
                        parts = v.split('.')
                        return tuple(int(part) for part in parts)
                    except:
                        # If parsing fails, fall back to string sorting
                        return v
            
            versions.sort(key=version_key, reverse=True)
            return versions[0]
        
        return None
        
    except Exception as e:
        print(f"  Error getting latest version from Docker Hub ({repository}): {e}")
        return None


def get_dockerhub_latest_tag(repository, include_prereleases=False):
    """
    Get latest tag from Docker Hub API (simple tag-based approach)
    
    Args:
        repository: Docker Hub repository (e.g., 'boky/postfix')
        include_prereleases: Whether to include prerelease tags
    
    Returns:
        Latest tag name or None
    """
    try:
        url = f"https://registry.hub.docker.com/v2/repositories/{repository}/tags/?page_size=10"
        
        data = http_get(url, timeout=15)
        
        if not (data and isinstance(data, dict) and 'results' in data):
            return None
        
        for tag in data['results']:
            tag_name = tag.get('name', '')
            
            # Skip 'latest' tag
            if tag_name == 'latest':
                continue
            
            # Skip prerelease tags unless requested
            if not include_prereleases:
                if any(prerelease in tag_name.lower() for prerelease in ['rc', 'beta', 'alpha', 'edge', 'nightly']):
                    continue
            
            return tag_name
        
        return None
        
    except Exception as e:
        print(f"  Error getting latest tag from Docker Hub ({repository}): {e}")
        return None