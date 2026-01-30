import re
import requests
from .utils import print_error


def get_opensearch_compatible_version():
    """Get the latest OpenSearch version supported by Graylog from the compatibility matrix"""
    url = "https://go2docs.graylog.org/current/downloading_and_installing_graylog/compatibility_matrix.htm"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        html = response.text

        # Find all OpenSearch version patterns like "2.19.4" in the page
        versions = re.findall(r'(\d+\.\d+\.\d+)', html)

        # Filter to 2.x versions only (3.x+ is explicitly unsupported)
        opensearch_versions = []
        for v in versions:
            parts = v.split('.')
            major = int(parts[0])
            if major == 2:
                opensearch_versions.append(v)

        if not opensearch_versions:
            return None

        # Sort by version components and return the highest
        opensearch_versions.sort(key=lambda v: [int(p) for p in v.split('.')])
        return opensearch_versions[-1]

    except Exception as e:
        print_error("opensearch", f"Error fetching Graylog compatibility matrix: {e}")
        return None
