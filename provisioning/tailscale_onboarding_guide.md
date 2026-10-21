# Tailscale Setup & Onboarding Speedrun

This guide is split into two parts: how to force a "fresh start" to simulate a brand-new user (for testing), and the exact steps a student must take to navigate the modern Tailscale onboarding UI.

---

## Part 1: Instructor Prep - Forcing a "Fresh Start"

To accurately simulate a day-zero student experience, you must completely destroy the cryptographic state on both the cloud provider side and the physical hardware side. Tailscale aggressively caches user state; if you skip this, it will bypass the onboarding maze entirely.

### 1. Destroy the Cloud State (The Account)
Delete the Tailnet associated with your test account. This wipes the database and resets your user flag to a first-time visitor.

1. Log into the Tailscale Admin Console on your laptop.
2. Navigate to **Settings > General** (or go directly to `https://login.tailscale.com/admin/settings/general`).
3. Scroll to the absolute bottom of the page.
4. Click **Delete Tailnet** and confirm. You will be immediately logged out.

### 2. Destroy the Hardware State (The Pi)
Wipe the local cryptographic identity so the daemon forgets it was ever bound to a network. Run this in the Cockpit terminal on the Pi:

```bash
sudo systemctl stop tailscaled
sudo rm -f /var/lib/tailscale/tailscaled.state
sudo systemctl start tailscaled
```

You are now ready to run the test as a brand-new user.

---

## Part 2: Student Workflow & The UI Speedrun

Tailscale's modern web interface is designed for enterprise corporate deployments. Follow these exact steps to bypass the corporate surveys and securely bind your Raspberry Pi to your phone.

### Step 1: Generate the Login Link
In your Cockpit terminal, run the following command to request a secure connection:

```bash
sudo tailscale up --reset
```
*Note: If you prefer to scan a code with your phone rather than clicking a link in the browser, type `sudo tailscale up --qr --reset` instead.*

Click the authentication URL generated in the terminal.

### Step 2: The Login
*   Choose **Sign in with Google** (or Apple/GitHub). 
*   Use your personal account.

### Step 3: The "Intent" Interrogation
Tailscale will try to determine if you are a corporate user. 
*   **Question:** "How are you planning to use Tailscale?"
*   **Action:** Select **Personal Use** / **For a hobby project** / **Just me**. 
*   *Warning:* Do not select "Work". This will drop you into a mandatory 14-day Enterprise trial and ask you to configure SSO and corporate billing.

### Step 4: The "Add Your First Device" Trap
The UI will likely prompt you to "Download Tailscale for Windows/Mac" to add your current laptop. 
*   **Action:** Ignore the download button. Look for small gray text that says **"Skip for now"** or click the **Machines** tab on the left sidebar. 
*   *Why:* Your Raspberry Pi is already waiting in the background. You just authenticated it. 

### Step 5: The Machine Approval (If Prompted)
You may see a banner stating a machine needs approval to join the network.
*   **Action:** Click **Approve**.
*   *Why:* Tailscale recently introduced "Device Approval" by default to prevent unauthorized devices from joining.

### Step 6: The Dashboard
Once you see a list of machines and your Pi (**SM-IoT-Host-XX**) is listed with a `100.x.y.z` IP address, the onboarding is complete. 

### Final Step: Remote Control
1. Download the Tailscale app on your personal phone.
2. Log in with the *exact same* account.
3. Turn off your phone's Wi-Fi.
4. Type your Pi's `100.x.y.z` IP address (with port `:1880`) into your phone's browser to control your Node-RED flows over the cellular network.