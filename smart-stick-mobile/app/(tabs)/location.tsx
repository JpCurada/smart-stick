/**
 * Tab 2: LOCATION — real-time GPS map.
 *
 * Polls /api/location every 5 s and renders an OpenStreetMap view via
 * Leaflet inside a WebView (works in Expo Go, no native build needed).
 */
import * as Linking from 'expo-linking';
import { useCallback } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { InfoRow } from '@/components/info-row';
import { LeafletMap } from '@/components/leaflet-map';
import { StatusBadge } from '@/components/status-badge';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { useEffectiveLocation } from '@/hooks/use-effective-location';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

export default function LocationScreen() {
  const location = usePoll(useCallback(() => api.location(), []), POLL_INTERVALS.location);
  const effective = useEffectiveLocation(location.data);
  const lat = effective.latitude;
  const lon = effective.longitude;
  const hasFix = lat != null && lon != null;
  // "Online" means a live stick fix. A phone fallback is still useful, but it's
  // the caregiver's position, not the stick's — so it isn't "Live".
  const online = location.error == null && effective.source === 'stick';
  const onPhone = effective.source === 'phone';

  const openInMaps = () => {
    if (!hasFix) return;
    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
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
          <StatusBadge online={online} label={online ? 'Live' : onPhone ? 'Phone' : 'No fix'} />
        </View>

        {hasFix ? (
          <View style={styles.mapWrap}>
            {onPhone && (
              <ThemedText style={styles.sourceNote}>
                Showing this phone&apos;s location — the stick has no GPS fix yet.
              </ThemedText>
            )}
            <LeafletMap latitude={lat} longitude={lon} accuracyM={effective.accuracyM} />
            <Pressable onPress={openInMaps} style={styles.openMapsBtn}>
              <ThemedText style={styles.openMapsLabel}>Open in Google Maps</ThemedText>
            </Pressable>
          </View>
        ) : (
          <ThemedView style={styles.mapPlaceholder}>
            <ThemedText style={styles.mapPlaceholderText}>Indoors</ThemedText>
            <ThemedText style={styles.mapPlaceholderHint}>
              GPS only works outdoors.
            </ThemedText>
          </ThemedView>
        )}

        <ThemedView style={styles.card}>
          <ThemedText type="subtitle">Details</ThemedText>
          <InfoRow label="Latitude" value={lat != null ? lat.toFixed(6) : '—'} />
          <InfoRow label="Longitude" value={lon != null ? lon.toFixed(6) : '—'} />
          <InfoRow
            label="Altitude"
            value={
              typeof location.data?.altitude === 'number'
                ? `${location.data.altitude.toFixed(1)} m`
                : '—'
            }
          />
          <InfoRow
            label="Accuracy"
            value={
              typeof location.data?.accuracy_m === 'number'
                ? `±${location.data.accuracy_m.toFixed(0)} m`
                : '—'
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

        {!online && !onPhone && (
          <ThemedText style={styles.errorBanner}>
            Indoors — no GPS signal. GPS only works outdoors with a clear view of the sky.
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
  mapWrap: {
    gap: 8,
  },
  sourceNote: {
    fontSize: 13,
    opacity: 0.8,
    textAlign: 'center',
  },
  mapPlaceholder: {
    height: 280,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  mapPlaceholderText: {
    fontSize: 16,
    fontWeight: '600',
  },
  mapPlaceholderHint: {
    fontSize: 13,
    opacity: 0.7,
    marginTop: 4,
    textAlign: 'center',
    paddingHorizontal: 16,
  },
  openMapsBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: Palette.primary,
    borderRadius: 8,
    alignItems: 'center',
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
    color: Palette.critical,
    textAlign: 'center',
  },
});
