/**
 * Tab 5: VIDEO — live MJPEG camera feed from the stick.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ActionButton } from '@/components/action-button';
import { InfoRow } from '@/components/info-row';
import { MjpegStream } from '@/components/mjpeg-stream';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';
import type { DetectionDto } from '@/lib/types';

const RECOGNITION_LOG_LIMIT = 10;

type RecognitionLogEntry = DetectionDto & { key: string };

const entryKey = (d: DetectionDto): string =>
  `${d.timestamp}|${d.class}|${d.bbox ? d.bbox.join(',') : 'nobbox'}`;

export default function VideoScreen() {
  const [streaming, setStreaming] = useState(false);
  const [recognitionLog, setRecognitionLog] = useState<RecognitionLogEntry[]>([]);
  const seenKeysRef = useRef<Set<string>>(new Set());

  const detections = usePoll(
    useCallback(() => api.latestDetections(), []),
    POLL_INTERVALS.detections,
  );

  useEffect(() => {
    const incoming = detections.data?.detections;
    if (!incoming || incoming.length === 0) return;
    const fresh: RecognitionLogEntry[] = [];
    for (const det of incoming) {
      const key = entryKey(det);
      if (seenKeysRef.current.has(key)) continue;
      seenKeysRef.current.add(key);
      fresh.push({ ...det, key });
    }
    if (fresh.length === 0) return;
    setRecognitionLog((prev) => {
      const next = [...fresh.reverse(), ...prev].slice(0, RECOGNITION_LOG_LIMIT);
      // Trim the seen-set so it doesn't grow unbounded.
      const keep = new Set(next.map((e) => e.key));
      seenKeysRef.current = keep;
      return next;
    });
  }, [detections.data]);

  const fps = detections.data?.fps ?? null;
  const inferenceMs = detections.data?.inference_time_ms ?? null;
  const objectCount = detections.data?.detections.length ?? 0;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="title">Video</ThemedText>

        <ThemedView style={styles.frame}>
          {streaming ? (
            <MjpegStream url={api.streamUrl()} />
          ) : (
            <View style={styles.framePlaceholder}>
              <ThemedText style={styles.framePlaceholderText}>
                Press Start to view the camera.
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

        <ThemedView style={styles.card}>
          <ThemedText type="subtitle">Recognition</ThemedText>
          {recognitionLog.length === 0 ? (
            <ThemedText style={styles.logEmpty}>
              No recognitions yet. Start the stream to begin logging.
            </ThemedText>
          ) : (
            recognitionLog.map((entry) => (
              <View key={entry.key} style={styles.logRow}>
                <ThemedText style={styles.logClass}>{entry.class}</ThemedText>
                <ThemedText style={styles.logMeta}>
                  {entry.distance_m.toFixed(1)} m · {(entry.confidence * 100).toFixed(0)}%
                </ThemedText>
                <ThemedText style={styles.logTime}>
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </ThemedText>
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
  frame: {
    aspectRatio: 4 / 3,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
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
  logEmpty: {
    opacity: 0.6,
    paddingVertical: 8,
  },
  logRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(127,127,127,0.2)',
    gap: 8,
  },
  logClass: {
    flex: 1,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  logMeta: {
    opacity: 0.8,
    fontVariant: ['tabular-nums'],
  },
  logTime: {
    opacity: 0.55,
    fontSize: 12,
    fontVariant: ['tabular-nums'],
  },
});
