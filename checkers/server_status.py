import subprocess
from .utils import print_error
from .rpi_kernel import get_latest_rpi_kernel_version

def check_server_status(instance, target):
    """Check Linux version via SSH"""
    if not target:
        print_error(instance, "No target configured")
        return None
    
    try:
        # SSH command to get hostname, kernel, and full OS info
        cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", target, 
               "hostname && uname -r && . /etc/os-release && echo \"$PRETTY_NAME\""]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 3:
                hostname = lines[0].strip()
                kernel = lines[1].strip()
                pretty_name = lines[2].strip().strip('"')  # Remove quotes from PRETTY_NAME
                
                # Format: hostname | Kernel | Full Name
                linux_info = f"{hostname} │ {kernel} │ {pretty_name}"
                print(f"  {instance}: {linux_info}")
                
                # Get latest kernel version for comparison
                latest_kernel = get_latest_rpi_kernel_version(kernel)
                
                return {
                    'hostname': hostname,
                    'kernel': kernel,
                    'latest_kernel': latest_kernel,
                    'os_name': pretty_name,
                    'display_info': linux_info
                }
            else:
                print_error(instance, "Incomplete system information")
                return None
        else:
            print_error(instance, f"SSH failed: {result.stderr.strip()}")
            return None
            
    except subprocess.TimeoutExpired:
        print_error(instance, "SSH timeout")
        return None
    except Exception as e:
        print_error(instance, f"SSH error: {e}")
        return None

