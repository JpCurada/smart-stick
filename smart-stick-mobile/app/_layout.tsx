import { DefaultTheme, ThemeProvider, type Theme } from '@react-navigation/native';
import * as Notifications from 'expo-notifications';
import { router, Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { Palette } from '@/constants/theme';
import { registerForPushNotifications } from '@/lib/notifications';

export const unstable_settings = {
  anchor: '(tabs)',
};

const appTheme: Theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: Palette.primary,
    background: Palette.background,
    card: Palette.surface,
    text: Palette.text,
    border: Palette.border,
    notification: Palette.primary,
  },
};

export default function RootLayout() {
  useEffect(() => {
    // Register the guardian phone with the RPi so it can receive SOS pushes.
    registerForPushNotifications().then((result) => {
      if (!result.registered) {
        console.warn('[notifications] not registered:', result.reason);
      }
    });

    // Tapping an SOS notification (foreground OR lock screen) routes the
    // guardian to the live-view tab so they can see the cane's location.
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as { type?: string } | null;
      if (data?.type === 'sos') {
        router.push('/(tabs)/location');
      }
    });

    return () => sub.remove();
  }, []);

  return (
    <ThemeProvider value={appTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
      <StatusBar style="dark" />
    </ThemeProvider>
  );
}
