import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Zap, Car } from 'lucide-react-native';
import Svg, { Circle } from 'react-native-svg';
import { NeonButton } from '../components/NeonButton';
import { theme, webStyles } from '../theme';
import { fallbackVehicle, useVehicleStore } from '../stores/vehicleStore';

const isWeb = Platform.OS === 'web';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

export default function HomeScreen({ navigation }: any) {
  const vehicle = useVehicleStore((state) => state.vehicle);
  const loadVehicle = useVehicleStore((state) => state.loadVehicle);
  const activeVehicle = vehicle ?? fallbackVehicle;
  const batteryProgress = Math.max(0, Math.min(100, activeVehicle.currentSoC)) / 100;

  useEffect(() => {
    loadVehicle();
  }, [loadVehicle]);

  const RADIUS = 96;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
  const SVG_SIZE = 220;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logo}>
            <Zap color={theme.colors.primary} fill={theme.colors.primary} size={28} />
            <Text style={styles.logoText}>EV APP</Text>
          </View>
          <View style={styles.badge}>
            <View style={[styles.badgeDot, webStyles.neonGlowSmall]} />
            <Text style={styles.badgeText}>Vehicle Connected</Text>
          </View>
        </View>

        {/* Battery Ring */}
        <View style={styles.ringWrapper}>
          <View style={styles.outerRing} />
          <View style={isWeb ? { filter: 'drop-shadow(0 0 10px rgba(0,255,0,0.6))' } as any : styles.nativeRingGlowFrame}>
            <Svg width={SVG_SIZE} height={SVG_SIZE} viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}>
              <Circle
                cx={SVG_SIZE / 2}
                cy={SVG_SIZE / 2}
                r={RADIUS}
                fill="transparent"
                stroke="rgba(0,255,0,0.2)"
                strokeWidth={10}
              />

              {!isWeb ? (
                <>
                  <Circle
                    cx={SVG_SIZE / 2}
                    cy={SVG_SIZE / 2}
                    r={RADIUS}
                    fill="transparent"
                    stroke="rgba(0,255,0,0.10)"
                    strokeWidth={24}
                    strokeDasharray={CIRCUMFERENCE}
                    strokeDashoffset={CIRCUMFERENCE * (1 - batteryProgress)}
                    strokeLinecap="round"
                    rotation="-90"
                    origin={`${SVG_SIZE / 2}, ${SVG_SIZE / 2}`}
                  />
                  <Circle
                    cx={SVG_SIZE / 2}
                    cy={SVG_SIZE / 2}
                    r={RADIUS}
                    fill="transparent"
                    stroke="rgba(0,255,0,0.18)"
                    strokeWidth={16}
                    strokeDasharray={CIRCUMFERENCE}
                    strokeDashoffset={CIRCUMFERENCE * (1 - batteryProgress)}
                    strokeLinecap="round"
                    rotation="-90"
                    origin={`${SVG_SIZE / 2}, ${SVG_SIZE / 2}`}
                  />
                </>
              ) : null}

              <Circle
                cx={SVG_SIZE / 2}
                cy={SVG_SIZE / 2}
                r={RADIUS}
                fill="transparent"
                stroke={theme.colors.primary}
                strokeWidth={10}
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={CIRCUMFERENCE * (1 - batteryProgress)}
                strokeLinecap="round"
                rotation="-90"
                origin={`${SVG_SIZE / 2}, ${SVG_SIZE / 2}`}
              />
            </Svg>
          </View>
          <View style={styles.ringInner}>
            <Text style={styles.batteryPct}>{Math.round(activeVehicle.currentSoC)}%</Text>
            <Text style={styles.batteryRange}>~{Math.round(activeVehicle.rangeLeft)} km range</Text>
          </View>
        </View>

        {/* Connected Vehicle */}
        <View style={[styles.vehicleCard, webStyles.glass]}>
          <Text style={styles.cardLabel}>CONNECTED VEHICLE</Text>
          <View style={styles.vehicleRow}>
            <View style={styles.vehicleIcon}>
              <Car color={theme.colors.primary} size={24} />
            </View>
            <View style={styles.vehicleInfo}>
              <Text style={styles.vehicleName}>{activeVehicle.make} {activeVehicle.model}</Text>
              <Text style={styles.vehicleSub}>{activeVehicle.batteryCapacity} kWh Battery</Text>
            </View>
          </View>
        </View>

        {/* CTA */}
        <NeonButton
          buttonStyle={styles.primaryBtn}
          onPress={() => navigation.navigate('ChargingRequest')}
          activeOpacity={0.85}
        >
          <Zap color="#000" fill="#000" size={20} />
          <Text style={styles.primaryBtnText}>Find Chargers</Text>
        </NeonButton>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: {
    flex: 1,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    paddingBottom: theme.spacing.lg,
    alignItems: 'center',
  },
  header: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xl,
  },
  logo: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm },
  logoText: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold' },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceLight,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: theme.radii.full,
    borderWidth: 1,
    borderColor: '#333538',
    gap: 6,
  },
  badgeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.primary,
  },
  badgeText: { color: theme.colors.textMuted, fontSize: 11, fontWeight: '600' },
  ringWrapper: {
    width: 220,
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
    borderRadius: 110,
  },
  outerRing: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    borderWidth: 10,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  nativeRingGlowFrame: {
    width: 220,
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringInner: {
    position: 'absolute',
    alignItems: 'center',
  },
  batteryPct: { color: theme.colors.text, fontSize: 48, fontWeight: 'bold' },
  batteryRange: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2 },
  vehicleCard: {
    ...theme.glass,
    width: '100%',
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  cardLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.md,
  },
  vehicleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
  },
  vehicleIcon: {
    width: 48,
    height: 48,
    borderRadius: theme.radii.md,
    backgroundColor: 'rgba(0,255,0,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  vehicleInfo: {
    flex: 1,
  },
  vehicleName: {
    color: theme.colors.text,
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  vehicleSub: {
    color: theme.colors.textMuted,
    fontSize: 12,
  },
  vehicleSoc: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(0,255,0,0.1)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: theme.radii.full,
  },
  vehicleSocText: {
    color: theme.colors.primary,
    fontSize: 13,
    fontWeight: 'bold',
  },
  primaryBtn: {
    width: '100%',
    height: 56,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.sm,
  },
  primaryBtnText: { color: '#000', fontSize: 18, fontWeight: 'bold' },
});
