export const colors = {
  // Backgrounds
  background: '#0A0B0D',
  surface: '#12131A',
  surfaceLight: '#1C1D26',

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
  border: '#1F2029',
  borderLight: '#2A2B36',

  // Glass effects
  glass: 'rgba(255, 255, 255, 0.08)',
  glassBorder: 'rgba(255, 255, 255, 0.12)',

  // Glow effects (for shadows)
  glowGreen: 'rgba(0, 255, 148, 0.25)',
  glowCyan: 'rgba(0, 212, 255, 0.25)',

  // Overlay
  overlay: 'rgba(0, 0, 0, 0.6)',
} as const;

export type ColorKey = keyof typeof colors;
