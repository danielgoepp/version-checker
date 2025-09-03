import requests
import re
from .utils import http_get

def get_latest_rpi_kernel_version(current_kernel):
    """
    Get the latest RPi kernel version using known latest versions by architecture
    This is a simplified approach until we can reliably parse RPi repositories
    """
    try:
        # Extract architecture from current kernel
        arch = extract_kernel_architecture(current_kernel)
        if not arch:
            return None
        
        # Extract current version numbers
        current_match = re.search(r'(\d+)\.(\d+)\.(\d+)', current_kernel)
        if not current_match:
            return None
            
        current_major = int(current_match.group(1))
        current_minor = int(current_match.group(2))
        current_patch = int(current_match.group(3))
        
        # Known latest kernel versions by architecture (manually maintained)
        # These should be updated periodically
        latest_versions = {
            'rpi-v8': '6.12.34+rpt-rpi-v8',
            'rpi-2712': '6.12.34+rpt-rpi-2712', 
            'rpi-v7': '6.12.34+rpt-rpi-v7',
            'rpi-v7l': '6.12.34+rpt-rpi-v7l',
            'v7+': '6.6.62-v7+',  # Older Pi models may use different kernel series
            'v8+': '6.6.62-v8+',
            'v6': '6.6.62-v6'
        }
        
        latest_kernel = latest_versions.get(arch)
        if not latest_kernel:
            return None
            
        # Extract latest version numbers
        latest_match = re.search(r'(\d+)\.(\d+)\.(\d+)', latest_kernel)
        if not latest_match:
            return None
            
        latest_major = int(latest_match.group(1))
        latest_minor = int(latest_match.group(2))
        latest_patch = int(latest_match.group(3))
        
        # Compare versions
        current_tuple = (current_major, current_minor, current_patch)
        latest_tuple = (latest_major, latest_minor, latest_patch)
        
        # Only return latest if it's actually newer
        if latest_tuple > current_tuple:
            return latest_kernel
        else:
            # Current is up to date or newer
            return current_kernel
        
    except Exception as e:
        print(f"Error checking RPi kernel versions: {e}")
        return None

def extract_kernel_architecture(kernel_version):
    """
    Extract architecture suffix from kernel version
    Examples:
    - 6.12.34+rpt-rpi-v8 -> rpi-v8
    - 6.12.34+rpt-rpi-2712 -> rpi-2712  
    - 6.6.22-v7+ -> v7+
    """
    # Pattern for RPi kernel architectures
    arch_patterns = [
        r'rpi-v8',
        r'rpi-2712', 
        r'rpi-v7l',
        r'rpi-v7',
        r'v8\+',
        r'v7\+',
        r'v6'
    ]
    
    for pattern in arch_patterns:
        match = re.search(pattern, kernel_version)
        if match:
            return match.group(0)
    
    return None

def extract_build_number(kernel_version):
    """
    Extract build number from kernel version
    Example: 6.12.34+rpt-rpi-v8 -> 34
    """
    match = re.search(r'(\d+\.\d+)\.(\d+)', kernel_version)
    if match:
        return match.group(2)
    return None

def get_debian_kernel_version():
    """
    Alternative: Check Debian repositories for latest RPi kernel packages
    This is more accurate for systems running Debian/Raspbian
    """
    try:
        # Check Debian package repository for raspberrypi-kernel
        # This would require parsing Debian package listings
        # For now, return None as this is more complex to implement
        return None
    except:
        return None