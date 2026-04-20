import re
import requests
from .utils import print_error


def get_opensearch_compatible_version():
    url = "https://go2docs.graylog.org/current/downloading_and_installing_graylog/compatibility_matrix.htm"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        html = response.text

        versions = re.findall(r'(\d+\.\d+\.\d+)', html)

        # Filter to 2.x only — 3.x+ is explicitly unsupported by Graylog
        opensearch_versions = [v for v in versions if int(v.split('.')[0]) == 2]

        if not opensearch_versions:
            return None

        opensearch_versions.sort(key=lambda v: [int(p) for p in v.split('.')])
        return opensearch_versions[-1]

    except Exception as e:
        print_error("opensearch", f"Error fetching Graylog compatibility matrix: {e}")
        return None
