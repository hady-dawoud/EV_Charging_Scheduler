import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { theme, webStyles } from '../theme';
import { api } from '../services/api';

const MESSAGES = [
  'Checking station telemetry...',
  'Evaluating grid constraints...',
  'Forecasting demand...',
  'Ranking best charging options...',
];

export default function LoadingRecommendationsScreen({ navigation }: any) {
  const [msgIndex, setMsgIndex] = useState(0);
  const rot1 = useRef(new Animated.Value(0)).current;
  const rot2 = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(1)).current;
  const msgOpacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Spinning rings
    Animated.loop(
      Animated.timing(rot1, { toValue: 1, duration: 8000, useNativeDriver: true })
    ).start();
    Animated.loop(
      Animated.timing(rot2, { toValue: -1, duration: 12000, useNativeDriver: true })
    ).start();
    // Pulse
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.15, duration: 800, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();

    // Cycle messages
    const interval = setInterval(() => {
      Animated.timing(msgOpacity, { toValue: 0, duration: 200, useNativeDriver: true }).start(() => {
        setMsgIndex((p) => (p + 1) % MESSAGES.length);
        Animated.timing(msgOpacity, { toValue: 1, duration: 200, useNativeDriver: true }).start();
      });
    }, 800);

    // Fetch and navigate
    api.getRecommendations().then(() => navigation.replace('Results'));

    return () => clearInterval(interval);
  }, []);

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

      <Text style={styles.title}>Optimizing Route</Text>
      <Animated.Text style={[styles.message, { opacity: msgOpacity }]}>
        {MESSAGES[msgIndex]}
      </Animated.Text>
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
  },
  message: {
    color: theme.colors.primary,
    fontFamily: 'monospace',
    fontSize: 13,
    textAlign: 'center',
  },
});
