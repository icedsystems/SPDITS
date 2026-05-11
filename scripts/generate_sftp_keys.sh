#!/bin/bash
# Generate SSH host keys for the SFTP server
# Run this once before starting docker-compose

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SFTP_DIR="$SCRIPT_DIR/../docker/sftp"

echo "Generating SSH host keys for SFTP..."

if [ ! -f "$SFTP_DIR/ssh_host_rsa_key" ]; then
    ssh-keygen -t rsa -b 4096 -f "$SFTP_DIR/ssh_host_rsa_key" -N ""
    echo "✓ RSA key generated"
fi

if [ ! -f "$SFTP_DIR/ssh_host_ed25519_key" ]; then
    ssh-keygen -t ed25519 -f "$SFTP_DIR/ssh_host_ed25519_key" -N ""
    echo "✓ ED25519 key generated"
fi

chmod 600 "$SFTP_DIR/ssh_host_rsa_key" "$SFTP_DIR/ssh_host_ed25519_key"
echo "Done. SFTP host keys are ready."
