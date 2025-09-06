from .utils import http_get
import re

def get_mongodb_latest_version():
    """Get latest MongoDB version from GitHub tags"""
    data = http_get("https://api.github.com/repos/mongodb/mongo/tags?per_page=100")
    if data and isinstance(data, list):
        # Filter for stable release tags (format: r8.2.0, r7.0.5, etc.)
        # Exclude alpha, rc, beta versions
        stable_tags = []
        for tag in data:
            tag_name = tag["name"]
            # Look for tags that start with 'r' followed by version numbers
            if re.match(r'^r\d+\.\d+\.\d+$', tag_name):
                # Extract version (remove 'r' prefix)
                version = tag_name[1:]
                stable_tags.append(version)
        
        if stable_tags:
            # Sort versions in descending order (latest first)
            # Convert to tuples for proper version sorting
            def version_key(v):
                return tuple(map(int, v.split('.')))
            
            stable_tags.sort(key=version_key, reverse=True)
            return stable_tags[0]
    
    return None