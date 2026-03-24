import { useMemo } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen } from '@/components/ui';
import { colors, spacing, borderRadius } from '@/theme';
import { mockStations } from '@/data/stations';

export default function StationsScreen() {
  const router = useRouter();
  const { targetBattery, optimizationMode, chargerType } = useLocalSearchParams<{
    targetBattery: string;
    optimizationMode: string;
    chargerType: string;
  }>();

  const filteredStations = useMemo(() => {
    // Filter by charger type
    let stations = [...mockStations];
    if (chargerType === 'ac') {
      stations = stations.filter((s) => s.chargerType === 'AC');
    } else if (chargerType === 'dc') {
      stations = stations.filter((s) => s.chargerType === 'DC');
    }

    // Sort by optimization mode
    switch (optimizationMode) {
      case 'cheapest':
        stations.sort((a, b) => a.pricePerKwh - b.pricePerKwh);
        break;
      case 'fastest':
        stations.sort((a, b) => b.powerKw - a.powerKw);
        break;
      case 'closest':
        stations.sort((a, b) => a.distance - b.distance);
        break;
    }

    return stations;
  }, [chargerType, optimizationMode]);

  const getSortLabel = () => {
    switch (optimizationMode) {
      case 'cheapest':
        return 'Sorted by price';
      case 'fastest':
        return 'Sorted by power';
      case 'closest':
        return 'Sorted by distance';
      default:
        return '';
    }
  };

  const getFilterLabel = () => {
    if (chargerType === 'ac') return 'AC';
    if (chargerType === 'dc') return 'DC';
    return '';
  };

  const filterLabel = getFilterLabel();
  const subtitle = `${filteredStations.length} ${filterLabel ? filterLabel + ' ' : ''}stations • ${getSortLabel()}`;

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Nearby Stations</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
      </View>

      <ScrollView style={styles.list} showsVerticalScrollIndicator={false}>
        {filteredStations.map((station) => (
          <Pressable
            key={station.id}
            style={styles.card}
            onPress={() => router.push(`/station/${station.id}`)}
          >
            <View style={styles.cardHeader}>
              <Text style={styles.stationName}>{station.name}</Text>
              <View style={styles.typeBadge}>
                <Text style={styles.typeBadgeText}>{station.chargerType}</Text>
              </View>
            </View>

            <View style={styles.cardDetails}>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Distance</Text>
                <Text style={styles.detailValue}>{station.distance} km</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Price</Text>
                <Text style={styles.detailValue}>${station.pricePerKwh.toFixed(2)}/kWh</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Power</Text>
                <Text style={styles.detailValue}>{station.powerKw} kW</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Available</Text>
                <Text
                  style={[
                    styles.detailValue,
                    station.availableStalls > 0 ? styles.available : styles.unavailable,
                  ]}
                >
                  {station.availableStalls}/{station.totalStalls} stalls
                </Text>
              </View>
            </View>
          </Pressable>
        ))}
        <View style={styles.listFooter} />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: spacing['2xl'],
    paddingBottom: spacing.lg,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  list: {
    flex: 1,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  stationName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.textPrimary,
    flex: 1,
  },
  typeBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  typeBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.background,
  },
  cardDetails: {
    gap: spacing.sm,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
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
  available: {
    color: colors.success,
  },
  unavailable: {
    color: colors.error,
  },
  listFooter: {
    height: spacing['2xl'],
  },
});
