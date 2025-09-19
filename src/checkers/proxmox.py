#!/usr/bin/env python

import json
import requests
import subprocess
import os
from pathlib import Path
# No longer need utils import - using requests directly
import config

def get_ceph_version(instance):
    """
    Get Ceph version via SSH
    
    Args:
        instance: Instance name (e.g., pve11, pve12, pve13, pve15)
    
    Returns:
        str: Ceph version or None if not available
    """
    try:
        cmd = [
            "ssh",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes", 
            "-o", "StrictHostKeyChecking=no",
            f"root@{instance}",
            "ceph --version 2>/dev/null"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse "ceph version 18.2.4 (e6ccd7ba688e)"
            import re
            match = re.search(r'ceph version (\d+\.\d+\.\d+)', output)
            if match:
                return match.group(1)
            else:
                # Fallback: try to extract version from output
                parts = output.split()
                if len(parts) >= 3 and parts[0] == 'ceph' and parts[1] == 'version':
                    return parts[2]
        
        return None
        
    except subprocess.TimeoutExpired:
        print(f"  SSH timeout getting Ceph version for {instance}")
        return None
    except Exception as e:
        print(f"  Error getting Ceph version for {instance}: {e}")
        return None


def get_proxmox_version(instance, url):
    """
    Get Proxmox VE version information via API and Ceph version via SSH
    
    Args:
        instance: Instance name (e.g., pve11, pve12, pve13, pve15)
        url: Base URL of the Proxmox server (e.g., https://pve11.goepp.net:8006)
    
    Returns:
        str: Combined Proxmox + Ceph version or Proxmox version only
    """
    try:
        
        # Construct the API endpoint
        api_url = f"{url}/api2/json/version"
        
        # Set up authentication headers using API token
        headers = {
            'Authorization': f'PVEAPIToken={config.PROXMOX_API_TOKEN}'
        }
        
        # Make the API call with authentication
        response = requests.get(api_url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract version information from the response
            if 'data' in data and isinstance(data['data'], dict):
                version_data = data['data']
                
                # The API returns version information in a simple dict format
                # Use the 'version' field which contains the full version number
                proxmox_version = version_data.get('version')
                
                if not proxmox_version:
                    # Fallback to 'release' if version is not available
                    proxmox_version = version_data.get('release')
                
                if proxmox_version:
                    # Get Ceph version via SSH
                    ceph_version = get_ceph_version(instance)
                    
                    if ceph_version:
                        combined_version = f"{proxmox_version} (Ceph {ceph_version})"
                        print(f"  {instance}: Proxmox {proxmox_version}, Ceph {ceph_version}")
                        return combined_version
                    else:
                        print(f"  {instance}: Proxmox {proxmox_version}")
                        return proxmox_version
                
                return None
                
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

def load_compatibility_matrix():
    """
    Load Proxmox-Ceph compatibility matrix from cache file
    
    Returns:
        dict: Compatibility matrix or empty dict if not available
    """
    cache_file = Path(__file__).parent.parent.parent / "proxmox_ceph_compatibility.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            return cache_data.get('compatibility_matrix', {})
        except Exception as e:
            print(f"  Error: Failed to load compatibility cache: {e}")
            print(f"  Run 'python3 refresh_proxmox_ceph_matrix.py' to generate compatibility data")
            return {}
    else:
        print(f"  Error: Compatibility matrix not found at {cache_file}")
        print(f"  Run 'python3 refresh_proxmox_ceph_matrix.py' to generate compatibility data")
        return {}

def get_ceph_latest_version_for_proxmox(proxmox_version):
    """
    Get latest supported Ceph version for a specific Proxmox version
    
    Args:
        proxmox_version: Proxmox version string (e.g., "9.0", "8.4.12")
    
    Returns:
        str: Latest supported Ceph version for that Proxmox version or None
    """
    if not proxmox_version:
        return None
        
    # Load compatibility matrix (from cache or hardcoded fallback)
    proxmox_ceph_compatibility = load_compatibility_matrix()
        
    # Extract major.minor version for compatibility check
    import re
    match = re.match(r'(\d+\.\d+)', proxmox_version)
    if not match:
        return None
        
    version_key = match.group(1)
    
    # Return the supported Ceph version for this Proxmox version
    return proxmox_ceph_compatibility.get(version_key)


def compare_proxmox_versions(current_version, latest_version):
    """
    Compare Proxmox versions properly handling patch releases

    Args:
        current_version: Current version string (e.g., "9.0.10")
        latest_version: Latest version string (e.g., "9.0")

    Returns:
        int: -1 if current < latest, 0 if equal, 1 if current > latest
    """
    if not current_version or not latest_version:
        return 0

    import re

    # Extract version numbers
    current_match = re.match(r'(\d+)\.(\d+)(?:\.(\d+))?', current_version)
    latest_match = re.match(r'(\d+)\.(\d+)(?:\.(\d+))?', latest_version)

    if not current_match or not latest_match:
        return 0

    # Parse version components
    current_major = int(current_match.group(1))
    current_minor = int(current_match.group(2))
    current_patch = int(current_match.group(3) or 0)

    latest_major = int(latest_match.group(1))
    latest_minor = int(latest_match.group(2))
    latest_patch = int(latest_match.group(3) or 0)

    # Compare versions
    if current_major != latest_major:
        return -1 if current_major < latest_major else 1
    if current_minor != latest_minor:
        return -1 if current_minor < latest_minor else 1
    if current_patch != latest_patch:
        return -1 if current_patch < latest_patch else 1

    return 0

def get_proxmox_latest_version(include_ceph=False, current_version=None):
    """
    Get latest Proxmox VE version from endoflife.date API, optionally with Ceph

    Args:
        include_ceph: Whether to include Ceph latest version
        current_version: Current version for intelligent comparison

    Returns:
        str: Latest version string (possibly combined with Ceph) or None
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
                proxmox_latest = latest.get('latest') or latest.get('cycle')

                if proxmox_latest and current_version:
                    # If current version is a patch release of the same major.minor,
                    # use the current version as the latest to avoid false update notifications
                    comparison = compare_proxmox_versions(current_version.split()[0], proxmox_latest)
                    if comparison >= 0:  # Current is same or newer
                        # Extract just the version part from current_version
                        import re
                        match = re.match(r'(\d+\.\d+(?:\.\d+)?)', current_version)
                        if match:
                            proxmox_latest = match.group(1)

                if proxmox_latest:
                    if include_ceph:
                        # Get latest supported Ceph version for this Proxmox version
                        ceph_latest = get_ceph_latest_version_for_proxmox(proxmox_latest)
                        if ceph_latest:
                            return f"{proxmox_latest} (Ceph {ceph_latest})"

                    return proxmox_latest

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