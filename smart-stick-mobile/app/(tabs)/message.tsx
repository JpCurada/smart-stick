/**
 * Tab 4: MESSAGE — send TTS to the stick.
 *
 * Six quick-message buttons map to the templates in
 * docs/specs.md §6.1. Custom messages are validated client-side
 * (max 500 chars) before being sent to /api/message.
 */
import { Check, Hourglass } from 'lucide-react-native';
import { useCallback, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ActionButton } from '@/components/action-button';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { POLL_INTERVALS } from '@/constants/api';
import { Palette } from '@/constants/theme';
import { usePoll } from '@/hooks/use-poll';
import { api } from '@/lib/api';

const QUICK_MESSAGES = [
  "I'm on my way!",
  'Stay where you are',
  'Call me when you can',
  'Are you okay?',
  "I'll be there soon",
  'Take a break',
] as const;

const MAX_LEN = 500;

export default function MessageScreen() {
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const history = usePoll(
    useCallback(() => api.messageHistory(), []),
    POLL_INTERVALS.battery,
  );

  const send = async (text: string) => {
    const clean = text.trim();
    if (!clean) return;
    setSending(true);
    try {
      await api.sendMessage(clean.slice(0, MAX_LEN), 'normal');
      setFeedback('Message queued for playback.');
      if (text === draft) setDraft('');
      void history.refetch();
    } catch {
      setFeedback('Failed to deliver message.');
    } finally {
      setSending(false);
      setTimeout(() => setFeedback(null), 2500);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <ThemedText type="title">Message</ThemedText>

          <View>
            <ThemedText type="subtitle">Quick messages</ThemedText>
            <View style={styles.quickGrid}>
              {QUICK_MESSAGES.map((msg) => (
                <Pressable
                  key={msg}
                  onPress={() => send(msg)}
                  disabled={sending}
                  style={({ pressed }) => [
                    styles.quickButton,
                    { opacity: pressed || sending ? 0.7 : 1 },
                  ]}
                >
                  <ThemedText style={styles.quickButtonText}>{msg}</ThemedText>
                </Pressable>
              ))}
            </View>
          </View>

          <View>
            <ThemedText type="subtitle">Custom message</ThemedText>
            <TextInput
              value={draft}
              onChangeText={(t) => setDraft(t.slice(0, MAX_LEN))}
              placeholder="Type a message…"
              placeholderTextColor="rgba(127,127,127,0.6)"
              multiline
              style={styles.textInput}
            />
            <ThemedText style={styles.counter}>
              {draft.length}/{MAX_LEN}
            </ThemedText>
            <ActionButton
              title="Send"
              onPress={() => send(draft)}
              loading={sending}
              disabled={draft.trim().length === 0}
            />
          </View>

          {feedback && <ThemedText style={styles.feedback}>{feedback}</ThemedText>}

          <View>
            <ThemedText type="subtitle">Recent messages</ThemedText>
            {history.data?.messages?.length ? (
              history.data.messages.slice(0, 20).map((m) => (
                <ThemedView key={m.message_id} style={styles.historyItem}>
                  <ThemedText style={styles.historyText}>{m.text}</ThemedText>
                  <View style={styles.historyMeta}>
                    <ThemedText style={styles.metaSmall}>
                      {new Date(m.timestamp).toLocaleTimeString()}
                    </ThemedText>
                    <View style={styles.statusRow}>
                      {m.delivered ? (
                        <Check size={14} color="#16a34a" />
                      ) : (
                        <Hourglass size={14} color="#f59e0b" />
                      )}
                      <ThemedText style={styles.metaSmall}>
                        {m.delivered ? 'delivered' : 'queued'}
                      </ThemedText>
                    </View>
                  </View>
                </ThemedView>
              ))
            ) : (
              <ThemedText style={styles.empty}>No messages yet.</ThemedText>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  content: { padding: 16, gap: 16 },
  quickGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  quickButton: {
    backgroundColor: Palette.primary,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    flexBasis: '48%',
    flexGrow: 1,
  },
  quickButtonText: {
    color: '#fff',
    fontWeight: '600',
    textAlign: 'center',
  },
  textInput: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.4)',
    borderRadius: 10,
    padding: 12,
    minHeight: 80,
    marginTop: 8,
    fontSize: 16,
    color: '#000',
    backgroundColor: 'rgba(127,127,127,0.05)',
  },
  counter: {
    textAlign: 'right',
    opacity: 0.6,
    marginVertical: 4,
    fontSize: 12,
  },
  feedback: {
    textAlign: 'center',
    color: '#16a34a',
  },
  historyItem: {
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  historyText: {
    marginBottom: 4,
  },
  historyMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaSmall: {
    fontSize: 12,
    opacity: 0.6,
  },
  empty: {
    opacity: 0.5,
    marginTop: 8,
  },
});
