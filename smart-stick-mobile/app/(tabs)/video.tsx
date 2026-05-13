/**
 * Tab 5: VIDEO — live camera feed.
 *
 * MVP polls /api/latest_frame at ~1 FPS by appending a cache-busting
 * timestamp. WebSocket streaming is Phase 2.
 *
 * Note: the backend currently returns HTTP 501 for /api/latest_frame.
 * The UI still renders the polling shell so the wiring is in place — the
 * Image just shows a friendly fallback until the backend serves frames.
 */
import { Image } from 'expo-image';
import { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ActionButton } from '@/components/action-button';
import { InfoRow } from '@/components/info-row';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

export default function VideoScreen() {
  const [streaming, setStreaming] = useState(false);
  const [frameUrl, setFrameUrl] = useState<string | null>(null);

  const detections = usePoll(
    useCallback(() => api.latestDetections(), []),
    POLL_INTERVALS.detections,
  );

  useEffect(() => {
    if (!streaming) return;
    const tick = () => setFrameUrl(api.latestFrameUrl());
    tick();
    const id = setInterval(tick, POLL_INTERVALS.cameraFrame);
    return () => clearInterval(id);
  }, [streaming]);

  const fps = detections.data?.fps ?? null;
  const inferenceMs = detections.data?.inference_time_ms ?? null;
  const objectCount = detections.data?.detections.length ?? 0;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="title">Video</ThemedText>

        <ThemedView style={styles.frame}>
          {streaming && frameUrl ? (
            <Image
              source={{ uri: frameUrl }}
              style={styles.frameImage}
              contentFit="cover"
              cachePolicy="none"
            />
          ) : (
            <View style={styles.framePlaceholder}>
              <ThemedText style={styles.framePlaceholderText}>
                {streaming ? 'Loading frame…' : 'Press Start to view the camera.'}
              </ThemedText>
            </View>
          )}
        </ThemedView>

        <View style={styles.actions}>
          {streaming ? (
            <ActionButton
              title="Stop Stream"
              color={Palette.warning}
              onPress={() => setStreaming(false)}
            />
          ) : (
            <ActionButton
              title="Start Stream"
              color={Palette.success}
              onPress={() => setStreaming(true)}
            />
          )}
        </View>

        <ThemedView style={styles.card}>
          <ThemedText type="subtitle">Stream stats</ThemedText>
          <InfoRow label="Detection FPS" value={fps != null ? fps.toFixed(1) : '—'} />
          <InfoRow
            label="Inference"
            value={inferenceMs != null ? `${inferenceMs} ms` : '—'}
          />
          <InfoRow label="Objects in frame" value={String(objectCount)} />
          <InfoRow
            label="Status"
            value={streaming ? 'Streaming' : 'Stopped'}
          />
        </ThemedView>

        {detections.data?.alert && (
          <ThemedView style={styles.alertCard}>
            <ThemedText style={styles.alertTitle}>Latest alert</ThemedText>
            <ThemedText style={styles.alertBody}>
              {detections.data.alert.object_class} @{' '}
              {detections.data.alert.distance_m.toFixed(1)} m ·{' '}
              {detections.data.alert.severity}
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
  frame: {
    aspectRatio: 4 / 3,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  frameImage: {
    width: '100%',
    height: '100%',
  },
  framePlaceholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  framePlaceholderText: {
    textAlign: 'center',
    opacity: 0.6,
  },
  actions: {
    gap: 8,
  },
  card: {
    padding: 16,
    borderRadius: 12,
    gap: 4,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  alertCard: {
    padding: 14,
    borderRadius: 10,
    backgroundColor: Palette.warning,
  },
  alertTitle: {
    fontWeight: '700',
    color: '#fff',
  },
  alertBody: {
    color: '#fff',
    textTransform: 'capitalize',
  },
});
