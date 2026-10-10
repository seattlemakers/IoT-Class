# SYSTEM ARCHITECTURE & EXHAUSTIVE RIGOR MANIFEST
**READ THIS ENTIRE DOCUMENT BEFORE PROPOSING CHANGES.** 
Do not assume standard Debian or Ubuntu behavior. Every mechanism below has been empirically proven on the live hardware via Popperian falsification.

## 1. The Network Split (Netplan vs NetworkManager)
The Raspberry Pi OS Trixie minimal image utilizes `rpi-cloud-init-mods`. Networking operates on a strict, proven dual-layer architecture:

* **Class Wi-Fi (Immutable/Power-Yank Immune):** The RPi Imager injects credentials into the FAT32 `/boot/`. On first boot, `cloud-init` translates this into an `/etc/netplan/*.yaml` payload. On *every subsequent boot*, `netplan-generator` renders the `.nmconnection` file directly to the `/run/NetworkManager/system-connections/` RAM disk. **It is never written to the SD card.** 
* **Student Wi-Fi (Volatile/Vulnerable):** Added manually via Cockpit or `nmcli`. NetworkManager bypasses Netplan entirely and writes the new profile directly to the SD card at `/etc/NetworkManager/system-connections/`.
* **The Bridge:** To protect student profiles from delayed-write ext4 corruption during a power-yank, `provision_master.sh` deploys a dispatcher hook (`/etc/NetworkManager/dispatcher.d/99-sync-on-connect`) that executes `/bin/sync` the moment the `wlan0` interface reports `up`.

## 2. The Swap Split (zram0 vs dphys-swapfile)
The system runs two distinct swap partitions simultaneously to protect the SD card while supporting 512MB Pi 1A+ devices. Do not attempt to merge or disable them.
* **Primary Swap (`/dev/zram0`):** Compressed RAM swap. Operates at Priority 100.
* **Fallback Swap (`/var/swap`):** Physical SD card swap. Operates at Priority -2. Strictly hard-capped to 512MB via offline `sed` regex in `post-flash.sh` (`s/^#?[[:space:]]*CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/`).
* **Mechanism:** The kernel pushes all swap to RAM (`zram0`). It strictly avoids SD card writes unless RAM compression is completely exhausted. Accompanied by `vm.swappiness=10`.

## 3. Hardware Constraints & Offline Provisioning
The target Pi 1 Model A+ has a single ARMv6 core and 512MB of RAM. The Realtek `rtl8192cu` Wi-Fi adapter is highly unstable under load without `swenc=1`.
* **Rule:** Heavy configuration (modprobe changes, swap limits, fstab edits) MUST happen offline via `post-flash.sh` while the SD card is mounted on the host laptop. Applying these on the live Pi via SSH creates race conditions, kernel panics, and OOM kills.
