#!/usr/bin/env python3
"""
Generate encryption key for database dump encryption.

Usage:
    python3 scripts/generate_encryption_key.py [--format {raw,base64,bash,env}]

This script generates a cryptographically secure 32-byte encryption key
suitable for AES-256 encryption using Fernet.

Output Formats:
    raw      - Raw 32 bytes (binary, not useful for configuration)
    base64   - Base64-encoded string (default, use in DUMP_ENCRYPTION_KEY)
    bash     - Bash export statement (copy-paste into shell)
    env      - .env file format (append to .env file)
"""

import os
import sys
import base64
import argparse


def generate_key() -> bytes:
    """
    Generate a cryptographically secure 32-byte key.

    Returns:
        32 bytes of random data
    """
    return os.urandom(32)


def format_key_base64(key: bytes) -> str:
    """Format key as base64 string."""
    return base64.b64encode(key).decode('utf-8')


def format_key_bash(key: bytes) -> str:
    """Format as bash export statement."""
    b64 = format_key_base64(key)
    return f'export DUMP_ENCRYPTION_KEY="{b64}"'


def format_key_env(key: bytes) -> str:
    """Format as .env file entry."""
    b64 = format_key_base64(key)
    return f'DUMP_ENCRYPTION_KEY={b64}'


def format_key_raw(key: bytes) -> str:
    """Format as raw hex string (informational only)."""
    return key.hex()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate encryption key for Basset Hound database dumps"
    )
    parser.add_argument(
        '--format',
        choices=['raw', 'base64', 'bash', 'env'],
        default='base64',
        help='Output format (default: base64)'
    )
    parser.add_argument(
        '--copy-to-clipboard',
        action='store_true',
        help='Copy output to clipboard (requires xclip or pbcopy)'
    )
    parser.add_argument(
        '--append-to-env',
        metavar='FILE',
        help='Append key to .env file (with backup)'
    )

    args = parser.parse_args()

    # Generate key
    key = generate_key()

    # Format key
    formatters = {
        'raw': format_key_raw,
        'base64': format_key_base64,
        'bash': format_key_bash,
        'env': format_key_env,
    }

    formatter = formatters.get(args.format)
    if not formatter:
        print(f"Unknown format: {args.format}", file=sys.stderr)
        sys.exit(1)

    output = formatter(key)

    # Display output
    print(output)

    # Copy to clipboard if requested
    if args.copy_to_clipboard:
        try:
            # Try xclip first (Linux)
            import subprocess
            proc = subprocess.Popen(['xclip', '-selection', 'clipboard'],
                                    stdin=subprocess.PIPE)
            proc.communicate(input=output.encode('utf-8'))
            print("\n✓ Copied to clipboard", file=sys.stderr)
        except FileNotFoundError:
            try:
                # Try pbcopy (macOS)
                import subprocess
                proc = subprocess.Popen(['pbcopy'],
                                        stdin=subprocess.PIPE)
                proc.communicate(input=output.encode('utf-8'))
                print("\n✓ Copied to clipboard", file=sys.stderr)
            except FileNotFoundError:
                print("\n⚠ Clipboard copy failed: xclip or pbcopy not found",
                      file=sys.stderr)
                sys.exit(1)

    # Append to .env file if requested
    if args.append_to_env:
        import shutil
        env_file = args.append_to_env

        # Create backup
        if os.path.exists(env_file):
            backup_file = f"{env_file}.backup.{os.urandom(4).hex()}"
            shutil.copy2(env_file, backup_file)
            print(f"✓ Created backup: {backup_file}", file=sys.stderr)

        # Append to file
        with open(env_file, 'a') as f:
            f.write(f"\n# Generated encryption key for database dump export\n")
            f.write(format_key_env(key))
            f.write("\n")

        print(f"✓ Appended to {env_file}", file=sys.stderr)

    # Security warnings
    print("\n" + "=" * 70, file=sys.stderr)
    print("SECURITY WARNINGS:", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print("1. Keep this key SECRET. Do not commit to version control.", file=sys.stderr)
    print("2. Store in secure location (Vault, Secrets Manager, HSM).", file=sys.stderr)
    print("3. Use environment variables or Kubernetes Secrets for deployment.", file=sys.stderr)
    print("4. Rotate key periodically (backup old keys for decrypting old dumps).", file=sys.stderr)
    print("5. Different keys can be used per environment (dev, staging, prod).", file=sys.stderr)
    print("=" * 70, file=sys.stderr)


if __name__ == '__main__':
    main()
