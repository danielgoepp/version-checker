#!/usr/bin/env python

import re

def get_latest_ubuntu_kernel_version(current_kernel, target_host=None):
    """
    Get the latest Ubuntu kernel version using dynamic checking via SSH and apt
    
    Args:
        current_kernel: Current kernel version string (e.g., "6.8.0-79-generic")
        target_host: SSH target to check apt repositories (optional)
    
    Returns:
        str: Latest kernel version or current if up-to-date/error
    """
    try:
        # SSH-based dynamic checking
        if target_host:
            latest_via_ssh = get_latest_kernel_via_ssh(target_host)
            if latest_via_ssh == 'no update':
                # No updates available - system is current
                return current_kernel
            elif latest_via_ssh and latest_via_ssh != current_kernel:
                if is_newer_ubuntu_kernel(latest_via_ssh, current_kernel):
                    return latest_via_ssh
            
        # If no newer version found, return current
        return current_kernel
        
    except Exception as e:
        print(f"  Error checking Ubuntu kernel versions: {e}")
        return current_kernel

def get_latest_kernel_via_ssh(target_host):
    """
    Get latest available kernel version via SSH using apt update + apt list --upgradable
    
    Args:
        target_host: SSH target (user@host or just host)
    
    Returns:
        str: Latest available kernel version or 'no update' if none available
    """
    try:
        import subprocess
        
        print(f"    Updating package lists on {target_host}...")
        # First run apt update to refresh package lists
        update_cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host, 
            'sudo', 'apt', 'update', '-qq'
        ]
        
        update_result = subprocess.run(update_cmd, capture_output=True, text=True, timeout=30)
        
        if update_result.returncode != 0:
            print(f"    apt update failed: {update_result.stderr}")
            return None
        
        print(f"    Checking for kernel updates...")
        # Then run apt list --upgradable to see what can be upgraded
        list_cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host, 
            'apt', 'list', '--upgradable'
        ]
        
        list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=15)
        
        if list_result.returncode == 0:
            # Parse apt list output for linux-image packages
            for line in list_result.stdout.split('\n'):
                if 'linux-image-' in line and 'generic' in line:
                    # Example line: "linux-image-generic/noble-updates,noble-security 6.8.0.85.85 amd64 [upgradable from: 6.8.0.79.79]"
                    # Extract the version being upgraded to
                    version_match = re.search(r'linux-image-generic\S*\s+(\S+)', line)
                    if version_match:
                        package_version = version_match.group(1)
                        
                        # Convert package version to kernel version format
                        # Package: 6.8.0.85.85 -> Kernel: 6.8.0-85-generic
                        version_parts = package_version.split('.')
                        if len(version_parts) >= 4:
                            major, minor, patch = version_parts[0], version_parts[1], version_parts[2]
                            abi = version_parts[3]
                            kernel_version = f"{major}.{minor}.{patch}-{abi}-generic"
                            print(f"    Found kernel update available: {kernel_version}")
                            return kernel_version
            
            # No linux-image packages found in upgradable list
            print(f"    No kernel updates available")
            return 'no update'
            
        return None
        
    except Exception as e:
        print(f"  Error getting kernel version via SSH: {e}")
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