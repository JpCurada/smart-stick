/**
 * Push notification setup for the guardian phone.
 *
 * On first launch we ask iOS for notification permission, fetch the Expo
 * push token, and POST it to the Smart Stick RPi via /api/notifications/
 * register. After that the RPi can push an "Emergency SOS" notification
 * whenever the cane user holds the physical SOS button.
 *
 * Notifications received while the app is FOREGROUND are surfaced by the
 * handler below as a banner + sound; tapping a notification (foreground
 * or backgrounded/lock-screen) routes the guardian into the live-view
 * tab via expo-router.
 */
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { api } from './api';

const PROJECT_ID =
  (Constants?.expoConfig?.extra?.eas as { projectId?: string } | undefined)?.projectId ??
  Constants?.easConfig?.projectId;

/**
 * Show notifications as banners even when the app is in the foreground.
 * Without this, an SOS arriving while the guardian is using the app is
 * silently dropped into the notification tray.
 */
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export type RegistrationResult =
  | { registered: true; token: string }
  | { registered: false; reason: string };

/**
 * Ask for permission, fetch an Expo push token, send it to the RPi.
 *
 * Safe to call on every launch — the RPi's `register` endpoint upserts.
 */
export async function registerForPushNotifications(): Promise<RegistrationResult> {
  if (!Device.isDevice) {
    return { registered: false, reason: 'simulator — push tokens require a real device' };
  }

  const settings = await Notifications.getPermissionsAsync();
  let granted = settings.granted || settings.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL;

  if (!granted) {
    const request = await Notifications.requestPermissionsAsync({
      ios: { allowAlert: true, allowBadge: true, allowSound: true },
    });
    granted = request.granted || request.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL;
  }

  if (!granted) {
    return { registered: false, reason: 'notification permission denied' };
  }

  try {
    const tokenResponse = await Notifications.getExpoPushTokenAsync(
      PROJECT_ID ? { projectId: PROJECT_ID } : undefined,
    );
    const token = tokenResponse.data;
    await api.registerPushToken(
      token,
      'guardian',
      Platform.OS === 'ios' ? 'ios' : 'android',
    );
    return { registered: true, token };
  } catch (err) {
    return {
      registered: false,
      reason: err instanceof Error ? err.message : 'unknown push registration error',
    };
  }
}
