import requests
from .utils import print_error, handle_timeout_error, handle_generic_error
import config


def get_unifi_os_nvr_latest_version(current_version=None):
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
        
        response = requests.get(rss_url, headers=headers, timeout=30, verify=True)
        
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
                        rss_version = version_match.group(1)
                        
                        # Special handling for early access users:
                        # If current version is newer than RSS stable version, use current as latest
                        if current_version and _is_version_newer(current_version, rss_version):
                            return current_version
                        
                        return rss_version
        
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


def _is_version_newer(version1, version2):
    """Compare semantic versions - returns True if version1 is newer than version2"""
    try:
        def version_tuple(v):
            return tuple(map(int, (v.split("."))))
        return version_tuple(version1) > version_tuple(version2)
    except:
        return False


def get_unifi_os_version(instance, url):
    """Get UniFi OS version via SSH command"""
    from .utils import ssh_get_version
    import re
    
    # Extract hostname from URL
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    
    if not hostname:
        print_error(instance, "Could not extract hostname from URL")
        return None
    
    # UniFi OS uses root user for SSH access
    ssh_target = f"root@{hostname}"
    
    # Try commands to get UniFi OS version (prioritize most reliable ones)
    commands_to_try = [
        "cat /usr/lib/version",
        "cat /etc/unifi-os/version",
        "unifi-os info 2>/dev/null | grep -i version || true"
    ]
    
    for command in commands_to_try:
        result = ssh_get_version(instance, ssh_target, command)
        if result and result.strip():
            
            # Parse version from the result
            # Pattern for /usr/lib/version: UNVR4.al324.v4.4.2.b26bf4a.250901.1127
            version_patterns = [
                r'\.v(\d+\.\d+\.\d+)\.',  # .v4.4.2. pattern from /usr/lib/version
                r'(\d+\.\d+\.\d+)',        # Any x.y.z pattern
            ]
            
            for pattern in version_patterns:
                match = re.search(pattern, result)
                if match:
                    version = match.group(1)
                    return version
    
    print_error(instance, "Could not determine UniFi OS version via SSH")
    return None