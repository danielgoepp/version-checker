from .utils import http_get
import re
import config

def get_mongodb_latest_version():
    """Get latest stable MongoDB version from GitHub tags
    
    MongoDB's stable release series typically has the most patch releases.
    This algorithm finds the major.minor series with the most releases,
    which is likely the stable/LTS series, then returns the latest patch.
    """
    headers = {}
    if config.GITHUB_API_TOKEN:
        headers['Authorization'] = f'token {config.GITHUB_API_TOKEN}'
    
    data = http_get("https://api.github.com/repos/mongodb/mongo/tags?per_page=100", headers=headers)
    if data and isinstance(data, list):
        # Group versions by major.minor series
        series_versions = {}
        
        for tag in data:
            tag_name = tag["name"]
            # Look for stable release tags (format: rX.Y.Z)
            # Exclude alpha, rc, beta versions
            if re.match(r'^r\d+\.\d+\.\d+$', tag_name):
                # Extract version (remove 'r' prefix)
                version = tag_name[1:]
                version_parts = version.split('.')
                
                if len(version_parts) == 3:
                    # Create major.minor key (e.g., "8.0", "8.1", "7.3")
                    series_key = f"{version_parts[0]}.{version_parts[1]}"
                    
                    if series_key not in series_versions:
                        series_versions[series_key] = []
                    series_versions[series_key].append(version)
        
        if not series_versions:
            return None
        
        # Find the series with the most releases (likely the stable/LTS series)
        stable_series = max(series_versions.keys(), key=lambda k: len(series_versions[k]))
        
        # Convert to tuples for proper version sorting
        def version_key(v):
            return tuple(map(int, v.split('.')))
        
        # Return the latest patch version from the most active series
        stable_versions = series_versions[stable_series]
        stable_versions.sort(key=version_key, reverse=True)
        
        print(f"  MongoDB: Found {len(stable_versions)} releases in {stable_series} series (stable)")
        return stable_versions[0]
    
    return None