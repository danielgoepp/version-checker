#!/usr/bin/env python3

"""
Script to refresh the Proxmox-Ceph compatibility matrix.
Fetches official version mappings from Proxmox documentation.
"""

import json
import requests
import re
from datetime import datetime

def fetch_proxmox_roadmap():
    """
    Fetch Proxmox roadmap for official Ceph version information
    """
    try:
        response = requests.get("https://pve.proxmox.com/wiki/Roadmap", timeout=8)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to fetch Proxmox roadmap: HTTP {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print("Timeout fetching Proxmox roadmap")
        return None
    except Exception as e:
        print(f"Error fetching Proxmox roadmap: {e}")
        return None

def parse_ceph_versions_from_roadmap(html_content):
    """
    Parse Ceph version information from Proxmox roadmap HTML
    """
    if not html_content:
        return {}
    
    version_mapping = {}
    
    # Look for patterns with stricter validation to avoid false positives
    ceph_patterns = [
        # Direct Proxmox VE version mapping patterns
        r'Proxmox\s+VE\s+([5-9]\.\d+).*?Ceph\s+(?:Squid\s+)?(\d+\.\d+\.\d+)',
        r'PVE\s+([5-9]\.\d+).*?Ceph\s+(?:Squid\s+)?(\d+\.\d+\.\d+)'
    ]
    
    print("  Searching for Ceph version patterns in roadmap...")
    
    for pattern in ceph_patterns:
        matches = re.finditer(pattern, html_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            pve_version = match.group(1)
            ceph_version = match.group(2)
            # Validate Proxmox version is reasonable (5.x - 9.x)
            if pve_version and float(pve_version) >= 5.0 and float(pve_version) < 10.0:
                if pve_version not in version_mapping:
                    version_mapping[pve_version] = ceph_version
                    print(f"  Found: Proxmox {pve_version} -> Ceph {ceph_version}")
    
    return version_mapping

def get_documentation_versions():
    """
    Fetch and parse Proxmox-Ceph versions from official documentation
    """
    print("Fetching versions from Proxmox documentation...")
    
    roadmap_content = fetch_proxmox_roadmap()
    if not roadmap_content:
        print("  Unable to fetch roadmap, skipping documentation verification")
        return {}
    
    roadmap_versions = parse_ceph_versions_from_roadmap(roadmap_content)
    print(f"  Found {len(roadmap_versions)} verified versions from documentation")
    
    return roadmap_versions


def generate_compatibility_matrix():
    """
    Generate compatibility matrix from official Proxmox documentation only
    """
    # Get documentation versions - this is our only source now
    doc_versions = get_documentation_versions()
    
    if not doc_versions:
        print("❌ No versions found in documentation - cannot generate matrix")
        return {}
    
    print(f"\nGenerating matrix from {len(doc_versions)} documented versions:")
    for pve_version, ceph_version in doc_versions.items():
        print(f"  Proxmox {pve_version} -> Ceph {ceph_version}")
    
    # Filter to only current/relevant Proxmox versions (5.x - 9.x)
    filtered_matrix = {}
    for pve_version, ceph_version in doc_versions.items():
        try:
            version_float = float(pve_version)
            if 5.0 <= version_float < 10.0:
                filtered_matrix[pve_version] = ceph_version
        except ValueError:
            continue
    
    # Display final matrix
    print("\nFinal compatibility matrix (documentation only):")
    for pve_version, ceph_version in sorted(filtered_matrix.items(), key=lambda x: x[0], reverse=True):
        print(f"  Proxmox {pve_version} -> Ceph {ceph_version}")
    
    return filtered_matrix


def save_matrix_to_file(matrix):
    """
    Save the compatibility matrix to a JSON file
    """
    cache_data = {
        "last_updated": datetime.now().isoformat(),
        "compatibility_matrix": matrix
    }
    
    cache_file = "proxmox_ceph_compatibility.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print(f"Compatibility matrix saved to {cache_file}")
        return True
    except Exception as e:
        print(f"Error saving matrix to file: {e}")
        return False


def main():
    """
    Main function to refresh the compatibility matrix
    """
    print("=== Proxmox-Ceph Compatibility Matrix Refresh ===")
    print()
    
    # Generate new matrix
    print("Generating new compatibility matrix...")
    matrix = generate_compatibility_matrix()
    
    # Save to file
    if save_matrix_to_file(matrix):
        print("\n✅ Matrix updated successfully!")
        print("\nCurrent compatibility matrix:")
        for pve_version, ceph_version in sorted(matrix.items(), key=lambda x: x[0], reverse=True):
            print(f"  Proxmox {pve_version} -> Ceph {ceph_version}")
    else:
        print("\n❌ Failed to save matrix to file")
    
    print(f"\nTo use this updated matrix, restart your version checker.")

if __name__ == "__main__":
    main()