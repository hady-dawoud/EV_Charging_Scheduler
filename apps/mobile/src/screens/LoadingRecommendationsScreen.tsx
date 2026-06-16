import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { theme, webStyles } from '../theme';
import { api } from '../services/api';
import { RootStackParamList } from '../types';

const MESSAGES = [
  'Checking station telemetry...',
  'Evaluating grid constraints...',
  'Forecasting demand...',
  'Ranking best charging options...',
];

type Props = NativeStackScreenProps<
  RootStackParamList,
  'LoadingRecommendations'
>;

export default function LoadingRecommendationsScreen({
  navigation,
  route,
}: Props) {
  const [msgIndex, setMsgIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const rot1 = useRef(new Animated.Value(0)).current;
  const rot2 = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(1)).current;
  const msgOpacity = useRef(new Animated.Value(1)).current;

  const request = route.params.request;

  useEffect(() => {
    Animated.loop(
      Animated.timing(rot1, { toValue: 1, duration: 8000, useNativeDriver: true })
    ).start();

    Animated.loop(
      Animated.timing(rot2, { toValue: -1, duration: 12000, useNativeDriver: true })
    ).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.15, duration: 800, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();

    const interval = setInterval(() => {
      Animated.timing(msgOpacity, { toValue: 0, duration: 200, useNativeDriver: true }).start(() => {
        setMsgIndex((p) => (p + 1) % MESSAGES.length);
        Animated.timing(msgOpacity, { toValue: 1, duration: 200, useNativeDriver: true }).start();
      });
    }, 800);

    api
      .getRecommendations(request)
      .then((result) => {
        console.log('Recommendations API result:', result);
        navigation.replace('Results', {
          result,
          selectedLocationName: request.locationName,
          selectedLocationLatitude: request.latitude,
          selectedLocationLongitude: request.longitude,
        });
      })
      .catch((err) => {
        const message =
          err instanceof Error ? err.message : 'Failed to load recommendations.';
        setError(message);
      });

    return () => clearInterval(interval);
  }, [navigation, msgOpacity, pulse, request, rot1, rot2]);

  const spin1 = rot1.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const spin2 = rot2.interpolate({ inputRange: [-1, 0], outputRange: ['-360deg', '0deg'] });

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.orbitArea}>
        <Animated.View style={[styles.ring1, { transform: [{ rotate: spin1 }] }]} />
        <Animated.View style={[styles.ring2, { transform: [{ rotate: spin2 }] }]} />
        <Animated.View style={[styles.innerGlow, { transform: [{ scale: pulse }] }]} />
        <View style={[styles.core, webStyles.neonGlowIntense]}>
          <View style={styles.coreInner} />
        </View>
      </View>

      <Text style={styles.title}>
        {error ? 'Could not Load Recommendations' : 'Optimizing Route'}
      </Text>

      {!error ? (
        <Animated.Text style={[styles.message, { opacity: msgOpacity }]}>
          {MESSAGES[msgIndex]}
        </Animated.Text>
      ) : (
        <>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => navigation.replace('ChargingRequest')}
            activeOpacity={0.85}
          >
            <Text style={styles.retryButtonText}>Back to Request</Text>
          </TouchableOpacity>
        </>
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
  orbitArea: {
    width: 192,
    height: 192,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.xxl,
  },
  ring1: {
    position: 'absolute',
    width: 192,
    height: 192,
    borderRadius: 96,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: 'rgba(0,255,0,0.3)',
  },
  ring2: {
    position: 'absolute',
    width: 160,
    height: 160,
    borderRadius: 80,
    borderWidth: 1,
    borderColor: 'rgba(0,255,0,0.2)',
  },
  innerGlow: {
    position: 'absolute',
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(0,255,0,0.1)',
  },
  core: {
    ...theme.neonGlowIntense,
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  coreInner: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#000',
  },
  title: {
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: theme.spacing.md,
    textAlign: 'center',
  },
  message: {
    color: theme.colors.primary,
    fontFamily: 'monospace',
    fontSize: 13,
    textAlign: 'center',
  },
  errorText: {
    color: '#f87171',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: theme.spacing.lg,
  },
  retryButton: {
    height: 48,
    paddingHorizontal: theme.spacing.xl,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  retryButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
});