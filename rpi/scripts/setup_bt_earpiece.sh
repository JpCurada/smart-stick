#!/usr/bin/env bash
#
# Smart Stick — Bluetooth earpiece setup helper.
#
# Usage:
#   ./setup_bt_earpiece.sh              # interactive pairing + set default sink
#   ./setup_bt_earpiece.sh diagnose     # read-only checks, no changes
#   ./setup_bt_earpiece.sh connect MAC  # reconnect a previously paired device
#   ./setup_bt_earpiece.sh test         # play a TTS test through the current sink
#
# Run as the same user that runs the FastAPI backend (PulseAudio is per-user).

set -euo pipefail

log()  { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

require_user_session() {
  if [[ "$(whoami)" == "root" ]]; then
    die "Do not run as root. Run as the user that runs the API (PulseAudio is per-user)."
  fi
}

diagnose() {
  log "Current user"
  whoami

  log "ALSA cards (aplay -l)"
  aplay -l 2>&1 | head -30 || true

  log "espeak / espeak-ng binaries"
  command -v espeak    && espeak --version 2>&1 | head -1 || warn "espeak not installed"
  command -v espeak-ng && espeak-ng --version 2>&1 | head -1 || warn "espeak-ng not installed"

  log "PulseAudio status"
  if ! command -v pactl >/dev/null; then
    warn "pactl not installed"
  else
    pactl info 2>&1 | head -10 || true
    log "PulseAudio sinks"
    pactl list short sinks 2>&1 || true
    log "Default sink"
    pactl get-default-sink 2>&1 || true
  fi

  log "bluetoothd"
  systemctl is-active bluetooth 2>&1 || warn "bluetooth.service not active"

  log "Paired devices"
  bluetoothctl devices Paired 2>&1 || bluetoothctl paired-devices 2>&1 || true

  log "Connected devices"
  bluetoothctl devices Connected 2>&1 || true
}

install_packages() {
  log "Installing audio + BT packages (requires sudo)"
  sudo apt update
  sudo apt install -y \
    espeak espeak-ng alsa-utils \
    pulseaudio pulseaudio-module-bluetooth \
    bluez bluez-tools

  log "Adding $USER to bluetooth/audio/pulse-access groups"
  sudo usermod -aG bluetooth,audio,pulse-access "$USER"

  log "Enabling per-user PulseAudio"
  systemctl --user enable --now pulseaudio.service pulseaudio.socket 2>/dev/null || \
    warn "Could not enable per-user pulseaudio (may already be running). Continuing."

  warn "If groups were newly added, log out and back in (or reboot) before continuing."
}

pair_interactive() {
  log "Make sure your earpiece is in PAIRING mode (usually hold the power button until it flashes blue/red)."
  read -r -p "Press ENTER when the earpiece is in pairing mode..." _

  log "Scanning for 20 seconds..."
  # Run scan in background so we can grep results without an interactive prompt
  bluetoothctl --timeout 20 scan on > /tmp/bt_scan.log 2>&1 || true

  log "Discovered devices"
  bluetoothctl devices | tee /tmp/bt_devices.log
  echo
  read -r -p "Enter the MAC address of your earpiece (XX:XX:XX:XX:XX:XX): " MAC
  if [[ ! "$MAC" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
    die "That doesn't look like a MAC address."
  fi

  log "Pairing $MAC"
  bluetoothctl --timeout 30 <<EOF
power on
agent on
default-agent
pair $MAC
trust $MAC
connect $MAC
EOF

  sleep 2
  if ! bluetoothctl info "$MAC" | grep -q "Connected: yes"; then
    die "Pairing finished but device is not connected. Check earpiece battery and try again."
  fi

  log "Paired and connected: $MAC"
  echo "$MAC" > "$HOME/.smartstick-bt-mac"
  log "Saved MAC to ~/.smartstick-bt-mac"

  set_default_sink "$MAC"
}

set_default_sink() {
  local mac="$1"
  # PulseAudio sink naming: bluez_sink.XX_XX_XX_XX_XX_XX.a2dp_sink
  local sink_id
  sink_id="bluez_sink.${mac//:/_}.a2dp_sink"

  log "Waiting for PulseAudio to register the BT sink..."
  for i in {1..10}; do
    if pactl list short sinks | grep -q "$sink_id"; then
      break
    fi
    sleep 1
  done

  if ! pactl list short sinks | grep -q "$sink_id"; then
    warn "Sink $sink_id not visible. Available sinks:"
    pactl list short sinks
    warn "Try: pactl set-default-sink <name-from-the-list-above>"
    return 1
  fi

  pactl set-default-sink "$sink_id"
  log "Default sink set to $sink_id"
}

reconnect() {
  local mac="${1:-}"
  if [[ -z "$mac" ]]; then
    [[ -f "$HOME/.smartstick-bt-mac" ]] || die "No MAC given and ~/.smartstick-bt-mac not found."
    mac="$(cat "$HOME/.smartstick-bt-mac")"
  fi
  log "Reconnecting $mac"
  bluetoothctl connect "$mac"
  sleep 2
  set_default_sink "$mac"
}

test_audio() {
  log "Default sink"
  pactl get-default-sink

  log "Speaking test message through pyttsx3 backend (espeak)"
  if command -v espeak-ng >/dev/null; then
    espeak-ng "Bluetooth earpiece audio test. If you hear this, routing works."
  elif command -v espeak >/dev/null; then
    espeak "Bluetooth earpiece audio test. If you hear this, routing works."
  else
    die "Neither espeak nor espeak-ng is installed."
  fi
}

main() {
  local cmd="${1:-pair}"
  case "$cmd" in
    diagnose)  diagnose ;;
    install)   install_packages ;;
    pair)
      require_user_session
      pair_interactive
      test_audio
      ;;
    connect)   require_user_session; reconnect "${2:-}" ;;
    test)      require_user_session; test_audio ;;
    *)         die "Unknown command: $cmd (use: diagnose | install | pair | connect [MAC] | test)" ;;
  esac
}

main "$@"
