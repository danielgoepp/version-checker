import requests
from .utils import http_get, print_error, handle_timeout_error, handle_generic_error
import config


def get_unifi_protect_latest_version():
    """Get latest UniFi Protect version from community releases RSS feed"""
    try:
        import xml.etree.ElementTree as ET
        import re
        
        # Use Ubiquiti's community releases RSS feed for UniFi Protect
        rss_url = "https://community.ui.com/rss/releases/UniFi-Protect/aada5f38-35d4-4525-9235-b14bd320e4d0"
        
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
                    # Extract version from title like "UniFi Protect Application 6.1.68"
                    version_match = re.search(r'UniFi Protect Application\s+([\d.]+)', title_text)
                    if version_match:
                        return version_match.group(1)
        
        return None
        
    except requests.exceptions.Timeout:
        print("Timeout getting latest UniFi Protect version from RSS")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting latest UniFi Protect version from RSS: {str(e)}")
        return None
    except Exception as e:
        print(f"Error parsing latest UniFi Protect version from RSS: {str(e)}")
        return None


def get_unifi_protect_version(instance, url):
    """Get UniFi Protect version from bootstrap API endpoint"""
    if not url:
        print_error(instance, "No URL provided")
        return None
    
    # Use the integration endpoint that works with API key
    base_url = url.rstrip('/')
    info_url = f"{base_url}/proxy/protect/integration/v1/meta/info"
    
    try:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Use API key authentication if configured  
        if config.UNIFI_PROTECT_API_KEY:
            headers['X-API-KEY'] = config.UNIFI_PROTECT_API_KEY
        
        response = requests.get(info_url, headers=headers, timeout=15, verify=True)
        
        if response.status_code == 401:
            print_error(instance, "Authentication required - please configure UniFi Protect API key")
            return None
        elif response.status_code == 403:
            print_error(instance, "Access forbidden - check UniFi Protect permissions")
            return None
        elif response.status_code != 200:
            print_error(instance, f"HTTP {response.status_code} - {response.reason}")
            return None
            
        data = response.json()
        
        # The integration response contains applicationVersion field
        version = data.get('applicationVersion')
        
        if version:
            return str(version)
        else:
            print_error(instance, "Version not found in integration response")
            return None
            
    except requests.exceptions.Timeout:
        return handle_timeout_error(instance, "integration API call")
    except requests.exceptions.ConnectionError as e:
        print_error(instance, f"Connection failed: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        return handle_generic_error(instance, str(e), "integration API call")
    except Exception as e:
        return handle_generic_error(instance, str(e), "version parsing")