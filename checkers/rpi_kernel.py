
def get_latest_rpi_kernel_version(current_kernel, target_host=None):
    """
    Get the latest RPi kernel version using dynamic checking via SSH and apt
    
    Args:
        current_kernel: Current kernel version string (e.g., "6.6.22-v7+")
        target_host: SSH target to check apt repositories (optional)
    
    Returns:
        str: Latest kernel version or current if up-to-date/error
    """
    try:
        # SSH-based dynamic checking
        if target_host:
            latest_via_ssh = get_latest_rpi_kernel_via_ssh(target_host)
            if latest_via_ssh == 'no update':
                # No updates available - system is current
                return current_kernel
            elif latest_via_ssh == 'kernel update available':
                # Update available - for now assume it's newer than current
                print("    RPi kernel update available (exact version unknown)")
                return 'update available'
            
        # If no newer version found, return current
        return current_kernel
        
    except Exception as e:
        print(f"  Error checking RPi kernel versions: {e}")
        return current_kernel

def get_latest_rpi_kernel_via_ssh(target_host):
    """
    Get latest available RPi kernel version via SSH using apt update + apt list --upgradable
    
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
            # Parse apt list output for raspberrypi-kernel packages
            for line in list_result.stdout.split('\n'):
                if 'raspberrypi-kernel' in line:
                    # Example line: "raspberrypi-kernel/stable 1:1.20250101~bookworm-1 arm64 [upgradable from: 1:1.20240430~bookworm-1]"
                    # For RPi, we need to check the actual running kernel after update
                    # Since package versions don't directly map to kernel versions
                    print(f"    Found RPi kernel update available")
                    # We'll need to get the current kernel and assume the update is newer
                    return 'kernel update available'
            
            # No raspberrypi-kernel packages found in upgradable list
            print(f"    No kernel updates available")
            return 'no update'
            
        return None
        
    except Exception as e:
        print(f"  Error getting RPi kernel version via SSH: {e}")
        return None



