/**
 * Tab 2: LOCATION — real-time GPS map.
 *
 * Polls /api/location every 5 s. The map view is rendered with
 * react-native-maps when available; until that native module is installed,
 * we display the coordinates and accuracy textually so the app still works
 * inside Expo Go for development.
 */
import * as Linking from 'expo-linking';
import { MapPin } from 'lucide-react-native';
import { useCallback } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { InfoRow } from '@/components/info-row';
import { StatusBadge } from '@/components/status-badge';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

export default function LocationScreen() {
  const location = usePoll(useCallback(() => api.location(), []), POLL_INTERVALS.location);
  const online = location.error == null && location.data != null;

  const openInMaps = () => {
    if (!location.data) return;
    const { latitude, longitude } = location.data;
    const url = `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
    void Linking.openURL(url);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={location.loading} onRefresh={location.refetch} />
        }
      >
        <View style={styles.header}>
          <ThemedText type="title">Location</ThemedText>
          <StatusBadge online={online} label={online ? 'Live' : 'No fix'} />
        </View>

        {/* Map placeholder — swap for <MapView /> once react-native-maps is wired. */}
        <ThemedView style={styles.mapPlaceholder}>
          {location.data ? (
            <View style={styles.mapCoordRow}>
              <MapPin size={20} color={Palette.primary} />
              <ThemedText style={styles.mapPlaceholderText}>
                {`${location.data.latitude.toFixed(5)}, ${location.data.longitude.toFixed(5)}`}
              </ThemedText>
            </View>
          ) : (
            <ThemedText style={styles.mapPlaceholderText}>Waiting for first GPS fix…</ThemedText>
          )}
          {location.data && (
            <Pressable onPress={openInMaps} style={styles.openMapsBtn}>
              <ThemedText style={styles.openMapsLabel}>Open in Google Maps</ThemedText>
            </Pressable>
          )}
        </ThemedView>

        <ThemedView style={styles.card}>
          <ThemedText type="subtitle">Details</ThemedText>
          <InfoRow
            label="Latitude"
            value={location.data ? location.data.latitude.toFixed(6) : '—'}
          />
          <InfoRow
            label="Longitude"
            value={location.data ? location.data.longitude.toFixed(6) : '—'}
          />
          <InfoRow
            label="Altitude"
            value={
              location.data?.altitude != null ? `${location.data.altitude.toFixed(1)} m` : '—'
            }
          />
          <InfoRow
            label="Accuracy"
            value={
              location.data?.accuracy_m != null ? `±${location.data.accuracy_m.toFixed(0)} m` : '—'
            }
          />
          <InfoRow
            label="Updated"
            value={
              location.data?.timestamp
                ? new Date(location.data.timestamp).toLocaleTimeString()
                : '—'
            }
          />
        </ThemedView>

        {!online && (
          <ThemedText style={styles.errorBanner}>
            No GPS fix yet. The stick needs a clear view of the sky outdoors.
          </ThemedText>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  content: { padding: 16, gap: 16 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  mapPlaceholder: {
    height: 280,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  mapCoordRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  mapPlaceholderText: {
    fontSize: 18,
    fontWeight: '600',
  },
  openMapsBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: Palette.primary,
    borderRadius: 8,
  },
  openMapsLabel: {
    color: '#fff',
    fontWeight: '600',
  },
  card: {
    padding: 16,
    borderRadius: 12,
    gap: 4,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  errorBanner: {
    color: '#dc2626',
    textAlign: 'center',
  },
});
