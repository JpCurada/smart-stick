/**
 * App-wide color palette and typography.
 *
 * The app intentionally locks to a single light theme regardless of the
 * OS dark-mode setting. Caregivers see the same look on every device.
 */
import { Platform } from 'react-native';

/** Primary brand pink. Used for active tabs, primary buttons, and the
 *  status accent. */
export const PRIMARY = '#fa5cef';

/** Hover / pressed state — a touch deeper than the primary so taps feel
 *  responsive. */
export const PRIMARY_DARK = '#e83fd6';

export const Palette = {
  primary: PRIMARY,
  primaryDark: PRIMARY_DARK,

  background: '#ffffff',
  surface: '#ffffff',
  surfaceMuted: '#fdf2fc', // very light pink wash for cards/sections

  text: '#1a1a1a',
  textMuted: '#6b7280',

  border: '#e5e7eb',
  borderStrong: '#d1d5db',

  success: '#16a34a',
  warning: '#f59e0b',
  critical: '#dc2626',
  onPrimary: '#ffffff',
} as const;

/**
 * Compatibility shim so existing `Colors[scheme]` lookups keep working.
 * Both light and dark resolve to the same light palette.
 */
const sharedScheme = {
  text: Palette.text,
  background: Palette.background,
  tint: Palette.primary,
  icon: Palette.textMuted,
  tabIconDefault: Palette.textMuted,
  tabIconSelected: Palette.primary,
};

export const Colors = {
  light: sharedScheme,
  dark: sharedScheme,
};

export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
});
