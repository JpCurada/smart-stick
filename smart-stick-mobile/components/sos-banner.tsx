/**
 * Foreground SOS banner shown on the Home tab when the cane's most recent
 * alert is type "sos". Tapping the banner opens Google Maps at the cane's
 * last known location and the in-app Location tab.
 *
 * Push notifications cover the lock-screen / backgrounded case; this
 * component covers the case where the guardian already has the app open.
 */
import { router } from 'expo-router';
import { Linking, Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Palette } from '@/constants/theme';
import type { LocationFix } from '@/lib/types';

type Props = {
  visible: boolean;
  location: LocationFix | null;
  triggeredAt?: string | null;
  onDismiss: () => void;
};

export function SosBanner({ visible, location, triggeredAt, onDismiss }: Props) {
  if (!visible) return null;

  const time = triggeredAt ? new Date(triggeredAt).toLocaleTimeString() : 'just now';
  const locationLine = location
    ? `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`
    : 'Unknown (no GPS fix yet)';

  const openMaps = () => {
    if (!location) return;
    const url = `https://maps.google.com/?q=${location.latitude.toFixed(6)},${location.longitude.toFixed(6)}`;
    Linking.openURL(url).catch((err) => console.warn('failed to open maps:', err));
  };

  const openLiveView = () => {
    router.push('/(tabs)/location');
  };

  return (
    <View style={styles.banner}>
      <ThemedText style={styles.title}>Emergency SOS</ThemedText>
      <View style={styles.row}>
        <ThemedText style={styles.label}>Time:</ThemedText>
        <ThemedText style={styles.value}>{time}</ThemedText>
      </View>
      <View style={styles.row}>
        <ThemedText style={styles.label}>Location:</ThemedText>
        <ThemedText style={styles.value}>{locationLine}</ThemedText>
      </View>

      <View style={styles.actions}>
        <Pressable
          onPress={openMaps}
          style={({ pressed }) => [
            styles.button,
            { opacity: location ? (pressed ? 0.7 : 1) : 0.4 },
          ]}
          disabled={!location}
        >
          <ThemedText style={styles.buttonText}>Open in Maps</ThemedText>
        </Pressable>
        <Pressable
          onPress={openLiveView}
          style={({ pressed }) => [styles.button, { opacity: pressed ? 0.7 : 1 }]}
        >
          <ThemedText style={styles.buttonText}>Live View</ThemedText>
        </Pressable>
      </View>

      <Pressable onPress={onDismiss} style={styles.dismiss}>
        <ThemedText style={styles.dismissText}>Acknowledge</ThemedText>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: Palette.critical,
    gap: 6,
  },
  title: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 4,
  },
  row: {
    flexDirection: 'row',
    gap: 6,
  },
  label: {
    color: '#fff',
    opacity: 0.9,
    fontWeight: '700',
  },
  value: {
    color: '#fff',
    flexShrink: 1,
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 10,
  },
  button: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.18)',
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
  },
  dismiss: {
    marginTop: 8,
    alignItems: 'center',
  },
  dismissText: {
    color: '#fff',
    opacity: 0.85,
    textDecorationLine: 'underline',
  },
});
