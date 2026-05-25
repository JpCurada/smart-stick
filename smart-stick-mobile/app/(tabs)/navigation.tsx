/**
 * Tab 6: NAVIGATION — mock LSTM movement analyzer output.
 *
 * Polls /api/navigation_log for the most recent navigational narrations.
 * Each entry shows the spoken text along with structured fields (object,
 * distance, position, suggestion) so the guardian can read what the user
 * just heard in the earpiece.
 */
import { useCallback } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';
import type { NavigationLogEntry } from '@/lib/types';

export default function NavigationScreen() {
  const log = usePoll(
    useCallback(() => api.navigationLog(50), []),
    POLL_INTERVALS.navigationLog,
  );

  const entries: NavigationLogEntry[] = log.data?.entries ?? [];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="title">Navigation</ThemedText>
        <ThemedText style={styles.subtitle}>
          Mock movement-analyzer narration spoken through the earpiece.
        </ThemedText>

        <ThemedView style={styles.card}>
          <ThemedText type="subtitle">Recent narrations</ThemedText>
          {entries.length === 0 ? (
            <ThemedText style={styles.empty}>
              No narrations yet. The analyzer speaks when an obstacle is close enough.
            </ThemedText>
          ) : (
            entries.map((entry) => (
              <View key={entry.id} style={styles.entry}>
                <ThemedText style={styles.entryText}>{entry.text}</ThemedText>
                <View style={styles.metaRow}>
                  <ThemedText style={styles.meta}>
                    {entry.object_class} · {entry.distance_m.toFixed(1)} m · {entry.position}
                  </ThemedText>
                  <ThemedText style={styles.time}>
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </ThemedText>
                </View>
              </View>
            ))
          )}
        </ThemedView>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  content: { padding: 16, gap: 16 },
  subtitle: {
    opacity: 0.7,
  },
  card: {
    padding: 16,
    borderRadius: 12,
    gap: 4,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  empty: {
    opacity: 0.6,
    paddingVertical: 8,
  },
  entry: {
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(127,127,127,0.2)',
    gap: 4,
  },
  entryText: {
    fontWeight: '600',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  meta: {
    opacity: 0.7,
    textTransform: 'capitalize',
    fontVariant: ['tabular-nums'],
  },
  time: {
    opacity: 0.55,
    fontSize: 12,
    fontVariant: ['tabular-nums'],
  },
});
