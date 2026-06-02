/**
 * Tab 3: FIND — locate the stick on a map and alert it remotely.
 *
 * Shows the stick's last known position, then two independent controls:
 *   • "Vibrate Stick" -> POST /api/vibrate (one strong pulse)
 *   • "Play Sound"    -> POST /api/buzz   (audible beep pattern)
 *
 * The two are split so a helper can pick whichever cue is easier to notice.
 */
import { Volume2, Vibrate } from 'lucide-react-native';
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ActionButton } from '@/components/action-button';
import { LeafletMap } from '@/components/leaflet-map';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

// Explicit green/orange for the two find actions — distinct from the
// pink brand palette so the two cues read as clearly different controls.
const VIBRATE_COLOR = '#34d399';
const SOUND_COLOR = '#f97316';

type Pending = 'vibrate' | 'sound' | null;

interface FeedbackState {
  message: string;
  success: boolean;
}

export default function FindScreen() {
  const location = usePoll(useCallback(() => api.location(), []), POLL_INTERVALS.location);
  const lat = typeof location.data?.latitude === 'number' ? location.data.latitude : null;
  const lon = typeof location.data?.longitude === 'number' ? location.data.longitude : null;
  const hasFix = lat != null && lon != null;

  const [pending, setPending] = useState<Pending>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const flash = (message: string, success: boolean) => {
    setFeedback({ message, success });
    setTimeout(() => setFeedback(null), 2500);
  };

  // Both buttons trigger the same combined buzz+vibrate Find alert on the
  // stick (POST /api/find). The backend re-asserts the override for the full
  // alert duration so the firmware doesn't cancel it after one loop.
  const handleFind = async (which: 'vibrate' | 'sound') => {
    setPending(which);
    try {
      await api.findMyStick();
      flash(which === 'vibrate' ? 'Vibrating the stick…' : 'Alerting the stick…', true);
    } catch {
      flash('Could not reach the stick.', false);
    } finally {
      setPending(null);
    }
  };

  const handleVibrate = () => handleFind('vibrate');
  const handleSound = () => handleFind('sound');

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={location.loading} onRefresh={location.refetch} />
        }
      >
        <View style={styles.header}>
          <ThemedText type="title">Find My Stick</ThemedText>
          <ThemedText style={styles.subtitle}>Locate and alert your device</ThemedText>
        </View>

        {hasFix ? (
          <View style={styles.mapWrap}>
            <LeafletMap
              latitude={lat}
              longitude={lon}
              accuracyM={location.data?.accuracy_m ?? null}
            />
          </View>
        ) : (
          <ThemedView style={styles.mapPlaceholder}>
            <ThemedText style={styles.mapPlaceholderText}>No location yet</ThemedText>
            <ThemedText style={styles.mapPlaceholderHint}>
              The stick reports its position over WiFi. GPS only works outdoors.
            </ThemedText>
          </ThemedView>
        )}

        <View style={styles.buttons}>
          <ActionButton
            title="Vibrate Stick"
            icon={Vibrate}
            color={VIBRATE_COLOR}
            onPress={handleVibrate}
            loading={pending === 'vibrate'}
            disabled={pending !== null}
          />
          <ActionButton
            title="Play Sound"
            icon={Volume2}
            color={SOUND_COLOR}
            onPress={handleSound}
            loading={pending === 'sound'}
            disabled={pending !== null}
          />
        </View>

        {feedback && (
          <ThemedView
            style={[
              styles.feedback,
              { backgroundColor: feedback.success ? Palette.success : Palette.critical },
            ]}
          >
            <ThemedText style={styles.feedbackText}>{feedback.message}</ThemedText>
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
    alignItems: 'center',
    gap: 4,
  },
  subtitle: { opacity: 0.7 },
  mapWrap: { gap: 8 },
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
  buttons: { gap: 14, marginTop: 4 },
  feedback: {
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  feedbackText: {
    color: '#fff',
    fontWeight: '600',
  },
});
