import React, { useRef, useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Zap } from 'lucide-react-native';
import { theme, webStyles } from '../theme';
import { api } from '../services/api';
import { authStorage } from '../services/authStorage';
import { useAuthStore } from '../stores/authStore';

const { width } = Dimensions.get('window');
const isWeb = Platform.OS === 'web';

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
      {/* Glow background */}
      <View style={[styles.glow, isWeb ? { filter: 'blur(100px)' } as any : {}]} />

      <Animated.View
        style={[
          styles.logoSection,
          { opacity: opacityAnim, transform: [{ scale: scaleAnim }] },
        ]}
      >
        <View style={[styles.iconBox, webStyles.neonGlow]}>
          <Zap color={theme.colors.primary} fill={theme.colors.primary} size={48} />
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
        <TouchableOpacity
          style={[styles.primaryBtn, webStyles.neonGlow]}
          onPress={() => navigation.navigate('Login')}
          activeOpacity={0.85}
        >
          <Text style={styles.primaryBtnText}>Sign In</Text>
        </TouchableOpacity>

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
  glow: {
    position: 'absolute',
    width: 384,
    height: 384,
    borderRadius: 192,
    backgroundColor: 'rgba(0,255,0,0.2)',
    top: '30%',
    alignSelf: 'center',
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 80,
  },
  iconBox: {
    ...theme.neonGlow,
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: theme.colors.surfaceLight,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
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
  primaryBtn: {
    backgroundColor: theme.colors.primary,
    height: 56,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
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
