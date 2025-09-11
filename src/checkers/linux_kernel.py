#!/usr/bin/env python

import subprocess

def get_latest_linux_kernel_version(current_kernel, target_host):
    """
    Check for available kernel updates using SSH and apt
    
    Args:
        current_kernel: Current kernel version string
        target_host: SSH target hostname
    
    Returns:
        str: 'update available' if updates exist, otherwise current_kernel
    """
    if not target_host:
        return current_kernel
        
    try:
        update_status = check_for_kernel_updates(target_host)
        return update_status if update_status == 'update available' else current_kernel
    except Exception as e:
        print(f"  Error checking kernel versions: {e}")
        return current_kernel

def check_for_kernel_updates(target_host):
    """
    Check for kernel updates via SSH using apt list --upgradable
    
    Returns:
        str: 'update available' or 'no update'
    """
    try:
        print(f"    Checking for kernel updates on {target_host}...")
        
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host, 'apt', 'list', '--upgradable'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            # Check for any kernel-related packages
            for line in result.stdout.split('\n'):
                if ('linux-image-' in line and 'generic' in line) or 'raspberrypi-kernel' in line:
                    print("    Found kernel update available")
                    return 'update available'
            
            return 'no update'
        
        return 'no update'
        
    except Exception as e:
        print(f"  Error getting kernel updates via SSH: {e}")
        return 'no update'

