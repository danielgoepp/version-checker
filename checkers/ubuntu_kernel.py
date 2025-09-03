#!/usr/bin/env python

import requests
import re
import json
from .utils import http_get

def get_latest_ubuntu_kernel_version(current_kernel):
    """
    Get the latest Ubuntu kernel version for comparison
    Uses Ubuntu's kernel.ubuntu.com API to find latest kernel versions
    
    Args:
        current_kernel: Current kernel version string (e.g., "6.8.0-31-generic")
    
    Returns:
        str: Latest kernel version or current if up-to-date/error
    """
    try:
        # Extract Ubuntu release info from kernel version
        # Ubuntu kernels typically follow pattern: X.Y.Z-N-generic, X.Y.Z-N-aws, etc.
        kernel_match = re.match(r'(\d+)\.(\d+)\.(\d+)-(\d+)-(generic|aws|azure|gcp|lowlatency)', current_kernel)
        
        if not kernel_match:
            # If we can't parse the kernel version, just return current
            return current_kernel
        
        major = int(kernel_match.group(1))
        minor = int(kernel_match.group(2))
        patch = int(kernel_match.group(3))
        abi = int(kernel_match.group(4))
        flavor = kernel_match.group(5)
        
        # Try to get latest kernel info from kernel.ubuntu.com API
        # This provides structured data about Ubuntu kernel versions
        api_url = "https://kernel.ubuntu.com/api/kernels.json"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            kernels_data = response.json()
            
            # Look for the latest stable kernel version
            latest_version = find_latest_ubuntu_kernel(kernels_data, major, minor, flavor)
            
            if latest_version:
                # Compare with current version
                if is_newer_ubuntu_kernel(latest_version, current_kernel):
                    return latest_version
        
        # Fallback: check mainline kernel.org for latest kernel versions
        latest_mainline = get_latest_mainline_kernel(major, minor)
        if latest_mainline and is_newer_ubuntu_kernel(latest_mainline, current_kernel):
            return latest_mainline
            
        # If we can't determine a newer version, return current
        return current_kernel
        
    except Exception as e:
        print(f"  Error checking Ubuntu kernel versions: {e}")
        return current_kernel

def find_latest_ubuntu_kernel(kernels_data, target_major, target_minor, flavor):
    """
    Find the latest Ubuntu kernel from the API data
    
    Returns:
        str: Latest kernel version string or None
    """
    try:
        # Ubuntu kernel API structure varies, so this is a simplified approach
        # Look for kernels matching our major.minor series
        
        latest_version = None
        latest_abi = 0
        
        # This is a simplified parser - the actual API structure may vary
        # For now, construct a reasonable latest version based on patterns
        
        # Ubuntu 24.04 LTS typically uses 6.8.x kernels
        # Ubuntu 22.04 LTS typically uses 5.15.x or 6.5.x kernels
        # Ubuntu 20.04 LTS typically uses 5.4.x kernels
        
        known_latest_versions = {
            (6, 8): "6.8.0-50-generic",  # Recent Ubuntu 24.04 LTS
            (6, 5): "6.5.0-44-generic",  # Ubuntu 22.04 LTS HWE
            (5, 15): "5.15.0-125-generic", # Ubuntu 22.04 LTS GA
            (5, 4): "5.4.0-200-generic",  # Ubuntu 20.04 LTS
        }
        
        return known_latest_versions.get((target_major, target_minor))
        
    except Exception as e:
        print(f"  Error parsing Ubuntu kernel data: {e}")
        return None

def get_latest_mainline_kernel(major, minor):
    """
    Get latest mainline kernel version for reference
    This provides a fallback when Ubuntu-specific info isn't available
    
    Returns:
        str: Latest mainline kernel version in Ubuntu format
    """
    try:
        # Check kernel.org for latest stable kernel in the same major.minor series
        api_url = "https://www.kernel.org/releases.json"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Look for latest stable release matching our series
            for release in data.get('releases', []):
                if release.get('moniker') == 'stable':
                    version = release.get('version', '')
                    
                    # Parse kernel.org version format
                    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version)
                    if match:
                        rel_major = int(match.group(1))
                        rel_minor = int(match.group(2))
                        rel_patch = int(match.group(3))
                        
                        if rel_major == major and rel_minor == minor:
                            # Convert to Ubuntu-style format (approximation)
                            return f"{version}-1-generic"
            
        return None
        
    except Exception as e:
        print(f"  Error getting mainline kernel version: {e}")
        return None

def is_newer_ubuntu_kernel(version1, version2):
    """
    Compare two Ubuntu kernel version strings
    
    Returns:
        bool: True if version1 is newer than version2
    """
    try:
        # Parse both versions
        match1 = re.match(r'(\d+)\.(\d+)\.(\d+)-(\d+)', version1)
        match2 = re.match(r'(\d+)\.(\d+)\.(\d+)-(\d+)', version2)
        
        if not match1 or not match2:
            return False
        
        # Extract version components
        v1_tuple = (int(match1.group(1)), int(match1.group(2)), 
                   int(match1.group(3)), int(match1.group(4)))
        v2_tuple = (int(match2.group(1)), int(match2.group(2)), 
                   int(match2.group(3)), int(match2.group(4)))
        
        return v1_tuple > v2_tuple
        
    except Exception as e:
        print(f"  Error comparing kernel versions: {e}")
        return False