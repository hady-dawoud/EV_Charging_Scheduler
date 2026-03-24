import { useState } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Button } from '@/src/components/ui';
import { colors, spacing, borderRadius } from '@/src/theme';

type OptimizationMode = 'cheapest' | 'fastest' | 'closest';
type ChargerType = 'ac' | 'dc' | 'any';

const OPTIMIZATION_OPTIONS: { value: OptimizationMode; label: string }[] = [
  { value: 'cheapest', label: 'Cheapest' },
  { value: 'fastest', label: 'Fastest' },
  { value: 'closest', label: 'Closest' },
];

const CHARGER_OPTIONS: { value: ChargerType; label: string }[] = [
  { value: 'ac', label: 'AC' },
  { value: 'dc', label: 'DC' },
  { value: 'any', label: 'Any' },
];

const CURRENT_BATTERY = 67;

export default function ChargingRequestScreen() {
  const router = useRouter();
  const [targetBattery, setTargetBattery] = useState(80);
  const [optimizationMode, setOptimizationMode] = useState<OptimizationMode>('cheapest');
  const [chargerType, setChargerType] = useState<ChargerType>('any');

  const handleFindStations = () => {
    router.push({
      pathname: '/stations',
      params: {
        targetBattery: targetBattery.toString(),
        optimizationMode,
        chargerType,
      },
    });
  };

  const adjustTarget = (delta: number) => {
    setTargetBattery((prev) => Math.max(CURRENT_BATTERY + 5, Math.min(100, prev + delta)));
  };

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={styles.title}>Charging Request</Text>

        {/* Battery Levels */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Current Battery</Text>
          <View style={styles.batteryDisplay}>
            <Text style={styles.batteryValue}>{CURRENT_BATTERY}%</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Target Battery</Text>
          <View style={styles.targetSelector}>
            <Pressable
              style={styles.adjustButton}
              onPress={() => adjustTarget(-5)}
            >
              <Text style={styles.adjustButtonText}>−</Text>
            </Pressable>
            <Text style={styles.targetValue}>{targetBattery}%</Text>
            <Pressable
              style={styles.adjustButton}
              onPress={() => adjustTarget(5)}
            >
              <Text style={styles.adjustButtonText}>+</Text>
            </Pressable>
          </View>
        </View>

        {/* Optimization Mode */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Optimize For</Text>
          <View style={styles.segmentedControl}>
            {OPTIMIZATION_OPTIONS.map((option) => (
              <Pressable
                key={option.value}
                style={[
                  styles.segment,
                  optimizationMode === option.value && styles.segmentActive,
                ]}
                onPress={() => setOptimizationMode(option.value)}
              >
                <Text
                  style={[
                    styles.segmentText,
                    optimizationMode === option.value && styles.segmentTextActive,
                  ]}
                >
                  {option.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Charger Type */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Charger Type</Text>
          <View style={styles.segmentedControl}>
            {CHARGER_OPTIONS.map((option) => (
              <Pressable
                key={option.value}
                style={[
                  styles.segment,
                  chargerType === option.value && styles.segmentActive,
                ]}
                onPress={() => setChargerType(option.value)}
              >
                <Text
                  style={[
                    styles.segmentText,
                    chargerType === option.value && styles.segmentTextActive,
                  ]}
                >
                  {option.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Submit */}
        <View style={styles.ctaContainer}>
          <Button title="Find Stations" onPress={handleFindStations} />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    paddingTop: spacing['2xl'],
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing['3xl'],
  },
  section: {
    marginBottom: spacing['2xl'],
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  batteryDisplay: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    alignItems: 'center',
  },
  batteryValue: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  targetSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
  },
  adjustButton: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.surfaceLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  adjustButtonText: {
    fontSize: 24,
    fontWeight: '600',
    color: colors.primary,
  },
  targetValue: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.primary,
    marginHorizontal: spacing['3xl'],
  },
  segmentedControl: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.xs,
  },
  segment: {
    flex: 1,
    paddingVertical: spacing.md,
    alignItems: 'center',
    borderRadius: borderRadius.sm,
  },
  segmentActive: {
    backgroundColor: colors.primary,
  },
  segmentText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  segmentTextActive: {
    color: colors.background,
  },
  ctaContainer: {
    marginTop: 'auto',
    paddingBottom: spacing['2xl'],
  },
});
