/**
 * Tab 3: FIND — remote vibrate / sound to locate a lost stick.
 *
 * Buttons fire optimistic POSTs to /api/vibrate and /api/emergency/sos.
 * A toast-style banner shows the result of the most recent command.
 */
import { Vibrate, Volume2 } from 'lucide-react-native';
import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ActionButton } from '@/components/action-button';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Palette } from '@/constants/theme';
import { api } from '@/lib/api';

interface FeedbackState {
  message: string;
  success: boolean;
}

export default function FindScreen() {
  const [vibrateLoading, setVibrateLoading] = useState(false);
  const [soundLoading, setSoundLoading] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const flash = (message: string, success: boolean) => {
    setFeedback({ message, success });
    setTimeout(() => setFeedback(null), 2500);
  };

  const handleVibrate = async () => {
    setVibrateLoading(true);
    try {
      await api.vibrate(255, 500);
      flash('Vibrating stick…', true);
    } catch {
      flash('Could not reach the stick.', false);
    } finally {
      setVibrateLoading(false);
    }
  };

  const handleSound = async () => {
    setSoundLoading(true);
    try {
      await api.emergencySos();
      flash('Playing SOS tone…', true);
    } catch {
      flash('Could not reach the stick.', false);
    } finally {
      setSoundLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="title">Find Stick</ThemedText>
        <ThemedText style={styles.subtitle}>
          Trigger a vibration or sound to help locate the stick if it&apos;s misplaced.
        </ThemedText>

        <View style={styles.buttons}>
          <ActionButton
            title="Vibrate Stick"
            icon={Vibrate}
            color={Palette.primary}
            onPress={handleVibrate}
            loading={vibrateLoading}
          />
          <ActionButton
            title="Play SOS Sound"
            icon={Volume2}
            color={Palette.warning}
            onPress={handleSound}
            loading={soundLoading}
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

        <ThemedView style={styles.note}>
          <ThemedText type="subtitle">Notes</ThemedText>
          <ThemedText style={styles.noteText}>
            • Vibrate: max intensity for 500 ms.
          </ThemedText>
          <ThemedText style={styles.noteText}>
            • SOS sound: 2500 Hz repeating tone — distinct from every other alert.
          </ThemedText>
          <ThemedText style={styles.noteText}>
            • Works over the same WiFi network. BLE fallback is available when the stick is
            offline and within ~50 m.
          </ThemedText>
        </ThemedView>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  content: { padding: 16, gap: 16 },
  subtitle: { opacity: 0.7 },
  buttons: { gap: 12, marginTop: 8 },
  feedback: {
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  feedbackText: {
    color: '#fff',
    fontWeight: '600',
  },
  note: {
    padding: 16,
    borderRadius: 12,
    gap: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
    marginTop: 8,
  },
  noteText: {
    opacity: 0.8,
  },
});
