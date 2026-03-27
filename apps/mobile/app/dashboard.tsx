import { View, Text, StyleSheet, ScrollView } from 'react-native';
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

const mockReservation = {
  stationName: 'PowerHub Downtown',
  date: 'Today',
  time: '4:30 PM',
  estimatedDuration: '45 min',
};

const mockPreferences = {
  optimizationMode: 'Cheapest',
  chargerType: 'DC Fast',
};

export default function DashboardScreen() {
  const router = useRouter();

  const handleFindChargers = () => {
    router.push('/charging-request');
  };

  return (
    <Screen>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
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

        {/* Recent Reservation */}
        <View style={styles.reservationCard}>
          <Text style={styles.sectionTitle}>Next Charge</Text>
          <View style={styles.divider} />
          <View style={styles.reservationDetails}>
            <View style={styles.reservationRow}>
              <Text style={styles.reservationLabel}>Station</Text>
              <Text style={styles.reservationValue}>{mockReservation.stationName}</Text>
            </View>
            <View style={styles.reservationRow}>
              <Text style={styles.reservationLabel}>Time</Text>
              <Text style={styles.reservationValue}>
                {mockReservation.date}, {mockReservation.time}
              </Text>
            </View>
            <View style={styles.reservationRow}>
              <Text style={styles.reservationLabel}>Duration</Text>
              <Text style={styles.reservationValue}>{mockReservation.estimatedDuration}</Text>
            </View>
          </View>
        </View>

        {/* Last Preferences */}
        <View style={styles.preferencesCard}>
          <Text style={styles.sectionTitle}>Last Preferences</Text>
          <View style={styles.divider} />
          <View style={styles.preferencesRow}>
            <View style={styles.preferenceBadge}>
              <Text style={styles.preferenceBadgeText}>{mockPreferences.optimizationMode}</Text>
            </View>
            <View style={styles.preferenceBadge}>
              <Text style={styles.preferenceBadgeText}>{mockPreferences.chargerType}</Text>
            </View>
          </View>
        </View>

        {/* CTA */}
        <View style={styles.ctaContainer}>
          <Button title="Find Chargers" onPress={handleFindChargers} />
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
  },
  content: {
    paddingTop: spacing['2xl'],
    paddingBottom: spacing['3xl'],
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
  reservationCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  preferencesCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing['2xl'],
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginBottom: spacing.md,
  },
  reservationDetails: {
    gap: spacing.sm,
  },
  reservationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  reservationLabel: {
    fontSize: 14,
    color: colors.textMuted,
  },
  reservationValue: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textPrimary,
  },
  preferencesRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  preferenceBadge: {
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.md,
  },
  preferenceBadgeText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.primary,
  },
  ctaContainer: {
    marginTop: spacing['2xl'],
  },
});
