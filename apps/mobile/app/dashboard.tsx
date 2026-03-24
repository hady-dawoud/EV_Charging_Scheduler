import { View, Text, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Button } from '@/components/ui';
import { colors, spacing, borderRadius } from '@/theme';

// Hardcoded mock data
const mockBattery = {
  percentage: 67,
  range: 180,
};

const mockVehicle = {
  name: 'Tesla Model 3',
  isConnected: true,
};

export default function DashboardScreen() {
  const router = useRouter();

  const handleFindChargers = () => {
    router.push('/charging-request');
  };

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={styles.greeting}>Good evening</Text>

        {/* Battery Status */}
        <View style={styles.batteryCard}>
          <View style={styles.batteryCircle}>
            <Text style={styles.batteryPercentage}>{mockBattery.percentage}%</Text>
            <Text style={styles.batteryLabel}>Battery</Text>
          </View>
          <View style={styles.batteryInfo}>
            <Text style={styles.rangeValue}>{mockBattery.range} km</Text>
            <Text style={styles.rangeLabel}>Estimated Range</Text>
          </View>
        </View>

        {/* Vehicle Status */}
        <View style={styles.vehicleCard}>
          <Text style={styles.vehicleName}>{mockVehicle.name}</Text>
          <View style={styles.statusRow}>
            <View
              style={[
                styles.statusDot,
                mockVehicle.isConnected ? styles.statusConnected : styles.statusDisconnected,
              ]}
            />
            <Text style={styles.statusText}>
              {mockVehicle.isConnected ? 'Connected' : 'Disconnected'}
            </Text>
          </View>
        </View>

        {/* CTA */}
        <View style={styles.ctaContainer}>
          <Button title="Find Chargers" onPress={handleFindChargers} />
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
  greeting: {
    fontSize: 24,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing['2xl'],
  },
  batteryCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing['2xl'],
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  batteryCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 4,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing['2xl'],
  },
  batteryPercentage: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.primary,
  },
  batteryLabel: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  batteryInfo: {
    flex: 1,
  },
  rangeValue: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  rangeLabel: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  vehicleCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing['2xl'],
  },
  vehicleName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: spacing.sm,
  },
  statusConnected: {
    backgroundColor: colors.success,
  },
  statusDisconnected: {
    backgroundColor: colors.error,
  },
  statusText: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  ctaContainer: {
    marginTop: 'auto',
    paddingBottom: spacing['2xl'],
  },
});
