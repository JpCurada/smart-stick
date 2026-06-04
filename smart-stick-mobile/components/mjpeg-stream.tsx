/**
 * MjpegStream — renders an MJPEG endpoint inside a WebView.
 *
 * React Native's <Image> doesn't decode multipart/x-mixed-replace, but a
 * WebView with a plain <img src="..."> tag does. This gives a smooth
 * ~15 fps live feed without per-frame HTTP polling.
 */
import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

type Props = {
  url: string;
};

function buildHtml(url: string): string {
  // The <img> holds a single multipart/x-mixed-replace connection. The server
  // keeps the connection flowing (it re-sends the latest frame as a keep-alive
  // when detection is slow), so the feed should never go silent. If the
  // connection still drops (WiFi blip, server restart), the <img> fires an
  // 'error' — reconnect on that, cache-busted, so the feed comes back on its own.
  return `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <style>
      html, body { margin: 0; padding: 0; height: 100%; background: #000; overflow: hidden; }
      .wrap { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
      img { width: 100%; height: 100%; object-fit: cover; display: block; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <img id="stream" alt="stream" />
    </div>
    <script>
      var BASE = ${JSON.stringify(url)};
      var RECONNECT_MS = 1500;
      var img = document.getElementById('stream');

      function connect() {
        var sep = BASE.indexOf('?') === -1 ? '?' : '&';
        img.src = BASE + sep + 'cb=' + Date.now();
      }

      // Reconnect only when the connection actually drops.
      img.addEventListener('error', function () {
        setTimeout(connect, RECONNECT_MS);
      });

      connect();
    </script>
  </body>
</html>`;
}

export function MjpegStream({ url }: Props) {
  const html = useMemo(() => buildHtml(url), [url]);

  return (
    <View style={styles.container}>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        style={styles.webview}
        javaScriptEnabled
        scrollEnabled={false}
        androidLayerType="hardware"
        mixedContentMode="always"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  webview: {
    flex: 1,
    backgroundColor: '#000',
  },
});
