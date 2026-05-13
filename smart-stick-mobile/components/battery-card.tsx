import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Palette } from '@/constants/theme';
import type { BatteryStatus, HealthStatus } from '@/lib/types';

interface BatteryCardProps {
  battery: BatteryStatus | null;
}

const HEALTH_COLORS: Record<HealthStatus, string> = {
  good: Palette.success,
  warning: Palette.warning,
  critical: Palette.critical,
};

export function BatteryCard({ battery }: BatteryCardProps) {
  if (!battery) {
    return (
      <ThemedView style={styles.card}>
        <ThemedText type="subtitle">Battery</ThemedText>
        <ThemedText style={styles.muted}>No reading yet…</ThemedText>
      </ThemedView>
    );
  }

  const pct = Math.max(0, Math.min(100, battery.percentage));
  const healthColor = HEALTH_COLORS[battery.health];

  return (
    <ThemedView style={styles.card}>
      <View style={styles.row}>
        <ThemedText type="subtitle">Battery</ThemedText>
        <View style={[styles.healthDot, { backgroundColor: healthColor }]} />
      </View>
      <ThemedText style={styles.percentage}>{pct}%</ThemedText>
      <View style={styles.barTrack}>
        <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: healthColor }]} />
      </View>
      <View style={styles.metaRow}>
        <Meta label="Voltage" value={`${battery.voltage.toFixed(2)} V`} />
        <Meta label="Health" value={battery.health} />
        <Meta
          label="Runtime"
          value={battery.runtime_minutes != null ? `${battery.runtime_minutes} min` : '—'}
        />
      </View>
    </ThemedView>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.meta}>
      <ThemedText style={styles.metaLabel}>{label}</ThemedText>
      <ThemedText style={styles.metaValue}>{value}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderRadius: 12,
    gap: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  healthDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  percentage: {
    fontSize: 48,
    fontWeight: '700',
    lineHeight: 52,
  },
  barTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(127,127,127,0.2)',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  meta: {
    flex: 1,
  },
  metaLabel: {
    fontSize: 12,
    opacity: 0.6,
  },
  metaValue: {
    fontSize: 14,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  muted: {
    opacity: 0.6,
  },
});
