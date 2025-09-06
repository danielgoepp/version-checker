#!/usr/bin/env python

import json
import requests
# No longer need utils import - using requests directly
import config

def get_proxmox_version(instance, url):
    """
    Get Proxmox VE version information via API
    
    Args:
        instance: Instance name (e.g., pve11, pve12, pve13, pve15)
        url: Base URL of the Proxmox server (e.g., https://pve11.goepp.net:8006)
    
    Returns:
        dict: Contains current_version and latest_version, or None on error
    """
    try:
        
        # Construct the API endpoint
        api_url = f"{url}/api2/json/version"
        
        # Set up authentication headers using API token
        headers = {
            'Authorization': f'PVEAPIToken={config.PROXMOX_API_TOKEN}'
        }
        
        # Make the API call with authentication
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract version information from the response
            if 'data' in data and isinstance(data['data'], dict):
                version_data = data['data']
                
                # The API returns version information in a simple dict format
                # Use the 'version' field which contains the full version number
                current_version = version_data.get('version')
                
                if current_version:
                    return current_version
                
                # Fallback to 'release' if version is not available
                return version_data.get('release')
                
        elif response.status_code == 401:
            print(f"  Authentication failed for {instance} Proxmox API (401 Unauthorized)")
            print(f"  Response: {response.text}")
            return None
        else:
            print(f"  Failed to get Proxmox version for {instance}: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectTimeout:
        print(f"  Connection timeout to {instance} Proxmox server")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  Connection error to {instance} Proxmox server")
        return None
    except json.JSONDecodeError:
        print(f"  Invalid JSON response from {instance} Proxmox server")
        return None
    except Exception as e:
        print(f"  Error checking Proxmox version for {instance}: {e}")
        return None

def get_proxmox_latest_version():
    """
    Get latest Proxmox VE version from endoflife.date API
    
    Returns:
        str: Latest version string or None
    """
    try:
        # Use endoflife.date API for Proxmox VE version information
        api_url = "https://endoflife.date/api/proxmox-ve.json"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            versions = response.json()
            
            # The API returns an array of version objects, sorted with latest first
            if versions and len(versions) > 0:
                latest = versions[0]
                
                # Use the 'latest' field which has more detailed version info like "9.0"
                if 'latest' in latest:
                    return latest['latest']
                
                # Fallback to cycle field if latest is not available
                if 'cycle' in latest:
                    return latest['cycle']
            
        else:
            print(f"  Failed to get latest Proxmox version: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.ConnectTimeout:
        print(f"  Connection timeout getting latest Proxmox version")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  Connection error getting latest Proxmox version")
        return None
    except json.JSONDecodeError:
        print(f"  Invalid JSON response from endoflife.date API")
        return None
    except Exception as e:
        print(f"  Error getting latest Proxmox version: {e}")
        return None