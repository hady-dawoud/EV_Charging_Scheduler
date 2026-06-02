import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

const extensions = [
  '.web.tsx',
  '.web.ts',
  '.tsx',
  '.ts',
  '.web.jsx',
  '.web.js',
  '.jsx',
  '.js',
  '.json',
];

const apiBaseUrl =
  process.env.VITE_API_BASE_URL ||
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  '';

const isDev = process.env.NODE_ENV !== 'production';

export default defineConfig({
  plugins: [react()],
  define: {
    global: 'globalThis',
    __DEV__: JSON.stringify(isDev),
    DEV: JSON.stringify(isDev),
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    'process.env.EXPO_PUBLIC_API_BASE_URL': JSON.stringify(apiBaseUrl),
  },
  resolve: {
    alias: [
      {
        find: 'react-native-shadow-2',
        replacement: path.resolve(process.cwd(), 'src/web-shims/react-native-shadow-2.tsx'),
      },
      {
        find: /^react-native$/,
        replacement: 'react-native-web',
      },
      {
        find: /^lucide-react-native$/,
        replacement: 'lucide-react',
      },
    ],
    extensions,
  },
  optimizeDeps: {
    exclude: ['react-native'],
    esbuildOptions: {
      resolveExtensions: extensions,
      loader: {
        '.js': 'jsx',
      },
      jsx: 'automatic',
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
});
