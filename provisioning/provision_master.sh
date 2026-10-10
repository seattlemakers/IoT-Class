#!/usr/bin/env bash
# ==============================================================================
# Script: provision_master.sh
# Purpose: Prepares the Golden Master image on Raspberry Pi 2 for fleet cloning
# Target Architecture: ARMv6zk compatible (runs on Pi 1 Model A+ and Pi 2)
# OS Target: Raspberry Pi OS 32-bit (Debian Trixie)
# ==============================================================================

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "[ERROR] This provisioning script must be run as root (or via sudo)."
    exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo "======================================================================"
echo "    Raspberry Pi Golden Master Provisioning (Debian Trixie / ARMv6)"
echo "    Target User: ${REAL_USER} | Home: ${REAL_HOME}"
echo "======================================================================"

echo "[1/10] Ensuring Wi-Fi stability configs are persistent..."
mkdir -p /etc/modprobe.d
cat << 'EOF' > /etc/modprobe.d/rtl8192cu.conf
options rtl8192cu swenc=1
EOF
chmod 644 /etc/modprobe.d/rtl8192cu.conf

mkdir -p /etc/NetworkManager/conf.d
cat << 'EOF' > /etc/NetworkManager/conf.d/99-wifi.conf
[main]
autoconnect-retries-default=0
auth-polkit=root-only

[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.powersave=2
EOF
chmod 644 /etc/NetworkManager/conf.d/99-wifi.conf

echo "[2/10] Updating base system and installing IoT dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get dist-upgrade -y

apt-get install -y --no-install-recommends \
    curl wget git ca-certificates gnupg htop jq xz-utils tar binutils \
    avahi-daemon avahi-utils dphys-swapfile \
    python3-paho-mqtt python3-dev python3-pip python3-venv \
    build-essential i2c-tools gpiod

systemctl enable avahi-daemon

echo "       Granting hardware bus access to ${REAL_USER}..."
usermod -aG dialout,gpio,i2c "$REAL_USER" || true

echo "[3/10] Installing Cockpit and cockpit-files via backports..."
apt-get install -y cockpit

DEB_KEYRING_URL="https://deb.debian.org/debian/pool/main/d/debian-archive-keyring/debian-archive-keyring_2025.1_all.deb"
KEYRING_TMP="/tmp/debian-keyring.deb"
if curl -sSL -o "$KEYRING_TMP" "$DEB_KEYRING_URL"; then
    dpkg -i "$KEYRING_TMP" || apt-get install -f -y
    rm -f "$KEYRING_TMP"
else
    apt-get install -y debian-archive-keyring || true
fi

cat << 'EOF' > /etc/apt/sources.list.d/debian-backports.sources
Types: deb
URIs: http://deb.debian.org/debian
Suites: trixie-backports
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

apt-get update -y
apt-get install -y -t trixie-backports cockpit-files
systemctl enable cockpit.socket
systemctl restart cockpit.socket || true

echo "[4/10] Staging ARMv6-compatible Node.js runtime..."
NODE_INSTALL_DIR="/usr/local"
INDEX_URL="https://unofficial-builds.nodejs.org/download/release/index.tab"

NODE_VER=$(curl -sL "$INDEX_URL" | awk '$1 ~ /^v20\./ && /armv6l/ { print $1; exit }')
if [[ -z "$NODE_VER" ]]; then
    NODE_VER=$(curl -sL "$INDEX_URL" | awk '/armv6l/ { print $1; exit }')
fi

if [[ -z "$NODE_VER" ]]; then
    echo "[ERROR] Could not resolve an ARMv6 Node.js binary release."
    exit 1
fi

NODE_TARBALL="node-${NODE_VER}-linux-armv6l.tar.xz"
NODE_URL="https://unofficial-builds.nodejs.org/download/release/${NODE_VER}/${NODE_TARBALL}"

curl -sSL "$NODE_URL" -o "/tmp/${NODE_TARBALL}"
tar -xJf "/tmp/${NODE_TARBALL}" -C "$NODE_INSTALL_DIR" --strip-components=1 \
    --exclude "CHANGELOG.md" --exclude "README.md" --exclude "LICENSE"
rm -f "/tmp/${NODE_TARBALL}"

echo "[5/10] Installing Node-RED and pre-compiling modules..."
npm install -g --unsafe-perm node-red

MODULE_LIST=(
    "@flowfuse/node-red-dashboard"
    "@sammachin/node-red-matter-controller"
)

stage_nodered_environment() {
    local TARGET_DIR="$1"
    local OWNER="$2"

    mkdir -p "$TARGET_DIR"
    cd "$TARGET_DIR"

    if [[ ! -f package.json ]]; then
        cat << 'EOF' > package.json
{
  "name": "workshop-node-red-workspace",
  "description": "Pre-warmed Node-RED environment for makerspace workshop",
  "version": "1.0.0",
  "private": true,
  "dependencies": {}
}
EOF
    fi

    npm install --no-audit --no-fund "${MODULE_LIST[@]}"

    if [[ -n "$OWNER" ]]; then
        chown -R "$OWNER":"$OWNER" "$TARGET_DIR"
    fi
}

stage_nodered_environment "/etc/skel/.node-red" ""
if [[ -n "$REAL_HOME" && -d "$REAL_HOME" ]]; then
    stage_nodered_environment "${REAL_HOME}/.node-red" "$REAL_USER"
fi

STARTER_FLOWS_JSON='[
  { "id": "tab_workshop", "type": "tab", "label": "Workshop Telemetry", "disabled": false },
  { "id": "mqtt_broker_local", "type": "mqtt-broker", "broker": "127.0.0.1", "port": "1883", "clientid": "", "autoConnect": true, "protocolVersion": "4", "keepalive": "60", "cleansession": true, "autoUnsubscribe": true },
  { "id": "mqtt_in_radar", "type": "mqtt in", "z": "tab_workshop", "name": "Radar Occupancy", "topic": "+/radar/#", "broker": "mqtt_broker_local", "x": 160, "y": 120, "wires": [["debug_radar_out"]] },
  { "id": "mqtt_in_plug", "type": "mqtt in", "z": "tab_workshop", "name": "S31 Plug Power", "topic": "+/plug/#", "broker": "mqtt_broker_local", "x": 160, "y": 200, "wires": [["debug_plug_out"]] },
  { "id": "debug_radar_out", "type": "debug", "z": "tab_workshop", "name": "Radar Stream", "active": true, "complete": "payload", "x": 420, "y": 120, "wires": [] },
  { "id": "debug_plug_out", "type": "debug", "z": "tab_workshop", "name": "Plug Stream", "active": true, "complete": "payload", "x": 420, "y": 200, "wires": [] }
]'

echo "$STARTER_FLOWS_JSON" > /etc/skel/.node-red/flows.json
if [[ -n "$REAL_HOME" && -d "$REAL_HOME" ]]; then
    echo "$STARTER_FLOWS_JSON" > "${REAL_HOME}/.node-red/flows.json"
    chown "$REAL_USER":"$REAL_USER" "${REAL_HOME}/.node-red/flows.json"
fi

cat << EOF > /etc/systemd/system/nodered.service
[Unit]
Description=Node-RED Graphical Flow Engine
After=network.target mosquitto.service

[Service]
Type=simple
User=${REAL_USER}
Group=${REAL_USER}
WorkingDirectory=${REAL_HOME}
Environment="NODE_OPTIONS=--max-old-space-size=256"
ExecStart=/usr/local/bin/node-red --userDir ${REAL_HOME}/.node-red
Restart=on-failure
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nodered.service

echo "[6/10] Installing Mosquitto MQTT broker..."
apt-get install -y mosquitto mosquitto-clients

cat << 'EOF' > /etc/mosquitto/conf.d/workshop.conf
listener 1883 0.0.0.0
allow_anonymous true
persistence false
EOF
chmod 644 /etc/mosquitto/conf.d/workshop.conf

systemctl enable mosquitto.service
systemctl restart mosquitto.service

echo "[7/10] Staging Blocky fast DNS proxy (ARMv6)..."
BLOCKY_API="https://api.github.com/repos/0xERR0R/blocky/releases/latest"
BLOCKY_URL=$(curl -sL "$BLOCKY_API" | jq -r '.assets[] | select(.name | test("Linux_armv6.*\\.tar\\.gz$")) | .browser_download_url' | head -n1)

if [[ -n "$BLOCKY_URL" && "$BLOCKY_URL" != "null" ]]; then
    curl -sSL "$BLOCKY_URL" -o /tmp/blocky.tar.gz
    tar -xzf /tmp/blocky.tar.gz -C /usr/local/bin/ blocky
    chmod 755 /usr/local/bin/blocky
    rm -f /tmp/blocky.tar.gz

    mkdir -p /etc/blocky
    cat << 'EOF' > /etc/blocky/config.yml
upstreams:
  groups:
    default:
      - 1.1.1.1
      - 9.9.9.9
ports:
  dns: 5335
log:
  level: info
EOF
    chmod 644 /etc/blocky/config.yml

    cat << 'EOF' > /etc/systemd/system/blocky.service
[Unit]
Description=Blocky Fast DNS Proxy
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/bin/blocky --config /etc/blocky/config.yml
Restart=always
RestartSec=5s
[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl disable blocky.service >/dev/null 2>&1 || true
fi

echo "[8/10] Installing Tailscale client..."
if curl -fsSL https://tailscale.com/install.sh | sh; then
    systemctl enable tailscaled.service
fi

echo "[9/10] Applying low-memory tuning for Raspberry Pi 1 Model A+..."
CONFIG_TXT="/boot/firmware/config.txt"
[[ ! -f "$CONFIG_TXT" ]] && CONFIG_TXT="/boot/config.txt"

if [[ -f "$CONFIG_TXT" ]]; then
    if grep -q "^gpu_mem=" "$CONFIG_TXT"; then
        sed -i 's/^gpu_mem=.*/gpu_mem=16/' "$CONFIG_TXT"
    else
        echo "gpu_mem=16" >> "$CONFIG_TXT"
    fi
fi

echo "[9.5/10] Deploying Power-Yank Sync for Student Networks..."
mkdir -p /etc/NetworkManager/dispatcher.d
cat << 'EOF' > /etc/NetworkManager/dispatcher.d/99-sync-on-connect
#!/bin/sh
if [ "$2" = "up" ]; then
    /bin/sync
fi
EOF
chmod 755 /etc/NetworkManager/dispatcher.d/99-sync-on-connect

cat << 'EOF' > /etc/sysctl.d/99-workshop-memory.conf
vm.swappiness=10
vm.vfs_cache_pressure=50
EOF
sysctl -p /etc/sysctl.d/99-workshop-memory.conf >/dev/null 2>&1 || true

echo "[10/10] Cleaning package cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "======================================================================"
echo "    Master Image Provisioning Complete"
echo "======================================================================"
