import subprocess
from .utils import print_error, print_version, extract_semantic_version

def get_docker_version(instance, hostname):
    """Get Docker version from remote host via SSH"""
    try:
        # SSH to the host and get Docker version
        cmd = f"ssh {hostname} 'sudo docker version --format \"{{{{.Server.Version}}}}\"'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            print_version(instance, version)
            return version
        else:
            print_error(instance, f"Error getting Docker version: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print_error(instance, "Timeout getting Docker version")
        return None
    except Exception as e:
        print_error(instance, f"Error getting Docker version: {e}")
        return None