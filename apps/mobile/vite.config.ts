import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

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

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
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
  define: {
    global: 'globalThis',
    __DEV__: JSON.stringify(true),
    DEV: JSON.stringify(true),
    'process.env.NODE_ENV': JSON.stringify('development'),
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
});
