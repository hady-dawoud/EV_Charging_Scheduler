import React, { useRef, useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Platform,
  ActivityIndicator,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Zap } from 'lucide-react-native';
import Svg, { Circle, Defs, RadialGradient, Stop } from 'react-native-svg';
import { NeonButton } from '../components/NeonButton';
import { theme, webStyles } from '../theme';
import { api } from '../services/api';
import { authStorage } from '../services/authStorage';
import { useAuthStore } from '../stores/authStore';

const isWeb = Platform.OS === 'web';
const SPLASH_GLOW_SIZE = 384;
const SPLASH_GLOW_BLUR = 100;
const NATIVE_GLOW_EXTRA = 116;
const NATIVE_GLOW_CANVAS = SPLASH_GLOW_SIZE + NATIVE_GLOW_EXTRA * 2;
const NATIVE_GLOW_INSET = (NATIVE_GLOW_CANVAS - SPLASH_GLOW_SIZE) / 2;

function GlowBackground() {
  const { height } = useWindowDimensions();

  if (isWeb) {
    return <View style={[styles.webGlow, { filter: `blur(${SPLASH_GLOW_BLUR}px)` } as any]} />;
  }

  return (
    <Svg
      width={NATIVE_GLOW_CANVAS}
      height={NATIVE_GLOW_CANVAS}
      viewBox={`0 0 ${NATIVE_GLOW_CANVAS} ${NATIVE_GLOW_CANVAS}`}
      style={[styles.nativeGlow, { top: height * 0.3 - NATIVE_GLOW_INSET }]}
      pointerEvents="none"
    >
      <Defs>
        <RadialGradient id="splashGlow" cx="50%" cy="50%" rx="50%" ry="50%">
          <Stop offset="0%" stopColor={theme.colors.primary} stopOpacity="0.19" />
          <Stop offset="34%" stopColor={theme.colors.primary} stopOpacity="0.156" />
          <Stop offset="56%" stopColor={theme.colors.primary} stopOpacity="0.102" />
          <Stop offset="78%" stopColor={theme.colors.primary} stopOpacity="0.041" />
          <Stop offset="100%" stopColor={theme.colors.primary} stopOpacity="0" />
        </RadialGradient>
      </Defs>
      <Circle
        cx={NATIVE_GLOW_CANVAS / 2}
        cy={NATIVE_GLOW_CANVAS / 2}
        r={NATIVE_GLOW_CANVAS / 2}
        fill="url(#splashGlow)"
      />
    </Svg>
  );
}

export default function SplashScreen({ navigation }: any) {
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;
  const buttonsAnim = useRef(new Animated.Value(40)).current;
  const buttonsOpacity = useRef(new Animated.Value(0)).current;
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);

  useEffect(() => {
    let isMounted = true;

    const showButtons = () => {
      Animated.parallel([
        Animated.timing(buttonsAnim, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(buttonsOpacity, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
      ]).start();
    };

    const bootstrapSession = async () => {
      try {
        const refreshToken = await authStorage.getRefreshToken();

        if (!refreshToken) {
          clearSession();
          return;
        }

        const tokens = await api.refresh(refreshToken, 'mobile-app');
        await authStorage.saveRefreshToken(tokens.refreshToken);

        const user = await api.getMe(tokens.accessToken);
        setSession(user, tokens.accessToken);

        if (isMounted) {
          navigation.replace('Main');
        }
      } catch (e) {
        console.error(e);
        await authStorage.clearRefreshToken();
        clearSession();
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
          showButtons();
        }
      }
    };

    Animated.parallel([
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(opacityAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start(() => {
      void bootstrapSession();
    });

    return () => {
      isMounted = false;
    };
  }, [buttonsAnim, buttonsOpacity, clearSession, navigation, opacityAnim, scaleAnim, setSession]);

  return (
    <SafeAreaView style={styles.container}>
      <GlowBackground />

      <Animated.View
        style={[
          styles.logoSection,
          { opacity: opacityAnim, transform: [{ scale: scaleAnim }] },
        ]}
      >
        <View style={styles.iconGlowFrame}>
          <View style={[styles.iconBox, webStyles.neonGlow, !isWeb && styles.nativeIconBox]}>
            <Zap color={theme.colors.primary} fill={theme.colors.primary} size={48} />
          </View>
        </View>
        <Text style={styles.title}>EV APP</Text>
        <Text style={styles.subtitle}>
          Smart EV Charging, Optimized for Cost, Time, and Grid Load
        </Text>
      </Animated.View>

      {isCheckingSession ? (
        <ActivityIndicator color={theme.colors.primary} />
      ) : (
        <Animated.View
          style={[
            styles.buttons,
          {
            opacity: buttonsOpacity,
            transform: [{ translateY: buttonsAnim }],
          },
        ]}
      >
        <NeonButton
          buttonStyle={styles.primaryBtn}
          frameStyle={styles.primaryBtnFrame}
          onPress={() => navigation.navigate('Login')}
          activeOpacity={0.85}
        >
          <Text style={styles.primaryBtnText}>Sign In</Text>
        </NeonButton>

        <TouchableOpacity
          style={[styles.secondaryBtn, webStyles.glass]}
          onPress={() => navigation.navigate('Signup')}
          activeOpacity={0.85}
        >
          <Text style={styles.secondaryBtnText}>Create Account</Text>
        </TouchableOpacity>


        </Animated.View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: theme.spacing.lg,
  },
  webGlow: {
    position: 'absolute',
    width: 384,
    height: 384,
    borderRadius: 192,
    backgroundColor: 'rgba(0,255,0,0.2)',
    top: '30%',
    alignSelf: 'center',
  },
  nativeGlow: {
    position: 'absolute',
    width: NATIVE_GLOW_CANVAS,
    height: NATIVE_GLOW_CANVAS,
    alignSelf: 'center',
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 80,
  },
  iconGlowFrame: {
    width: 96,
    height: 96,
    marginBottom: theme.spacing.lg,
    overflow: 'visible',
  },
  iconBox: {
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: theme.colors.surfaceLight,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  nativeIconBox: {
    backgroundColor: '#17191B',
    borderColor: '#333538',
  },
  title: {
    color: theme.colors.text,
    fontSize: 40,
    fontWeight: 'bold',
    letterSpacing: -1,
    marginBottom: theme.spacing.sm,
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: 14,
    textAlign: 'center',
    maxWidth: 250,
    lineHeight: 20,
  },
  buttons: {
    width: '100%',
    gap: theme.spacing.md,
  },
  primaryBtnFrame: {
    width: '100%',
    height: 56,
    marginBottom: theme.spacing.md,
    overflow: 'visible',
  },
  primaryBtn: {
    backgroundColor: theme.colors.primary,
    height: 56,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'visible',
  },
  primaryBtnText: {
    color: '#000',
    fontSize: 18,
    fontWeight: 'bold',
  },
  secondaryBtn: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    height: 56,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: theme.spacing.md,
  },
  secondaryBtnText: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  ghostBtn: {
    height: 56,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ghostBtnText: {
    color: theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '500',
  },
});
