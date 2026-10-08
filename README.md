# Makerspace IoT & Embedded Systems Workshop

A hands-on, 3-hour technical curriculum for learning modern, local-first IoT architecture, Linux systems administration, and microcontroller sensor firmware on resource-constrained hardware.

Students build an autonomous edge smart home stack featuring a **Raspberry Pi 1 Model A+** edge controller, a commercial **Sonoff S31 smart plug** reflashed with ESPHome, and an **ESP32 mmWave radar sensor** publishing telemetry over MQTT into **Node-RED**.

---

## Workshop Objectives & Philosophy

1. **Local-First & Cloud-Free:** Zero dependence on proprietary cloud services (AWS IoT, Tuya, SmartThings). All messaging, logic, and telemetry stay within the local area network.
2. **Standardized Protocols Over Monoliths:** Demystify smart home ecosystems by using open standards: **MQTT** as the central event bus, **JSON** for payload interchange, and **Matter Multi-Admin** for cross-platform interoperability.
3. **Real Engineering Ownership:** Students configure Linux hostnames, create administrative users, write device YAML configurations, compile micro-controller firmware, and build browser dashboards from scratch.
4. **Hardware Reality & Resource Optimization:** Running modern IoT stacks (Debian Trixie, Cockpit, Node-RED, Mosquitto, Tailscale) on a single-core 700 MHz ARMv6 processor with 512 MB RAM teaches efficient resource budgeting and headless system management.

---

## Repository Structure

```text
├── README.md                           <- This file
├── docs/                               <- Architectural evaluations, audits, and guides
│   ├── architectural_assessment.md     <- Resource footprint and ARMv6 feasibility audit
│   ├── deduplication_audit.md          <- Machine identity & cryptographic key audit
│   ├── hardware_wiring_guide.md        <- FTDI jig, Sonoff S31, and LD2410C pinouts
│   └── matter_multi_admin_guide.md     <- Step-by-step phone-to-Node-RED Matter pairing
│
├── slides/                             <- Classroom presentation materials
│   └── workshop_slides.html            <- Self-contained HTML/CSS presentation deck
│
├── firmware/                           <- ESPHome configs and starter templates
│   ├── station-plug.yaml               <- Sonoff S31 relay & CSE7766 power monitor template
│   └── station-radar.yaml              <- ESP32 + HLK-LD2410C 24 GHz presence radar template
│
├── provisioning/                       <- Host preparation & fleet flashing tools
│   ├── prep_master_sd.sh               <- Injects rtl8192cu driver & NM stability configs
│   ├── generalize_master.sh            <- Purges machine-id, keys, and state before imaging
│   └── batch_flash.sh                  <- Parallel card writing & per-station serialization
│
├── router/                             <- Network infrastructure automation
│   └── setup_openwrt_subnets.sh        <- Configures 6 isolated SSIDs and subnets on Archer A7
│
└── staging/                            <- Zero-internet student laptop deployment
    ├── setup_station.bat               <- 1-click batch launcher for student laptops
    └── README_DRIVE_STAGING.md         <- Instructions for packaging wheels & PlatformIO cache
```

---

## Hardware Architecture

```text
                     [ OpenWrt Archer A7 Router ]
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
[ Station 01 Subnet ]        [ Station 02 Subnet ]        [ Station 03..06 ]
  SSID: SM-Electronics-01      SSID: SM-Electronics-02      Isolated Subnets
  192.168.11.0/24              192.168.12.0/24              192.168.13-16.0/24
      │                            │
      ├─► Pi 1 Model A+ (11.10)     ├─► Pi 1 Model A+ (12.10)
      ├─► S31 Smart Plug            ├─► S31 Smart Plug
      ├─► ESP32 Radar Sensor        ├─► ESP32 Radar Sensor
      └─► Student Windows Laptop   └─► Student Windows Laptop
```

### Station Bill of Materials (BOM)
* **Station Edge Server:** Raspberry Pi 1 Model A+ (700 MHz ARM11, 512 MB RAM) with an RTL8192CU-based USB Wi-Fi dongle and 16 GB MicroSD card.
* **Commercial Appliance:** Sonoff S31 120V Smart Plug (ESP8266 + CSE7766 energy monitoring IC).
* **Sensor Node:** ESP32 DevKit v1 + Hi-Link HLK-LD2410C 24 GHz mmWave human presence radar on a mini breadboard.
* **Programming Jig:** 3.3V FTDI / USB-to-UART bridge adapter with DuPont test leads or pogo-pin clip.
* **Network Infrastructure:** TP-Link Archer A7 running OpenWrt, hosting 6 isolated Wi-Fi SSIDs (`SM-Electronics-01` through `06`).

---

## Core Scripts & Tooling

### 1. Master Image Staging & Wi-Fi Stability
* **`provisioning/prep_master_sd.sh`**  
  Must be executed on the freshly flashed golden master SD card before its initial boot. It resolves known driver dropouts on the Realtek `rtl8192cu` chipset and prevents NetworkManager from abandoning reconnect loops:
  * Sets `options rtl8192cu swenc=1` in `/etc/modprobe.d/rtl8192cu.conf` to force software encryption.
  * Disables Wi-Fi power saving (`wifi.powersave=2`) and enables infinite connection retries (`connection.autoconnect-retries=0`) in `/etc/NetworkManager/conf.d/99-wifi.conf`.

### 2. Golden Master De-duplication
* **`provisioning/generalize_master.sh`**  
  Run on the Raspberry Pi 2 master unit prior to shutting down and capturing the disk image. Scrubs 9 critical state files:
  * Machine ID (`/etc/machine-id`, DBus ID) to eliminate DHCP lease collisions.
  * SSH host keys (`/etc/ssh/ssh_host_*`) so each board generates unique keys on first boot.
  * Cockpit self-signed TLS certificates (`/etc/cockpit/ws-certs.d/`).
  * Tailscale machine authorization state (`/var/lib/tailscale/*`).
  * Mosquitto retained topic database (`/var/lib/mosquitto/mosquitto.db`).
  * Node-RED runtime identity and Matter controller fabric storage keys.
  * Systemd entropy random seeds and log journals.

### 3. Linux Host Batch Provisioning
* **`provisioning/batch_flash.sh`**  
  Run on an instructor Linux laptop connected to a multi-port USB SD card reader. Writes the compressed golden image (`.img.gz`) across up to 4 cards concurrently, mounts their FAT and ext4 partitions, and directly injects:
  * Station-specific hostname (`station-01` through `station-06`).
  * Station default user account and SHA-512 hashed password (`station01`).
  * Station Wi-Fi connection profile with dedicated SSID binding (`SM-Electronics-0X`).
  * SSH enablement token (`/boot/firmware/ssh`).

### 4. Router Subnet & Isolation Setup
* **`router/setup_openwrt_subnets.sh`**  
  Pushed to the OpenWrt router via SSH. Uses UCI commands to spin up 6 virtual wireless interfaces on `radio0`, 6 distinct static subnets (`192.168.11.1/24` through `192.168.16.1/24`), 6 DHCP pools, and isolated firewall rules that permit outbound internet traffic while blocking cross-station packet sniffing and mDNS bleed.

### 5. Offline Student Laptop Staging
* **`staging/setup_station.bat`**  
  A 1-click batch script hosted on the makerspace Google Drive. Allows any Windows laptop in the space to be configured in under 90 seconds without downloading gigabytes over classroom Wi-Fi:
  * Installs ESPHome from a local wheelhouse (`--no-index --find-links=wheels`).
  * Extracts pre-warmed PlatformIO toolchain and cross-compilers (`platformio_cache.tar.gz`) directly into `%USERPROFILE%\.platformio`.
  * Stages commented starter YAML files in `C:\Workshop\ESPHome\`.
  * Creates a desktop launcher and opens the browser-based ESPHome Dashboard at `http://localhost:6052`.

---

## 3-Hour Workshop Execution Flow

| Segment | Window | Lab Focus | Operational Details |
| :--- | :--- | :--- | :--- |
| **Module 0** | 00:00 – 00:25 | **Curriculum Kickoff & Foundations** | Smart home landscape, Wi-Fi vs. Mesh vs. Matter, MQTT pub/sub fundamentals, and architectural walkthrough of the Pi Imager options wizard via slides. |
| **Lab 1** | 00:25 – 00:50 | **Linux Systems Admin via Cockpit** | Students connect to `https://192.168.1X.10:9090`. They set custom hostnames (`hostnamectl`), create their personal sudo user account, and pre-seed their home Wi-Fi credentials into NetworkManager. |
| **Pipeline Shift** | 00:50 – 00:55 | **Background Software Launch** | One command launched in Cockpit terminal: starts Mosquitto, stages Node-RED starter flows, and enables background systemd units while leaving CPU free for students. |
| **Lab 2A** | 00:55 – 01:25 | **Sonoff S31 Teardown & Flashing** | Physical disassembly, FTDI 3.3V jumpering, GPIO0 bootloader grounding, hands-on YAML configuration, and local compile/flash via Chrome Web Serial. |
| **Lab 2B** | 01:25 – 01:50 | **ESP32 + mmWave Radar Assembly** | Breadboard wiring (UART pins, power rails), hands-on sensor YAML customization, flashing over USB-C, and real-time serial presence stream verification. |
| **Lab 3** | 01:50 – 02:25 | **Node-RED Visual Automation** | Connecting to `http://station-XX.local:1880`. Wire incoming MQTT presence payloads into S31 relay switching logic and build dashboard power gauges. |
| **Demo** | 02:25 – 02:45 | **Matter Multi-Admin Live Demo** | Instructor pairs a commercial Matter-over-Wi-Fi plug to a smartphone over BLE, generates a 11-digit Multi-Admin sharing code, and pairs it into Node-RED for dual local control. |
| **Checkout** | 02:45 – 03:00 | **Take-Home Verification** | Testing mDNS `.local` host resolution and autonomous Wi-Fi fallback before boxing up hardware kits. |

---

## Safety & Operational Guidelines

* **Sonoff S31 High-Voltage Safety:**  
  The internal logic ground of the Sonoff S31 floats at AC mains potential when plugged into a wall. **THE S31 MUST NEVER BE PLUGGED INTO A WALL OUTLET WHILE CONNECTED TO A LAPTOP OR FTDI PROGRAMMER.** Power during flashing is supplied exclusively by the FTDI adapter's isolated 3.3V rail.
* **FTDI Voltage Jumper:**  
  Always confirm the FTDI adapter jumper is set to **3.3V**. Applying 5V directly to the S31 programming header will permanently destroy the ESP8266 SoC.
* **Compilation Offloading:**  
  Do not attempt to compile C++ binaries or run `npm install` directly on the Raspberry Pi 1. Doing so triggers kernel Out-Of-Memory (OOM) faults. All firmware compilation occurs on student laptops; all package dependencies are pre-baked into the golden master image.

---

## License & Attribution

Developed for makerspace electronics and IoT education. All shell scripts, batch routines, and configuration files are released under the MIT License.