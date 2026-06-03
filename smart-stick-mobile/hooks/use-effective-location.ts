/**
 * useEffectiveLocation — pick the best coordinate to plot on the map.
 *
 * The stick's GPS (reported over WiFi via /api/location) is always primary:
 * the whole point is showing where the blind person is. But the stick has no
 * fix indoors or during a GPS cold start, which leaves the map blank. When
 * that happens we fall back to the *phone's* GPS so the caregiver still sees a
 * real position, and expose a `source` flag so the UI can say which it is.
 *
 * The phone fix is only fetched when the stick lacks one — we never override a
 * live stick fix with the phone, and we don't poll the phone GPS when it isn't
 * needed (battery).
 */
import * as Location from 'expo-location';
import { useEffect, useRef, useState } from 'react';

import type { LocationFix } from '@/lib/types';

export type LocationSource = 'stick' | 'phone' | 'none';

export interface EffectiveLocation {
  latitude: number | null;
  longitude: number | null;
  accuracyM: number | null;
  source: LocationSource;
}

// How often to refresh the phone fix while we're relying on it. The stick
// polls every 5 s; matching that keeps the fallback marker reasonably fresh
// without hammering the GPS.
const PHONE_REFRESH_MS = 5000;

function isFix(loc: LocationFix | null | undefined): loc is LocationFix {
  return (
    loc != null &&
    typeof loc.latitude === 'number' &&
    typeof loc.longitude === 'number'
  );
}

export function useEffectiveLocation(stick: LocationFix | null | undefined): EffectiveLocation {
  const stickHasFix = isFix(stick);
  const [phone, setPhone] = useState<Location.LocationObject | null>(null);
  const [permission, setPermission] = useState<boolean | null>(null);
  const askedRef = useRef(false);

  // Only fetch the phone fix while the stick lacks one. The effect re-runs when
  // stickHasFix flips, tearing down the interval as soon as the stick recovers.
  useEffect(() => {
    if (stickHasFix) return;

    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    const read = async () => {
      try {
        const pos = await Location.getLastKnownPositionAsync({});
        const fresh = pos ?? (await Location.getCurrentPositionAsync({}));
        if (!cancelled && fresh) setPhone(fresh);
      } catch {
        // GPS off or denied — leave phone null, UI falls through to 'none'.
      }
    };

    const start = async () => {
      if (!askedRef.current) {
        askedRef.current = true;
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (cancelled) return;
        setPermission(status === 'granted');
        if (status !== 'granted') return;
      } else if (permission === false) {
        return;
      }
      await read();
      timer = setInterval(read, PHONE_REFRESH_MS);
    };

    void start();
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [stickHasFix, permission]);

  if (stickHasFix) {
    return {
      latitude: stick.latitude,
      longitude: stick.longitude,
      accuracyM: stick.accuracy_m ?? null,
      source: 'stick',
    };
  }

  if (phone) {
    return {
      latitude: phone.coords.latitude,
      longitude: phone.coords.longitude,
      accuracyM: phone.coords.accuracy ?? null,
      source: 'phone',
    };
  }

  return { latitude: null, longitude: null, accuracyM: null, source: 'none' };
}
