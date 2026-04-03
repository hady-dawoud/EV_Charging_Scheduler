import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen, Button } from '@/components/ui';
import { colors, spacing, borderRadius } from '@/theme';
import { mockStations } from '@/data/stations';

export default function StationDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const station = mockStations.find((s) => s.id === id);

  const handleReserve = () => {
    if (station) {
      router.push({
        pathname: '/reservation-confirmation',
        params: { stationName: station.name },
      });
    }
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
    paddingBottom: spacing['2xl'],
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
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.accent,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.md,
  },
  typeBadgeText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.accent,
  },
  powerBadge: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.md,
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
    fontSize: 10,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 2,
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: borderRadius.xl,
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
    color: colors.accent,
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
