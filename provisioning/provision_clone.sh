#!/usr/bin/env bash
# ==============================================================================
# Script: provision_clone.sh
# Purpose: Strips cryptographic uniqueness and assigns decoupled identities to clones
# Execution: Run on the host laptop against the mounted clone SD card
# ==============================================================================

set -euo pipefail

if [[ $# -ne 4 && $# -ne 6 ]]; then
    echo "Usage: $0 <boot_mount_path> <rootfs_mount_path> <host_number> <ap_number> [extra_ssid] [extra_psk]"
    echo "Example: $0 /media/$USER/bootfs /media/$USER/rootfs 05 1"
    echo "Example: $0 /media/$USER/bootfs /media/$USER/rootfs 05 1 'The Cyber' 'MyPassword'"
    exit 1
fi

BOOT_MOUNT="$1"
ROOTFS_MOUNT="$2"
HOST_ID=$(printf "%02d" "$((10#$3))")
AP_ID=$(printf "%d" "$((10#$4))")
EXTRA_SSID="${5:-}"
EXTRA_PSK="${6:-}"

NEW_HOSTNAME="SM-IoT-Host-${HOST_ID}"
STATION_SSID="SM-Electronics-${AP_ID}"

if [[ ! -d "$BOOT_MOUNT" || ! -d "$ROOTFS_MOUNT" ]]; then
    echo "[ERROR] Mount points do not exist. Check paths."
    exit 1
fi

echo "======================================================================"
echo "    Deploying Clone Identity: ${NEW_HOSTNAME}"
echo "    Target Network: ${STATION_SSID} (Priority: 10)"
[[ -n "$EXTRA_SSID" ]] && echo "    Secondary Network: ${EXTRA_SSID} (Priority: 5)"
echo "======================================================================"

# 1. Hostname Injection & Cloud-Init Payload Neutralization
echo "[1/10] Injecting Hostname (${NEW_HOSTNAME})..."
echo "$NEW_HOSTNAME" | sudo tee "${ROOTFS_MOUNT}/etc/hostname" >/dev/null
sudo sed -i -E "s/^127\.0\.1\.1[[:space:]]+.*/127.0.1.1\t${NEW_HOSTNAME}/" "${ROOTFS_MOUNT}/etc/hosts"

BOOT_USER_DATA="${BOOT_MOUNT}/user-data"
[[ ! -f "$BOOT_USER_DATA" ]] && BOOT_USER_DATA="${BOOT_MOUNT}/firmware/user-data"
if [[ -f "$BOOT_USER_DATA" ]]; then
    sudo sed -i -E "s/^hostname:[[:space:]]*.*$/hostname: \"${NEW_HOSTNAME}\"/" "$BOOT_USER_DATA"
fi

# 2. Cloud-Init Instance Purge
echo "[2/10] Purging Cloud-Init instance cache..."
sudo rm -rf "${ROOTFS_MOUNT}/var/lib/cloud/"*
sudo rm -f "${ROOTFS_MOUNT}/var/log/cloud-init"*

# 3. Machine-ID & DBus Reset
echo "[3/10] Truncating Systemd Machine-IDs..."
sudo truncate -s 0 "${ROOTFS_MOUNT}/etc/machine-id"
sudo rm -f "${ROOTFS_MOUNT}/var/lib/dbus/machine-id"

# 4. SSH Host Keys & Cockpit TLS
echo "[4/10] Forging new SSH keys offline..."
sudo rm -f "${ROOTFS_MOUNT}/etc/ssh/"ssh_host_*
sudo rm -f "${ROOTFS_MOUNT}/etc/cockpit/ws-certs.d/"*
sudo ssh-keygen -A -f "${ROOTFS_MOUNT}"

# 5. Tailscale Machine State
echo "[5/10] Stripping Tailscale node identity..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/tailscale/tailscaled.state"
sudo rm -f "${ROOTFS_MOUNT}/var/lib/tailscale/tailscaled.log.conf"

# 6. Mosquitto Retained Topics
echo "[6/10] Clearing Mosquitto retained topic database..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/mosquitto/mosquitto.db"

# 7. Node-RED & Matter Controller Runtime State
echo "[7/10] Purging Node-RED session & Matter fabric states..."
NODE_RED_DIR=$(sudo find "${ROOTFS_MOUNT}/home" -maxdepth 2 -type d -name ".node-red" 2>/dev/null | head -n 1 || true)
if [[ -n "$NODE_RED_DIR" ]]; then
    sudo rm -f "${NODE_RED_DIR}/.config.json"
    sudo rm -f "${NODE_RED_DIR}/.config.runtime.json"
    sudo rm -f "${NODE_RED_DIR}/.sessions.json"
    sudo rm -f "${NODE_RED_DIR}/flows_cred.json"
    sudo rm -rf "${NODE_RED_DIR}/node-red-matter"
fi

echo "Scanning for architecture-dependent Node.js binaries..."
SEARCH_PATHS=("${ROOTFS_MOUNT}/usr/local/lib/node_modules" "${ROOTFS_MOUNT}/etc/skel/.node-red/node_modules")
[[ -n "$NODE_RED_DIR" ]] && SEARCH_PATHS+=("${NODE_RED_DIR}/node_modules")

while IFS= read -r -d '' bin; do
    if [[ "$bin" == *"/@node-rs/bcrypt-linux-arm-gnueabihf/"* ]]; then
        echo "[FIXED] Purging known ARMv7 bcrypt binary: ${bin#"$ROOTFS_MOUNT"}"
        sudo rm -f "$bin"
    else
        echo "========================================================="
        echo "[FATAL ERROR] Unknown native C++ binary detected!"
        echo "File: ${bin#"$ROOTFS_MOUNT"}"
        echo "This ARMv7 binary will trigger a SIGILL crash on the Pi 1."
        echo "Halting provisioning. You must manually rebuild this module."
        echo "========================================================="
        exit 1
    fi
done < <(sudo find "${SEARCH_PATHS[@]}" -type f -name "*.node" -print0 2>/dev/null || true)

# 8. Station Wi-Fi Injection (Interface-agnostic NetworkManager profiles)
echo "[8/10] Injecting Station AP Profile for ${STATION_SSID} (Priority 10)..."
sudo mkdir -p "${ROOTFS_MOUNT}/etc/NetworkManager/system-connections"
sudo rm -f "${ROOTFS_MOUNT}/etc/NetworkManager/system-connections/SM-Electronics-"*.nmconnection

NM_FILE="${ROOTFS_MOUNT}/etc/NetworkManager/system-connections/${STATION_SSID}.nmconnection"
NEW_UUID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)

sudo tee "${NM_FILE}" >/dev/null <<EOF
[connection]
id=${STATION_SSID}
uuid=${NEW_UUID}
type=wifi
autoconnect=true
autoconnect-priority=10
autoconnect-retries=0

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

if [[ -n "$EXTRA_SSID" ]]; then
    EXTRA_FILE="${ROOTFS_MOUNT}/etc/NetworkManager/system-connections/${EXTRA_SSID}.nmconnection"
    EXTRA_UUID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
    sudo tee "${EXTRA_FILE}" >/dev/null <<EOF
[connection]
id=${EXTRA_SSID}
uuid=${EXTRA_UUID}
type=wifi
autoconnect=true
autoconnect-priority=5
autoconnect-retries=0

[wifi]
mode=infrastructure
ssid=${EXTRA_SSID}

[wifi-security]
key-mgmt=wpa-psk
psk=${EXTRA_PSK}

[ipv4]
method=auto

[ipv6]
addr-gen-mode=default
method=auto
EOF
    sudo chmod 600 "${EXTRA_FILE}"
    sudo chown root:root "${EXTRA_FILE}"
fi

# 9. Wi-Fi Keep-Alive & Dynamic Interface Rescan Service
echo "[9/10] Deploying Wi-Fi config and carrier-gated rescan service..."
sudo mkdir -p "${ROOTFS_MOUNT}/etc/NetworkManager/conf.d"
sudo tee "${ROOTFS_MOUNT}/etc/NetworkManager/conf.d/99-wifi.conf" >/dev/null <<'EOF'
[main]
autoconnect-retries-default=0

[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.powersave=2
EOF
sudo chmod 644 "${ROOTFS_MOUNT}/etc/NetworkManager/conf.d/99-wifi.conf"

sudo mkdir -p "${ROOTFS_MOUNT}/usr/local/bin"
sudo tee "${ROOTFS_MOUNT}/usr/local/bin/wifi-infinite-rescan.sh" >/dev/null <<'EOF'
#!/usr/bin/env bash
while true; do
    for dev in /sys/class/net/*; do
        [[ -d "$dev/phy80211" || -d "$dev/wireless" ]] || continue
        IFACE="${dev##*/}"

        CARRIER=0
        read -r CARRIER < "$dev/carrier" 2>/dev/null || CARRIER=0

        if [[ "$CARRIER" != "1" ]]; then
            STATE=$(nmcli -g GENERAL.STATE dev show "$IFACE" 2>/dev/null || true)
            if [[ "$STATE" == "30 (disconnected)" ]]; then
                nmcli dev wifi rescan ifname "$IFACE" >/dev/null 2>&1 || true
            fi
        fi
    done
    sleep 10
done
EOF
sudo chmod 755 "${ROOTFS_MOUNT}/usr/local/bin/wifi-infinite-rescan.sh"

sudo mkdir -p "${ROOTFS_MOUNT}/etc/systemd/system/multi-user.target.wants"
sudo tee "${ROOTFS_MOUNT}/etc/systemd/system/wifi-infinite-rescan.service" >/dev/null <<'EOF'
[Unit]
Description=Carrier-Gated Infinite Wi-Fi Rescan Loop
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
ExecStart=/usr/local/bin/wifi-infinite-rescan.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo chmod 644 "${ROOTFS_MOUNT}/etc/systemd/system/wifi-infinite-rescan.service"
sudo ln -sf /etc/systemd/system/wifi-infinite-rescan.service \
    "${ROOTFS_MOUNT}/etc/systemd/system/multi-user.target.wants/wifi-infinite-rescan.service"

# 10. Entropy & Access Enablement
echo "[10/10] Resetting entropy and enforcing SSH headless access..."
sudo rm -f "${ROOTFS_MOUNT}/var/lib/systemd/random-seed"
sudo rm -rf "${ROOTFS_MOUNT}/var/log/journal/"*
sudo touch "${BOOT_MOUNT}/ssh"

sync
echo "======================================================================"
echo "    Clone ${NEW_HOSTNAME} successfully stripped and staged."
echo "    Safe to unmount and eject SD card."
echo "======================================================================"

