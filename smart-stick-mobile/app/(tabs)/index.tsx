/**
 * Tab 1: HOME — device status.
 *
 * Polls /api/status; degrades to an offline state if the stick is
 * unreachable.
 */
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { InfoRow } from '@/components/info-row';
import { SosBanner } from '@/components/sos-banner';
import { StatusBadge } from '@/components/status-badge';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

export default function HomeScreen() {
  const status = usePoll(useCallback(() => api.status(), []), POLL_INTERVALS.status);

  const online = status.error == null && status.data != null;
  const fps = status.data?.detection.fps ?? null;
  const inferenceMs = status.data?.detection.inference_time_ms ?? null;
  const lastSync = status.data?.timestamp ?? null;

  // Track which SOS timestamps the guardian has acknowledged so the banner
  // can be dismissed but reappear instantly if the user presses SOS again.
  const sos = status.data?.sos ?? null;
  const [acknowledgedAt, setAcknowledgedAt] = useState<string | null>(null);
  const sosVisible = sos != null && sos.timestamp !== acknowledgedAt;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={status.loading} onRefresh={status.refetch} />
        }
      >
        <View style={styles.header}>
          <ThemedText type="title">Smart Stick</ThemedText>
          <StatusBadge online={online} />
        </View>

        <SosBanner
          visible={sosVisible}
          location={status.data?.location ?? null}
          triggeredAt={sos?.timestamp ?? null}
          onDismiss={() => setAcknowledgedAt(sos?.timestamp ?? null)}
        />

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

        <ThemedView style={styles.card}>
          <ThemedText type="subtitle">Navigation</ThemedText>
          <ThemedText style={styles.cardNote}>Only works when GPS is turned on</ThemedText>
        </ThemedView>

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
  card: {
    padding: 16,
    borderRadius: 12,
    gap: 4,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  cardNote: {
    opacity: 0.6,
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
