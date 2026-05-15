/**
 * LeafletMap — OpenStreetMap renderer via WebView.
 *
 * Works in Expo Go (no native module). Pans to `latitude`/`longitude` and
 * shows a marker. Re-renders only when coordinates change appreciably so the
 * WebView is not reloaded on every poll tick.
 */
import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

type Props = {
  latitude: number;
  longitude: number;
  accuracyM?: number | null;
  zoom?: number;
};

function buildHtml(lat: number, lon: number, zoom: number, accuracy: number | null): string {
  const accuracyCircle =
    accuracy != null && accuracy > 0
      ? `L.circle([${lat}, ${lon}], { radius: ${accuracy}, color: '#1d4ed8', weight: 1, fillOpacity: 0.12 }).addTo(map);`
      : '';

  return `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
      html, body, #map { height: 100%; margin: 0; padding: 0; background: #e5e7eb; }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      var map = L.map('map', { zoomControl: true, attributionControl: false })
        .setView([${lat}, ${lon}], ${zoom});
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map);
      L.marker([${lat}, ${lon}]).addTo(map);
      ${accuracyCircle}
    </script>
  </body>
</html>`;
}

export function LeafletMap({ latitude, longitude, accuracyM, zoom = 17 }: Props) {
  const html = useMemo(
    () => buildHtml(latitude, longitude, zoom, accuracyM ?? null),
    [
      Math.round(latitude * 1e5),
      Math.round(longitude * 1e5),
      zoom,
      accuracyM != null ? Math.round(accuracyM) : -1,
    ],
  );

  return (
    <View style={styles.container}>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        style={styles.webview}
        javaScriptEnabled
        domStorageEnabled
        scrollEnabled={false}
        androidLayerType="hardware"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: 280,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(127,127,127,0.3)',
  },
  webview: {
    flex: 1,
    backgroundColor: '#e5e7eb',
  },
});
