import type { LucideIcon } from 'lucide-react-native';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Palette } from '@/constants/theme';

interface ActionButtonProps {
  title: string;
  onPress: () => void | Promise<void>;
  color?: string;
  loading?: boolean;
  disabled?: boolean;
  icon?: LucideIcon;
}

export function ActionButton({
  title,
  onPress,
  color = Palette.primary,
  loading = false,
  disabled = false,
  icon: Icon,
}: ActionButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: color, opacity: isDisabled ? 0.5 : pressed ? 0.85 : 1 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color="#fff" />
      ) : (
        <View style={styles.row}>
          {Icon && <Icon color="#fff" size={20} />}
          <ThemedText style={styles.label}>{title}</ThemedText>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 50,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  label: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});
