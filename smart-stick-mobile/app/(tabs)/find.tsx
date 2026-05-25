/**
 * Tab 3: FIND — remote buzz + vibrate to locate a lost stick.
 *
 * Single button fires POST /api/find which triggers buzzer AND vibrator
 * together on the cane and opens a 30-second window during which detection
 * haptics/buzzer are suppressed so the find sequence isn't drowned out.
 */
import { Bell } from 'lucide-react-native';
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
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const flash = (message: string, success: boolean) => {
    setFeedback({ message, success });
    setTimeout(() => setFeedback(null), 2500);
  };

  const handleFind = async () => {
    setLoading(true);
    try {
      await api.findMyStick();
      flash('Buzzing and vibrating the stick…', true);
    } catch {
      flash('Could not reach the stick.', false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="title">Find Stick</ThemedText>
        <ThemedText style={styles.subtitle}>
          Make the stick buzz and vibrate so you can locate it.
        </ThemedText>

        <View style={styles.buttons}>
          <ActionButton
            title="Find My Stick"
            icon={Bell}
            color={Palette.primary}
            onPress={handleFind}
            loading={loading}
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
            • Buzzer plus vibration fire together for one short pulse.
          </ThemedText>
          <ThemedText style={styles.noteText}>
            • Detection alerts are paused for 30 seconds so the find sequence is unambiguous.
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
