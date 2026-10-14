#!/usr/bin/env bash
# ==============================================================================
# Script: provision_clone.sh
# Purpose: Strips cryptographic uniqueness and assigns decoupled identities to clones
# Execution: Run on the host laptop against the mounted clone SD card
# ==============================================================================

set -euo pipefail

if [[ $# -ne 4 ]]; then
    echo "Usage: $0 <boot_mount_path> <rootfs_mount_path> <host_number> <ap_number>"
    echo "Example: $0 /media/$USER/bootfs /media/$USER/rootfs 05 1"
    exit 1
fi

BOOT_MOUNT="$1"
ROOTFS_MOUNT="$2"
HOST_ID=$(printf "%02d" "${3#0}")
AP_ID=$(printf "%d" "${4#0}")

NEW_HOSTNAME="SM-IoT-Host-${HOST_ID}"
STATION_SSID="SM-Electronics-${AP_ID}"

if [[ ! -d "$BOOT_MOUNT" || ! -d "$ROOTFS_MOUNT" ]]; then
    echo "[ERROR] Mount points do not exist. Check paths."
    exit 1
fi

echo "======================================================================"
echo "    Deploying Clone Identity: ${NEW_HOSTNAME}"
echo "    Target Network: ${STATION_SSID} (Priority: 10)"
echo "======================================================================"

# 1. Hostname Injection & Cloud-Init Payload Neutralization
echo "[1/9] Injecting Hostname (${NEW_HOSTNAME})..."
echo "$NEW_HOSTNAME" | sudo tee "${ROOTFS_MOUNT}/etc/hostname" >/dev/null
sudo sed -i -E "s/^127\.0\.1\.1[[:space:]]+.*/127.0.1.1\t${NEW_HOSTNAME}/" "${ROOTFS_MOUNT}/etc/hosts"

BOOT_USER_DATA="${BOOT_MOUNT}/user-data"
[[ ! -f "$BOOT_USER_DATA" ]] && BOOT_USER_DATA="${BOOT_MOUNT}/firmware/user-data"
if [[ -f "$BOOT_USER_DATA" ]]; then
    # Blind regex overwrite of the master's hostname to prevent resurrection
    sudo sed -i -E "s/^hostname:[[:space:]]*.*$/hostname: \"${NEW_HOSTNAME}\"/" "$BOOT_USER_DATA"
fi

# 2. Cloud-Init Instance Purge
echo "[2/9] Purging Cloud-Init instance cache..."
sudo rm -rf "${ROOTFS_MOUNT}/var/lib/cloud/"*
sudo rm -f "${ROOTFS_MOUNT}/var/log/cloud-init"*

# 3. Machine-ID & DBus Reset
echo "[3/9] Truncating Systemd Machine-IDs..."
sudo truncate -s 0 "${ROOTFS_MOUNT}/etc/machine-id"
sudo rm -f "${ROOTFS_MOUNT}/var/lib/dbus/machine-id"

# 4. SSH Host Keys & Cockpit TLS
echo "[4/9] Forging new SSH keys offline..."
sudo rm -f "${ROOTFS_MOUNT}/etc/ssh/"ssh_host_*
sudo rm -f "${ROOTFS_MOUNT}/etc/cockpit/ws-certs.d/"*
# Leverage laptop CPU to mathematically generate the clone's keys, bypassing Pi 1 entropy limits
sudo ssh-keygen -A -f "${ROOTFS_MOUNT}"

# 5. Tailscale Machine State
echo "[5/9] Stripping Tailscale node identity..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/tailscale/tailscaled.state"
sudo rm -f "${ROOTFS_MOUNT}/var/lib/tailscale/tailscaled.log.conf"

# 6. Mosquitto Retained Topics
echo "[6/9] Clearing Mosquitto retained topic database..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/mosquitto/mosquitto.db"

# 7. Node-RED & Matter Controller Runtime State
echo "[7/9] Purging Node-RED session & Matter fabric states..."
NODE_RED_DIR=$(sudo find "${ROOTFS_MOUNT}/home" -maxdepth 2 -type d -name ".node-red" | head -n 1)
if [[ -n "$NODE_RED_DIR" ]]; then
    sudo rm -f "${NODE_RED_DIR}/.config.json"
    sudo rm -f "${NODE_RED_DIR}/.config.runtime.json"
    sudo rm -f "${NODE_RED_DIR}/.sessions.json"
    sudo rm -f "${NODE_RED_DIR}/flows_cred.json"
    # The Matter node uses an isolated storage directory for fabric credentials
    sudo rm -rf "${NODE_RED_DIR}/node-red-matter"
fi

# Neutralize ARMv7 bcrypt binaries inherited from Master Pi 2
# Ensure $ROOTFS points to the mounted root partition of the SD card
echo "Scanning for architecture-dependent Node.js binaries..."

# Search global modules and local user palette (suppressing errors if paths don't exist yet)
NODE_BINS=$(find "${ROOTFS}/usr/local/lib/node_modules" "${ROOTFS}/home/admin/.node-red/node_modules" -type f -name "*.node" 2>/dev/null)

if [ -n "$NODE_BINS" ]; then
    for bin in $NODE_BINS; do
        if [[ "$bin" == *"/@node-rs/bcrypt-linux-arm-gnueabihf/"* ]]; then
            echo "[FIXED] Purging known ARMv7 bcrypt binary: ${bin#$ROOTFS}"
            rm -f "$bin"
        else
            echo "========================================================="
            echo "[FATAL ERROR] Unknown native C++ binary detected!"
            echo "File: ${bin#$ROOTFS}"
            echo "This ARMv7 binary will trigger a SIGILL crash on the Pi 1."
            echo "Halting provisioning. You must manually rebuild this module."
            echo "========================================================="
            exit 1
        fi
    done
fi

# 8. Station Wi-Fi Injection (NetworkManager priority override)
echo "[8/9] Injecting Station AP Profile for ${STATION_SSID} (Priority 10)..."
sudo rm -f "${ROOTFS_MOUNT}/etc/NetworkManager/system-connections/"*.nmconnection

NM_FILE="${ROOTFS_MOUNT}/etc/NetworkManager/system-connections/${STATION_SSID}.nmconnection"
NEW_UUID=$(uuidgen)

sudo tee "${NM_FILE}" >/dev/null <<EOF
[connection]
id=${STATION_SSID}
uuid=${NEW_UUID}
type=wifi
interface-name=wlan0
autoconnect-priority=10

[wifi]
mode=infrastructure
ssid=${STATION_SSID}

[wifi-security]
key-mgmt=wpa-psk
psk=${STATION_SSID}

[ipv4]
method=auto

[ipv6]
addr-gen-mode=default
method=auto
EOF

sudo chmod 600 "${NM_FILE}"
sudo chown root:root "${NM_FILE}"

# 9. Entropy & Access Enablement
echo "[9/9] Resetting entropy and enforcing SSH headless access..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/systemd/random-seed"
sudo rm -rf "${ROOTFS_MOUNT}/var/log/journal/"*
sudo touch "${BOOT_MOUNT}/ssh"

sync
echo "======================================================================"
echo "    Clone ${NEW_HOSTNAME} successfully stripped and staged."
echo "    Safe to unmount and eject SD card."
echo "======================================================================"
