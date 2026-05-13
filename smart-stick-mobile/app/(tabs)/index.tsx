/**
 * Tab 1: HOME — device status & battery.
 *
 * Polls /api/battery and /api/status; degrades to an offline state if the
 * stick is unreachable.
 */
import { useCallback } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BatteryCard } from '@/components/battery-card';
import { InfoRow } from '@/components/info-row';
import { StatusBadge } from '@/components/status-badge';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

export default function HomeScreen() {
  const battery = usePoll(useCallback(() => api.battery(), []), POLL_INTERVALS.battery);
  const status = usePoll(useCallback(() => api.status(), []), POLL_INTERVALS.battery);

  const online = battery.error == null && battery.data != null;
  const fps = status.data?.detection.fps ?? null;
  const inferenceMs = status.data?.detection.inference_time_ms ?? null;
  const lastSync = battery.data?.timestamp ?? status.data?.timestamp ?? null;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={battery.loading} onRefresh={battery.refetch} />
        }
      >
        <View style={styles.header}>
          <ThemedText type="title">Smart Stick</ThemedText>
          <StatusBadge online={online} />
        </View>

        <BatteryCard battery={battery.data} />

        <View style={styles.section}>
          <ThemedText type="subtitle">Detection</ThemedText>
          <InfoRow label="FPS" value={fps != null ? fps.toFixed(1) : '—'} />
          <InfoRow
            label="Inference"
            value={inferenceMs != null ? `${inferenceMs} ms` : '—'}
          />
          <InfoRow
            label="Latest alert"
            value={status.data?.detection.latest_alert?.object_class ?? 'None'}
          />
        </View>

        <View style={styles.section}>
          <ThemedText type="subtitle">Sync</ThemedText>
          <InfoRow
            label="Last sync"
            value={lastSync ? new Date(lastSync).toLocaleTimeString() : '—'}
          />
          <InfoRow
            label="Distance today"
            value={
              status.data?.session?.distance_km != null
                ? `${status.data.session.distance_km.toFixed(2)} km`
                : '—'
            }
          />
        </View>

        {!online && (
          <ThemedView style={styles.errorCard}>
            <ThemedText style={styles.errorTitle}>Stick unreachable</ThemedText>
            <ThemedText style={styles.errorBody}>
              Your phone needs to be on the same WiFi network as the stick. Remote access
              over cellular is not supported in this version.
            </ThemedText>
          </ThemedView>
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
  section: {
    gap: 4,
  },
  errorCard: {
    padding: 14,
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Palette.critical,
    gap: 6,
    marginTop: 8,
  },
  errorTitle: {
    color: Palette.critical,
    fontWeight: '700',
  },
  errorBody: {
    color: Palette.critical,
    opacity: 0.9,
  },
});
