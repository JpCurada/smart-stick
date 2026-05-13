import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Palette } from '@/constants/theme';

interface StatusBadgeProps {
  online: boolean;
  label?: string;
}

export function StatusBadge({ online, label }: StatusBadgeProps) {
  const text = label ?? (online ? 'Online' : 'Offline');
  const color = online ? Palette.success : Palette.critical;
  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <ThemedText style={styles.text}>{text}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    alignSelf: 'flex-start',
  },
  text: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
  },
});
