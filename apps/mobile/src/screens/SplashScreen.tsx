import React, { useRef, useEffect, useState } from 'react';
import zapRouteLogo from '../assets/branding/zaproute-logo-wide.png';
import type { ImageSourcePropType } from 'react-native';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Platform,
  ActivityIndicator,
  useWindowDimensions,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle, Defs, RadialGradient, Stop } from 'react-native-svg';
import { NeonButton } from '../components/NeonButton';
import { theme, webStyles } from '../theme';
import { api } from '../services/api';
import { authStorage } from '../services/authStorage';
import { useAuthStore } from '../stores/authStore';

const isWeb = Platform.OS === 'web';
const zapRouteLogoSource: ImageSourcePropType =
  Platform.OS === 'web'
    ? { uri: zapRouteLogo as string }
    : (zapRouteLogo as unknown as ImageSourcePropType);
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
        <Image
          source={zapRouteLogoSource}
          style={styles.splashLogo}
          resizeMode="contain"
        />
        <View style={styles.taglinePill}>
          <Text style={styles.taglineText}>TAP. ZAP. GO.</Text>
        </View>
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
  splashLogo: {
    width: 320,
    height: 120,
    marginBottom: theme.spacing.md,
  },
  taglinePill: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(144, 254, 127, 0.34)',
    backgroundColor: 'rgba(14, 35, 32, 0.72)',
    marginTop: theme.spacing.xs,
  },
  taglineText: {
    color: theme.colors.primary,
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 2.2,
    textTransform: 'uppercase',
  },
  iconGlowFrame: {
    width: 96,
    height: 96,
    marginBottom: theme.spacing.lg,
    overflow: 'visible',
  },
  iconShadow: {
    width: 96,
    height: 96,
    borderRadius: 28,
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
    backgroundColor: '#102317',
    borderColor: 'rgba(54, 92, 58, 0.72)',
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
