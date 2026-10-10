#!/usr/bin/env bash
# ==============================================================================
# Script: provision_clone.sh
# Purpose: Strips cryptographic uniqueness and assigns station identities to clones
# Execution: Run on the host laptop against the mounted clone SD card
# ==============================================================================

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <boot_mount_path> <rootfs_mount_path> <station_number>"
    echo "Example: $0 /media/$USER/bootfs /media/$USER/rootfs 05"
    exit 1
fi

BOOT_MOUNT="$1"
ROOTFS_MOUNT="$2"
STATION_ID=$(printf "%02d" "${3#0}") # Strips leading zero if provided, formats to exactly 2 digits
NEW_HOSTNAME="station-${STATION_ID}"

if [[ ! -d "$BOOT_MOUNT" || ! -d "$ROOTFS_MOUNT" ]]; then
    echo "[ERROR] Mount points do not exist. Check paths."
    exit 1
fi

echo "======================================================================"
echo "    Deploying Clone Identity: ${NEW_HOSTNAME}"
echo "======================================================================"

# 1. Hostname Injection
echo "[1/8] Injecting Hostname (${NEW_HOSTNAME})..."
echo "$NEW_HOSTNAME" | sudo tee "${ROOTFS_MOUNT}/etc/hostname" >/dev/null
sudo sed -i -E "s/^127\.0\.1\.1[[:space:]]+.*/127.0.1.1\t${NEW_HOSTNAME}/" "${ROOTFS_MOUNT}/etc/hosts"

# 2. Cloud-Init Instance Purge (CRITICAL FOR NETPLAN)
echo "[2/8] Purging Cloud-Init instance cache..."
sudo rm -rf "${ROOTFS_MOUNT}/var/lib/cloud/"*
sudo rm -f "${ROOTFS_MOUNT}/var/log/cloud-init"*

# 3. Machine-ID & DBus Reset
echo "[3/8] Truncating Systemd Machine-IDs..."
# Truncate to 0 bytes so systemd regenerates a new UUID on boot
sudo truncate -s 0 "${ROOTFS_MOUNT}/etc/machine-id"
sudo rm -f "${ROOTFS_MOUNT}/var/lib/dbus/machine-id"

# 4. SSH Host Keys & Cockpit TLS
echo "[4/8] Stripping SSH and TLS cryptographic keys..."
sudo rm -f "${ROOTFS_MOUNT}/etc/ssh/"ssh_host_*
sudo rm -f "${ROOTFS_MOUNT}/etc/cockpit/ws-certs.d/"*

# 5. Tailscale Machine State
echo "[5/8] Stripping Tailscale node identity..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/tailscale/tailscaled.state"
sudo rm -f "${ROOTFS_MOUNT}/var/lib/tailscale/tailscaled.log.conf"

# 6. Mosquitto Retained Topics
echo "[6/8] Clearing Mosquitto retained topic database..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/mosquitto/mosquitto.db"

# 7. Node-RED & Matter Controller Runtime State
echo "[7/8] Purging Node-RED session & Matter fabric states..."
NODE_RED_DIR=$(sudo find "${ROOTFS_MOUNT}/home" -maxdepth 2 -type d -name ".node-red" | head -n 1)
if [[ -n "$NODE_RED_DIR" ]]; then
    sudo rm -f "${NODE_RED_DIR}/.config.json"
    sudo rm -f "${NODE_RED_DIR}/.config.runtime.json"
    sudo rm -f "${NODE_RED_DIR}/.sessions.json"
    sudo rm -f "${NODE_RED_DIR}/flows_cred.json"
    # The Matter node uses an isolated storage directory for fabric credentials
    sudo rm -rf "${NODE_RED_DIR}/node-red-matter"
fi

# 8. Entropy & SSH Enablement
echo "[8/8] Resetting entropy and enforcing SSH headless access..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/systemd/random-seed"
sudo rm -rf "${ROOTFS_MOUNT}/var/log/journal/"*
sudo touch "${BOOT_MOUNT}/ssh"

sync
echo "======================================================================"
echo "    Clone ${NEW_HOSTNAME} successfully stripped and staged."
echo "    Safe to unmount and eject SD card."
echo "======================================================================"
