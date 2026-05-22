# Auto-connect Pi to "EE Wi-Fi" on boot

The Pi runs NetworkManager (Raspberry Pi OS Bookworm). NetworkManager already
starts at boot via systemd and auto-connects to any saved connection profile.
So "auto-connect to WiFi on boot" is just: drop a profile file in the right
directory with the right permissions, then enable it.

The template lives at [wifi-ee.nmconnection.template](wifi-ee.nmconnection.template).
The real file with the password is **not committed** — set it up on the Pi by
hand the first time, then it persists across reboots.

## Install (run on the Pi, not from this laptop)

```bash
# 1. Copy the template to the system connections dir under the final name.
sudo cp /home/pi/smart-stick/rpi/systemd/wifi-ee.nmconnection.template \
        /etc/NetworkManager/system-connections/EE-Wi-Fi.nmconnection

# 2. Substitute the placeholder with your real WiFi password.
#    (Type the password directly — do not commit it.)
sudo sed -i "s|__PSK__|<your-real-password-here>|" \
        /etc/NetworkManager/system-connections/EE-Wi-Fi.nmconnection

# 3. NetworkManager refuses to load files that aren't owned by root with
#    mode 600. This is the most common reason "it doesn't autoconnect."
sudo chown root:root /etc/NetworkManager/system-connections/EE-Wi-Fi.nmconnection
sudo chmod 600       /etc/NetworkManager/system-connections/EE-Wi-Fi.nmconnection

# 4. Reload NM so it picks up the new profile, then activate it.
sudo nmcli connection reload
sudo nmcli connection up "EE Wi-Fi"
```

## Verify

```bash
# Should show "EE Wi-Fi" as an active wifi connection.
nmcli connection show --active

# Should show wlan0 with an IPv4 address (e.g. 192.168.x.y).
ip addr show wlan0

# Should resolve from another machine on the same network.
# Run this from your laptop, not the Pi:
ping raspberrypi.local
```

## Test that it actually comes up after a reboot

```bash
sudo reboot
# wait ~30s, then from your laptop:
ssh pi@raspberrypi.local
```

If SSH connects, autoconnect is working. If it doesn't, the most likely
causes — in order of probability:

1. File permissions wrong (must be `root:root` mode `600`, see step 3 above).
2. SSID has a typo. NM matches exactly — "EE Wi-Fi" must match the network's
   broadcast name character-for-character, including the space.
3. WiFi is out of range or the password is wrong. Check `journalctl -u NetworkManager -b`
   for "authentication failed" lines.

## Removing the network later

```bash
sudo nmcli connection delete "EE Wi-Fi"
```

This deletes the file under `/etc/NetworkManager/system-connections/` too.
