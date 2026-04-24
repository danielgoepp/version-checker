#!/usr/bin/env python

import subprocess

_STATUS_NO_UPDATE = 'No updates'


def get_latest_linux_kernel_version(current_kernel, target_host):
    if not target_host:
        return _STATUS_NO_UPDATE
    try:
        return _check_apt_upgradable(target_host)
    except Exception as e:
        print(f"  Error checking apt updates: {e}")
        return _STATUS_NO_UPDATE


def _check_apt_upgradable(target_host):
    print(f"    Checking for apt updates on {target_host}...")

    cmd = [
        'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
        target_host, 'apt list --upgradable 2>/dev/null'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

    if result.returncode != 0:
        return _STATUS_NO_UPDATE

    packages = [l for l in result.stdout.splitlines() if l and not l.startswith('Listing')]
    count = len(packages)
    return f"{count} packages" if count > 0 else _STATUS_NO_UPDATE
