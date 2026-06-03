/**
 * Tab 3: FIND — locate the stick on a map and alert it remotely.
 *
 * Shows the stick's last known position, then two independent controls:
 *   • "Vibrate Stick" -> POST /api/find?mode=vibrate (haptics only, silent)
 *   • "Play Sound"    -> POST /api/find?mode=buzz    (buzzer only, no vibration)
 *
 * Both go through /api/find (not /api/vibrate or /api/buzz) so the backend
 * re-asserts the override for the full alert window — a single one-shot
 * command is cancelled by the firmware on its next loop and only blips.
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
import { useEffectiveLocation } from '@/hooks/use-effective-location';
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
  const effective = useEffectiveLocation(location.data);
  const lat = effective.latitude;
  const lon = effective.longitude;
  const hasFix = lat != null && lon != null;
  const onPhone = effective.source === 'phone';

  const [pending, setPending] = useState<Pending>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const flash = (message: string, success: boolean) => {
    setFeedback({ message, success });
    setTimeout(() => setFeedback(null), 2500);
  };

  // Each button triggers a single-cue Find alert: vibrate-only or buzz-only.
  // The backend re-asserts the chosen override for the full alert duration so
  // the firmware doesn't cancel it after one loop.
  const handleFind = async (which: 'vibrate' | 'sound') => {
    setPending(which);
    try {
      await api.findMyStick(which === 'vibrate' ? 'vibrate' : 'buzz');
      flash(which === 'vibrate' ? 'Vibrating the stick…' : 'Sounding the stick…', true);
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
            {onPhone && (
              <ThemedText style={styles.sourceNote}>
                Showing this phone&apos;s location — the stick has no GPS fix yet.
              </ThemedText>
            )}
            <LeafletMap latitude={lat} longitude={lon} accuracyM={effective.accuracyM} />
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
