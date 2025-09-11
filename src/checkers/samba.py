import subprocess
from .utils import print_error


def get_samba_version(instance, target):
    """Get Samba version via SSH"""
    
    try:
        # SSH command to get Samba version
        cmd = [
            "ssh",
            "-o",
            "ConnectTimeout=10", 
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            instance,
            'smbd --version 2>/dev/null || smbstatus --version 2>/dev/null || rpm -q samba 2>/dev/null || dpkg -l | grep samba | head -1'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            if output:
                # Parse different Samba version output formats
                version = parse_samba_version(output)
                if version:
                    print(f"  {instance}: {version}")
                    return version
                else:
                    print_error(instance, f"Could not parse Samba version from: {output}")
                    return None
            else:
                print_error(instance, "No Samba version output received")
                return None
        else:
            error_msg = result.stderr.strip() if result.stderr else "SSH command failed"
            print_error(instance, f"SSH failed: {error_msg}")
            return None
            
    except subprocess.TimeoutExpired:
        print_error(instance, "SSH timeout")
        return None
    except Exception as e:
        print_error(instance, f"SSH error: {str(e)}")
        return None


def parse_samba_version(output):
    """Parse Samba version from various output formats"""
    import re
    
    # Try different parsing patterns
    patterns = [
        r'Version\s+(\d+\.\d+\.\d+)',  # "Version 4.15.2"
        r'samba\s+(\d+\.\d+\.\d+)',   # "samba 4.15.2-ubuntu"
        r'samba.*?(\d+\.\d+\.\d+)',   # Any line with samba and version
        r'(\d+\.\d+\.\d+)',           # Just version numbers
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def get_latest_samba_version(target_host):
    """
    Check for available Samba updates using SSH and apt
    
    Args:
        target_host: SSH target hostname
    
    Returns:
        str: 'update available' if updates exist, otherwise 'No updates'
    """
    if not target_host:
        return 'No updates'
        
    try:
        update_status = check_for_samba_updates(target_host)
        return update_status
    except Exception as e:
        print(f"  Error checking Samba updates: {e}")
        return 'No updates'


def check_for_samba_updates(target_host):
    """
    Check for Samba updates via SSH using apt list --upgradable
    
    Returns:
        str: 'update available' or 'No updates'
    """
    try:
        print(f"    Checking for Samba updates on {target_host}...")
        
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host, 'apt', 'list', '--upgradable'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            # Check for any Samba-related packages
            for line in result.stdout.split('\n'):
                if any(pkg in line.lower() for pkg in ['samba', 'smbd', 'nmbd', 'winbind']):
                    print("    Found Samba update available")
                    return 'update available'
            
            return 'No updates'
        
        return 'No updates'
        
    except Exception as e:
        print(f"  Error getting Samba updates via SSH: {e}")
        return 'No updates'