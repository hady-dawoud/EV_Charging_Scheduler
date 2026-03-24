export const colors = {
  // Backgrounds
  background: '#0A0A0F',
  surface: '#1A1A24',
  surfaceLight: '#252532',

  // Primary accent (electric blue)
  primary: '#00D4FF',
  primaryMuted: '#00A3C4',

  // Secondary accent (neon green)
  accent: '#00FF94',
  accentMuted: '#00C472',

  // Text
  textPrimary: '#FFFFFF',
  textSecondary: '#A0A0B0',
  textMuted: '#6B6B7B',

  // Status
  success: '#00FF94',
  warning: '#FFB800',
  error: '#FF4D6A',

  // Border
  border: '#2A2A3A',
  borderLight: '#3A3A4A',

  // Overlay
  overlay: 'rgba(0, 0, 0, 0.6)',
} as const;

export type ColorKey = keyof typeof colors;
