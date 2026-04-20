#!/Users/dang/Documents/Development/version-checker/.venv/bin/python
# PYTHON_ARGCOMPLETE_OK

import argparse
import os
import sys
from pathlib import Path

# Suppress urllib3 OpenSSL warning before importing anything that uses requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)


def _vault_path() -> Path | None:
    folder = os.environ.get("OBSIDIAN_VAULT_FOLDER", "/Users/dang/Documents/Goeppedia/Software")
    p = Path(folder)
    return p if p.is_dir() else None


def _parse_note_name_instance(md: Path) -> tuple[str, str] | None:
    import yaml
    content = md.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    end = content.find("\n---\n", 4)
    if end == -1:
        return None
    frontmatter = yaml.safe_load(content[4:end]) or {}
    name = frontmatter.get("name")
    instance = frontmatter.get("instance")
    if name and instance:
        return name, instance
    return None


def _app_completer(prefix, parsed_args, **kwargs):
    vault = _vault_path()
    if vault is None:
        return []
    names = set()
    for md in vault.glob("*.md"):
        result = _parse_note_name_instance(md)
        if result:
            names.add(result[0])
    return [n for n in sorted(names) if n.startswith(prefix)]


def _instance_completer(prefix, parsed_args, **kwargs):
    vault = _vault_path()
    if vault is None:
        return []
    app = getattr(parsed_args, "app", None)
    instances = []
    for md in vault.glob("*.md"):
        result = _parse_note_name_instance(md)
        if result:
            name, instance = result
            if app is None or name == app:
                instances.append(instance)
    return [i for i in sorted(set(instances)) if i.startswith(prefix)]


def main():
    parser = argparse.ArgumentParser(description="Goepp Homelab Version Manager")
    parser.add_argument(
        "--vault",
        default=None,
        help="Path to Obsidian Software vault folder (default: from config)",
    )
    parser.add_argument(
        "--check-all", action="store_true", help="Check all applications and exit"
    )
    parser.add_argument("--summary", action="store_true", help="Show summary and exit")
    parser.add_argument(
        "--list", action="store_true", help="List all applications and exit"
    )
    parser.add_argument(
        "--updates",
        action="store_true",
        help="List only applications with updates available and exit",
    )
    app_arg = parser.add_argument("--app", type=str, help="Check specific application by name")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help=(
            "Upgrade the application specified by --app. "
            "For version_pin='latest': triggers an AWX job directly. "
            "For version_pin='pinned': updates the k3s manifest file first, then triggers AWX."
        ),
    )
    instance_arg = parser.add_argument(
        "--instance",
        type=str,
        default="",
        help="Filter to a specific instance (use with --app)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Force AWX trigger even if already up to date or manifest unchanged. "
            "For version_pin='pinned': skips manifest update and goes straight to AWX."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making any changes (use with --app --upgrade)",
    )

    try:
        import argcomplete
        app_arg.completer = _app_completer
        instance_arg.completer = _instance_completer
        argcomplete.autocomplete(parser, exclude=["--"])
    except ImportError:
        pass

    args = parser.parse_args()

    from version_manager import VersionManager

    vm = VersionManager(args.vault)

    if not vm.notes:
        print("Failed to load vault notes. Check vault path and permissions.")
        sys.exit(1)

    if args.check_all:
        vm.check_all_applications()
    elif args.summary:
        vm.show_summary()
    elif args.list:
        vm.show_applications()
    elif args.updates:
        vm.show_updates()
    elif args.app:
        if args.upgrade:
            label = f"'{args.app}'" + (f" (instance: {args.instance})" if args.instance else "")
            if args.dry_run:
                print(f"[DRY RUN] Upgrade requested for {label}")
            else:
                print(f"Upgrade requested for {label}")
            print()
            vm.upgrade_application(args.app, dry_run=args.dry_run, instance=args.instance, force=args.force)
        else:
            matching = vm.find_application_rows_by_name(args.app, instance=args.instance)

            if not matching:
                print(f"Application '{args.app}' not found")
                print("Available applications:")
                for name in vm.get_all_application_names():
                    print(f"  {name}")
                sys.exit(1)

            for idx in matching:
                vm.check_single_application(idx)
    elif args.upgrade:
        print("--upgrade requires --app")
        parser.print_help()
        sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
