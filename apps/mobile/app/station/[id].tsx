import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Screen, Button } from '@/src/components/ui';
import { colors, spacing, borderRadius } from '@/src/theme';

// Local station details map (only fields needed for details view)
const stationDetails: Record<string, {
  name: string;
  address: string;
  distance: number;
  chargerType: string;
  powerKw: number;
  pricePerKwh: number;
  availableStalls: number;
  totalStalls: number;
  hours: string;
}> = {
  '1': {
    name: 'EcoCharge Downtown',
    address: '123 Main Street, Downtown District',
    distance: 1.2,
    chargerType: 'DC',
    powerKw: 150,
    pricePerKwh: 0.25,
    availableStalls: 2,
    totalStalls: 4,
    hours: '24/7',
  },
  '2': {
    name: 'GreenPower Mall',
    address: '456 Shopping Center Blvd, Level B2',
    distance: 2.8,
    chargerType: 'AC',
    powerKw: 22,
    pricePerKwh: 0.18,
    availableStalls: 3,
    totalStalls: 6,
    hours: '6:00 AM - 11:00 PM',
  },
  '3': {
    name: 'FastVolt Highway',
    address: 'Highway 101, Exit 42 Rest Area',
    distance: 4.5,
    chargerType: 'DC',
    powerKw: 350,
    pricePerKwh: 0.32,
    availableStalls: 1,
    totalStalls: 2,
    hours: '24/7',
  },
  '4': {
    name: 'CityCharge Central',
    address: '789 Central Ave, Parking Garage A',
    distance: 3.1,
    chargerType: 'DC',
    powerKw: 50,
    pricePerKwh: 0.22,
    availableStalls: 4,
    totalStalls: 8,
    hours: '5:00 AM - 12:00 AM',
  },
};

export default function StationDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const station = stationDetails[id ?? ''];

  const handleReserve = () => {
    Alert.alert('Coming Soon', 'Reservation functionality will be available in a future update.');
  };

  if (!station) {
    return (
      <Screen>
        <View style={styles.content}>
          <Text style={styles.errorText}>Station not found</Text>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>{station.name}</Text>

        <View style={styles.badgeRow}>
          <View style={styles.typeBadge}>
            <Text style={styles.typeBadgeText}>{station.chargerType}</Text>
          </View>
          <View style={styles.powerBadge}>
            <Text style={styles.powerBadgeText}>{station.powerKw} kW</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Location</Text>
          <View style={styles.card}>
            <Text style={styles.address}>{station.address}</Text>
            <Text style={styles.distance}>{station.distance} km away</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pricing</Text>
          <View style={styles.card}>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Per kWh</Text>
              <Text style={styles.priceValue}>${station.pricePerKwh.toFixed(2)}</Text>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Availability</Text>
          <View style={styles.card}>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Stalls</Text>
              <Text
                style={[
                  styles.detailValue,
                  station.availableStalls > 0 ? styles.available : styles.unavailable,
                ]}
              >
                {station.availableStalls}/{station.totalStalls} available
              </Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Hours</Text>
              <Text style={styles.detailValue}>{station.hours}</Text>
            </View>
          </View>
        </View>

        <View style={styles.ctaContainer}>
          <Button title="Reserve Spot" onPress={handleReserve} />
        </View>
      </ScrollView>
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
    marginBottom: spacing.md,
  },
  badgeRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing['2xl'],
  },
  typeBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  typeBadgeText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.background,
  },
  powerBadge: {
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  powerBadgeText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  section: {
    marginBottom: spacing.xl,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.lg,
  },
  address: {
    fontSize: 16,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  distance: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.xs,
  },
  detailLabel: {
    fontSize: 14,
    color: colors.textMuted,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textPrimary,
  },
  priceValue: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.primary,
  },
  available: {
    color: colors.success,
  },
  unavailable: {
    color: colors.error,
  },
  ctaContainer: {
    paddingVertical: spacing['2xl'],
  },
  errorText: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: spacing['4xl'],
  },
});
