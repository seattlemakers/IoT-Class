#!/bin/bash
set -euo pipefail

# Fallbacks for strict unbound variable checking (-u)
REAL_USER="${SUDO_USER:-${USER:-root}}"
ROOTFS_MOUNT="/media/${REAL_USER}/rootfs"

if [[ ! -d "$ROOTFS_MOUNT" ]]; then
    echo "[ERROR] Mount point ${ROOTFS_MOUNT} does not exist!"
    exit 1
fi

echo "Applying offline tweaks to ${ROOTFS_MOUNT}..."

# ==========================================
# 1. REALTEK HARDWARE ARMOR
# ==========================================
sudo mkdir -p "${ROOTFS_MOUNT}/etc/modprobe.d"

# Decoupled software encryption parameters
echo "options rtl8192cu swenc=1" | sudo tee "${ROOTFS_MOUNT}/etc/modprobe.d/rtl8192cu.conf" >/dev/null
echo "options rtlwifi swenc=1" | sudo tee "${ROOTFS_MOUNT}/etc/modprobe.d/rtlwifi.conf" >/dev/null

# Disable NetworkManager Wi-Fi power saving
sudo mkdir -p "${ROOTFS_MOUNT}/etc/NetworkManager/conf.d"
cat << 'EOF' | sudo tee "${ROOTFS_MOUNT}/etc/NetworkManager/conf.d/99-wifi.conf" >/dev/null
[main]
autoconnect-retries-default=0
auth-polkit=root-only

[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.powersave=2
EOF

# ==========================================
# 2. KIOSK MEMORY & SD WEAR TUNING
# ==========================================
# SD Card Wear: Add noatime to /etc/fstab root ext4 entry
FSTAB="${ROOTFS_MOUNT}/etc/fstab"
if [[ -f "$FSTAB" ]]; then
    if ! grep -q -E "[[:space:]]/[[:space:]]+ext4[[:space:]]+.*noatime" "$FSTAB"; then
        sudo sed -i -E 's|([[:space:]]/[[:space:]]+ext4[[:space:]]+[^[:space:]]*)|&,noatime|' "$FSTAB"
    fi
fi

# Memory & Swappiness Tuning
sudo mkdir -p "${ROOTFS_MOUNT}/etc/sysctl.d"
echo "vm.swappiness=10" | sudo tee "${ROOTFS_MOUNT}/etc/sysctl.d/99-sd-wear-tuning.conf" >/dev/null

# Enforce 512MB swap. Handles missing files, uncommented lines, and spaced comments safely.
SWAP_FILE="${ROOTFS_MOUNT}/etc/dphys-swapfile"
if [[ -f "$SWAP_FILE" ]]; then
    if grep -q -E "^#?[[:space:]]*CONF_SWAPSIZE=" "$SWAP_FILE"; then
        sudo sed -i -E 's/^#?[[:space:]]*CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' "$SWAP_FILE"
    else
        echo "CONF_SWAPSIZE=512" | sudo tee -a "$SWAP_FILE" >/dev/null
    fi
fi

# Journald: Persistent on disk to save RAM, but strictly capped to save flash
sudo mkdir -p "${ROOTFS_MOUNT}/etc/systemd/journald.conf.d"
sudo mkdir -p "${ROOTFS_MOUNT}/var/log/journal"
sudo tee "${ROOTFS_MOUNT}/etc/systemd/journald.conf.d/99-persistent-journal.conf" >/dev/null << 'EOF'
[Journal]
Storage=persistent
SystemMaxUse=15M
RuntimeMaxUse=10M
EOF

# Permissions & Flush
# Safe find executions that bypass shell parsing traps and ignore empty directories
sudo find "${ROOTFS_MOUNT}/etc/modprobe.d" -name "*.conf" -type f -exec chmod 644 {} +
sudo find "${ROOTFS_MOUNT}/etc/NetworkManager/conf.d" -name "*.conf" -type f -exec chmod 644 {} +
sudo find "${ROOTFS_MOUNT}/etc/sysctl.d" -name "*.conf" -type f -exec chmod 644 {} +
sudo find "${ROOTFS_MOUNT}/etc/systemd/journald.conf.d" -name "*.conf" -type f -exec chmod 644 {} +

sync
echo "Done! The SD card is prepped for first boot."
