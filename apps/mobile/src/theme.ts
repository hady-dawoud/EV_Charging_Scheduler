import { ViewStyle, TextStyle, Platform } from 'react-native';

const isWeb = Platform.OS === 'web';

// Inline style helpers — use these as inline styles on components
// (StyleSheet.create strips unknown CSS props on web)
export const webStyles = {
  glass: isWeb
    ? ({ backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' } as any)
    : {},
  neonGlow: isWeb
    ? ({ boxShadow: '0 0 8px rgba(0, 255, 0, 0.4), 0 0 20px rgba(0, 255, 0, 0.25), 0 0 40px rgba(0, 255, 0, 0.1)' } as any)
    : {},
  neonGlowSmall: isWeb
    ? ({ boxShadow: '0 0 4px rgba(0, 255, 0, 0.5), 0 0 10px rgba(0, 255, 0, 0.3)' } as any)
    : {},
  neonGlowIntense: isWeb
    ? ({ boxShadow: '0 0 15px rgba(0, 255, 0, 0.5), 0 0 40px rgba(0, 255, 0, 0.3), 0 0 80px rgba(0, 255, 0, 0.1)' } as any)
    : {},
  blueGlow: isWeb
    ? ({ boxShadow: '0 4px 12px rgba(37, 99, 235, 0.4), 0 8px 24px rgba(37, 99, 235, 0.2)' } as any)
    : {},
  neonText: isWeb
    ? ({ textShadow: '0 0 10px rgba(0, 255, 0, 0.5)' } as any)
    : {},
};

export const theme = {
  colors: {
    // Core backgrounds
    background: '#0A0B0D',
    surface: '#1A1C1E',
    surfaceLight: 'rgba(255, 255, 255, 0.05)',

    // Neon green accent
    primary: '#00FF00',
    neonGreen: '#00FF00',

    // Glass layers
    glass: 'rgba(255, 255, 255, 0.1)',
    glassDark: 'rgba(0, 0, 0, 0.4)',
    glassBorder: '#3A3C3F',       // visible grey border for glass
    glassDarkBorder: '#2A2C2F',   // visible grey border for glass-dark

    // Text
    text: '#FFFFFF',
    textMuted: '#9CA3AF',

    // Misc
    border: '#333538',            // visible grey border
    error: '#EF4444',
    blue: '#2563EB',
  },

  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },

  radii: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    xxl: 32,
    full: 9999,
  },

  fonts: {
    sans: 'Inter',
  },

  // Glass morphism base styles (for StyleSheet)
  glass: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderWidth: 1,
    borderColor: '#3A3C3F',
  } as ViewStyle,

  glassDark: {
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderWidth: 1,
    borderColor: '#2A2C2F',
  } as ViewStyle,

  // Native-only shadow styles (for non-web platforms)
  neonGlow: (isWeb
    ? {}
    : { shadowColor: '#00FF00', shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.3, shadowRadius: 20, elevation: 10 }
  ) as ViewStyle,

  neonGlowSmall: (isWeb
    ? {}
    : { shadowColor: '#00FF00', shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.6, shadowRadius: 6, elevation: 5 }
  ) as ViewStyle,

  neonGlowIntense: (isWeb
    ? {}
    : { shadowColor: '#00FF00', shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.8, shadowRadius: 30, elevation: 15 }
  ) as ViewStyle,

  blueGlow: (isWeb
    ? {}
    : { shadowColor: '#2563EB', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.3, shadowRadius: 16, elevation: 10 }
  ) as ViewStyle,

  neonText: {
    color: '#00FF00',
    ...(isWeb
      ? {}
      : { textShadowColor: 'rgba(0, 255, 0, 0.5)', textShadowOffset: { width: 0, height: 0 }, textShadowRadius: 10 }),
  } as TextStyle,
};

export type Theme = typeof theme;
