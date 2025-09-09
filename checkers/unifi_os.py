import requests
from .utils import print_error, handle_timeout_error, handle_generic_error


def get_unifi_os_nvr_latest_version():
    """Get latest UniFi OS version for UNVR/NVR devices from community releases RSS feed"""
    try:
        import xml.etree.ElementTree as ET
        import re
        
        # Use Ubiquiti's community releases RSS feed for UniFi OS NVR/UNVR
        rss_url = "https://community.ui.com/rss/releases/UniFi%20Protect%20NVR/ba34c1fa-d237-4161-872b-c3104ef77085"
        
        headers = {
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'User-Agent': 'Version Checker 1.0'
        }
        
        response = requests.get(rss_url, headers=headers, timeout=15, verify=True)
        
        if response.status_code == 200:
            # Parse the RSS XML
            root = ET.fromstring(response.content)
            
            # Look for the first (most recent) item in the RSS feed
            items = root.findall('.//item')
            if items:
                first_item = items[0]
                title = first_item.find('title')
                if title is not None:
                    title_text = title.text
                    # Extract version from title like "UniFi OS - Network Video Recorders 4.3.6"
                    version_match = re.search(r'UniFi OS - Network Video Recorders\s+([\d.]+)', title_text)
                    if version_match:
                        return version_match.group(1)
        
        return None
        
    except requests.exceptions.Timeout:
        print("Timeout getting latest UniFi OS NVR version from RSS")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting latest UniFi OS NVR version from RSS: {str(e)}")
        return None
    except Exception as e:
        print(f"Error parsing latest UniFi OS NVR version from RSS: {str(e)}")
        return None