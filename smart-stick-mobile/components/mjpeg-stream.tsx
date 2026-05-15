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
      <img src="${url}" alt="stream" />
    </div>
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
        javaScriptEnabled={false}
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
