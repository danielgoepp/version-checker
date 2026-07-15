#!/usr/bin/env python

import json
import re
import requests
import subprocess
import config

def get_ceph_version(instance):
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
            match = re.search(r'ceph version (\d+\.\d+\.\d+)', output)
            if match:
                return match.group(1)
            else:
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
    try:
        api_url = f"{url}/api2/json/version"
        headers = {
            'Authorization': f'PVEAPIToken={config.PROXMOX_API_TOKEN}'
        }

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if 'data' in data and isinstance(data['data'], dict):
                version_data = data['data']

                proxmox_version = version_data.get('version')

                if not proxmox_version:
                    proxmox_version = version_data.get('release')

                if proxmox_version:
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

def get_proxmox_latest_version(include_ceph=False):
    try:
        api_url = f"{config.PROXMOX_APT_VERSIONS_URL}/api2/json/nodes/{config.PROXMOX_APT_VERSIONS_NODE}/apt/versions"
        headers = {
            'Authorization': f'PVEAPIToken={config.PROXMOX_API_TOKEN}'
        }

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            proxmox_latest = None

            for pkg in data.get('data', []):
                if pkg.get('Package') == 'pve-manager':
                    proxmox_latest = pkg.get('Version')
                    break

            if proxmox_latest:
                if include_ceph:
                    for pkg in data.get('data', []):
                        if pkg.get('Package') == 'ceph':
                            ceph_ver = pkg.get('Version', '')
                            match = re.match(r'(\d+\.\d+\.\d+)', ceph_ver)
                            if match:
                                return f"{proxmox_latest} (Ceph {match.group(1)})"
                            break

                return proxmox_latest

            print("  pve-manager package not found in APT versions response")
            return None

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
        print(f"  Invalid JSON response from Proxmox API")
        return None
    except Exception as e:
        print(f"  Error getting latest Proxmox version: {e}")
        return None
