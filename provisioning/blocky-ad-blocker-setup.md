# Blocky DNS Proxy: Classroom Context & Home Activation Guide

## 1. Classroom Status & Architectural Context

Blocky is a lightweight, Go-based DNS proxy and ad-blocking sinkhole staged during master provisioning (`provision_master.sh`). In the classroom environment, the `blocky` service remains **inactive and disabled** by default.

### Why Blocky Is Left Inactive in Class

- **Out of scope:** While DNS is a key part of a networked set of sensors, and Blocky is based on using DNS to resolving ad servers to bogus/non-functional IP addresses, setting this service up would be somewhat of a distraction for an IoT class.
- **Memory Budget Preservation:** The Raspberry Pi 1 has 512MB of RAM (shared with the VideoCore IV GPU). With Node-RED (~130MB), Tailscale (~50MB), Cockpit (~60MB), and kernel overhead, active memory hovers around 320–350MB. Blocky caches blocklists directly in memory; loading standard ad-lists adds 40–70MB, while doable on this hardware.
- **Classroom Subnet Constraints:** The OpenWrt router isolates each station onto separate subnets (`st1`–`st6`). Students do not have administrative access to change DHCP Option 6 on the router. Testing Blocky in class would require manual per-device network adapter overrides on laptops or phones, adding friction without teaching core IoT automation logic.

## 2. DNS Sinkhole Mechanics

```
[ Client Device ] 
       │ 
       │ (1) DNS Query: "adservice.google.com" (Port 53 UDP/TCP)
       ▼
[ Blocky on Pi ] ──── (Matches Blacklist) ────► Returns 0.0.0.0 (Ad Dropped)
       │
       │ (2) DNS Query: "api.open-meteo.com"
       ▼
(No Match) ──────────► Forwards to Upstream (1.1.1.1 / 8.8.8.8) ──► Returns Public IP
```

- **DHCP Delegation:** Blocky does not route internet traffic or inspect packets. Instead, the local home router informs all connected devices via DHCP (Option 6) that the Pi is the primary DNS resolver.
- **Query Interception:** When a client looks up an address, it queries port 53 on the Pi. Blocky checks the domain against its in-memory blocklist. Matching domains resolve to `0.0.0.0` or `NXDOMAIN`, preventing ads and tracking scripts from downloading.
- **Upstream Forwarding:** Legitimate requests pass through to configured external resolvers (e.g., Cloudflare `1.1.1.1`, Google `8.8.8.8`) and are cached locally in RAM for faster subsequent lookups.
- **Known Bypass Vectors:** Devices with hardcoded DNS (such as Google Home or Chromecasts) bypass DHCP-assigned DNS unless the router actively enforces port 53 DNAT redirection. Applications using DNS-over-HTTPS (DoH) or DNS-over-TLS (DoT) will bypass local DNS entirely unless encrypted DNS is blocked at the firewall.

## 3. Home Network Activation Guide

To convert the Pi into a network-wide ad blocker at home, complete the following steps once the device is connected to the home Wi-Fi network.

### Step 1: Assign a Static DHCP Lease

Log into your home router admin interface (typically `192.168.1.1` or `192.168.0.1`):

1. Navigate to **LAN Setup** / **DHCP Server** / **Static Lease**.
2. Locate the Pi (`SM-IoT-Host-XX` or its MAC address from `ip link show wlan0`).
3. Reserve a fixed IP address (e.g., `192.168.1.50`).

### Step 2: Deploy the Blocky Configuration

In the Cockpit terminal, create or update `/etc/blocky/config.yml`:

Bash

```YAML
sudo tee /etc/blocky/config.yml > /dev/null << 'EOF'
upstreams:
  groups:
    default:
      - 1.1.1.1
      - 8.8.8.8
blocking:
  blackLists:
    ads:
      - https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
  clientGroupsBlock:
    default:
      - ads
  blockType: zeroIP
  refreshPeriod: 24h

port: 53
httpPort: 4000
log:
  level: info
  format: text
EOF
```

### Step 3: Handle Port 53 Conflicts & Start the Service

Raspberry Pi OS often runs `systemd-resolved` on port 53 (`127.0.0.53`). Check for port conflicts and start Blocky:

Bash

```
# Check if port 53 is already bound
sudo ss -tulpn | grep :53

# If systemd-resolved is using port 53, disable its stub listener:
sudo sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf
sudo systemctl restart systemd-resolved

# Enable and start Blocky
sudo systemctl enable blocky
sudo systemctl start blocky
```

### Step 4: Verify Local Resolution

Test resolution directly against the local Blocky instance before pointing the whole network at it:

Bash

```
# 1. Test standard lookup (should return public IPs)
dig @127.0.0.1 api.open-meteo.com +short

# 2. Test ad domain (should return 0.0.0.0)
dig @127.0.0.1 adservice.google.com +short
```

### Step 5: Route Home Network DNS to the Pi

1. Return to your home router admin settings.

2. Under **DHCP Server Settings**, locate **Primary DNS** (DNS Server 1).

3. Change the value from your ISP/router default to the Pi’s static IP address (e.g., `192.168.1.50`).

4. Set **Secondary DNS** (DNS Server 2) to empty (or leave it blank).

   > *Note:* If a public DNS server like `1.1.1.1` is placed in the secondary slot, operating systems will split queries across both servers, causing ads to intermittently bypass Blocky.

5. Save and reboot the router, or disconnect and reconnect client devices to force DHCP lease renewal.