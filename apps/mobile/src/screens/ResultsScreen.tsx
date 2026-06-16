import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { theme, webStyles } from '../theme';
import { getStationMapLocation } from '../data/demoLocations';
import { useSettingsStore } from '../stores/settingsStore';
import { formatCurrencyAmount } from '../utils/preferencesFormat';
import {
  ApiRecommendationOption,
  RootStackParamList,
  UiStationRecommendation,
} from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Results'>;

const asNumber = (value: unknown, fallback = 0) =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;

const asString = (value: unknown, fallback = '') =>
  typeof value === 'string' ? value : fallback;

const asStringArray = (value: unknown) =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];

const getMetadataNumber = (
  metadata: Record<string, unknown> | undefined,
  keys: string[]
) => {
  if (!metadata) return Number.NaN;

  for (const key of keys) {
    const value = metadata[key];

    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }

    if (typeof value === 'string') {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return Number.NaN;
};

const getConnectionType = (chargerLabel: string) => {
  const normalized = chargerLabel.toLowerCase();
  if (normalized.includes('ac')) return 'AC';
  return 'DC';
};

const getSpeedLabel = (chargerLabel: string) => {
  const normalized = chargerLabel.toLowerCase();

  if (normalized.includes('ultra')) return 'Ultra Rapid';
  if (normalized.includes('rapid')) return 'Rapid';
  if (normalized.includes('ac')) return 'Standard';
  return 'Standard';
};

const mapOptionToUiStation = (
  option: ApiRecommendationOption
): UiStationRecommendation => {
  const id = asString(option.station_id, 'unknown_station');
  const name = asString(option.station_name, 'Unknown station');
  const zoneId = asString(option.zone_id, 'unknown_zone');
  const latitude = getMetadataNumber(option.metadata, [
    'latitude',
    'lat',
    'station_latitude',
    'station_lat',
    'charger_latitude',
    'charger_lat',
  ]);
  const longitude = getMetadataNumber(option.metadata, [
    'longitude',
    'lng',
    'lon',
    'station_longitude',
    'station_lng',
    'station_lon',
    'charger_longitude',
    'charger_lng',
    'charger_lon',
  ]);
  const mapLocation = getStationMapLocation({
    stationId: id,
    stationName: name,
    zoneId,
    latitude: Number.isFinite(latitude) ? latitude : null,
    longitude: Number.isFinite(longitude) ? longitude : null,
  });

  return {
    id,
    name,
    zoneId,
    transformerId: asString(option.transformer_id, 'unknown_transformer'),
    distanceKm: asNumber(option.distance_km),
    estimatedWaitMinutes: asNumber(option.estimated_wait_minutes),
    estimatedDurationMinutes: asNumber(option.estimated_duration_minutes),
    estimatedCostGbp: asNumber(option.estimated_cost_gbp),
    headroomKw: asNumber(option.transformer_headroom_kw),
    queueLength: asNumber(option.current_queue),
    utilization: asNumber(option.utilization),
    score: asNumber(option.score),
    chargerLabel: asString(option.metadata?.connector_mix_total, 'rapid'),
    reasonTags: asStringArray(option.reason_tags),
    latitude: mapLocation.isExact ? mapLocation.latitude : null,
    longitude: mapLocation.isExact ? mapLocation.longitude : null,
    address: mapLocation.address,
  };
};

const formatMinutes = (minutes: number) => `${Math.round(asNumber(minutes))} min`;
const formatCurrency = (gbp: number) => `£${asNumber(gbp).toFixed(2)}`;

function StationOptionCard({
  station,
  highlighted = false,
  onPress,
}: {
  station: UiStationRecommendation;
  highlighted?: boolean;
  onPress: () => void;
}) {
  const preferences = useSettingsStore((state) => state.preferences);
  const connectionType = getConnectionType(station.chargerLabel);
  const speedLabel = getSpeedLabel(station.chargerLabel);

  return (
    <TouchableOpacity
      style={[highlighted ? styles.topCard : styles.optionCard, highlighted && webStyles.neonGlow]}
      onPress={onPress}
      activeOpacity={0.85}
    >
      <View style={styles.optionHeader}>
        <Text style={styles.stationName}>{station.name}</Text>
        <Text style={styles.price}>{formatCurrencyAmount(station.estimatedCostGbp, preferences.currency)}</Text>
      </View>

      <View style={styles.optionGrid}>
        <View style={styles.infoPill}>
          <Text style={styles.infoLabel}>CONNECTION</Text>
          <Text style={styles.infoValue}>{connectionType}</Text>
        </View>

        <View style={styles.infoPill}>
          <Text style={styles.infoLabel}>CHARGE TIME</Text>
          <Text style={styles.infoValue}>{formatMinutes(station.estimatedDurationMinutes)}</Text>
        </View>

        <View style={styles.infoPill}>
          <Text style={styles.infoLabel}>SPEED</Text>
          <Text style={styles.infoValue}>{speedLabel}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

export default function ResultsScreen({ navigation, route }: Props) {
  const bundle = route.params?.result ?? null;
  const selectedLocationName = route.params?.selectedLocationName;
  const selectedLocationLatitude = route.params?.selectedLocationLatitude;
  const selectedLocationLongitude = route.params?.selectedLocationLongitude;

  const top =
    bundle?.top_recommendation != null
      ? mapOptionToUiStation(bundle.top_recommendation)
      : null;

  const alternatives = Array.isArray(bundle?.alternatives)
    ? bundle.alternatives.map(mapOptionToUiStation)
    : [];

  if (!bundle) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView contentContainerStyle={styles.container}>
          <View style={styles.topRow}>
            <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
              <ChevronLeft color={theme.colors.text} size={28} />
            </TouchableOpacity>
            <Text style={styles.pageTitle}>Charging Options</Text>
          </View>

          <View style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>No recommendation returned</Text>
            <Text style={styles.emptyText}>Try again.</Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={28} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Charging Options</Text>
        </View>

        {top ? (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>TOP RECOMMENDATION</Text>
            <StationOptionCard
              station={top}
              highlighted
              onPress={() => navigation.navigate('StationDetails', {
                station: top,
                selectedLocationName,
                selectedLocationLatitude,
                selectedLocationLongitude,
              })}
            />
          </View>
        ) : (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>TOP RECOMMENDATION</Text>
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>No top recommendation was returned.</Text>
            </View>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ALTERNATIVES</Text>

          {alternatives.length === 0 ? (
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>No alternatives were returned for this request.</Text>
            </View>
          ) : (
            alternatives.map((station) => (
              <StationOptionCard
                key={station.id}
                station={station}
                onPress={() => navigation.navigate('StationDetails', {
                    station,
                    selectedLocationName,
                    selectedLocationLatitude,
                    selectedLocationLongitude,
                  })}
              />
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 40 },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md, marginBottom: theme.spacing.xl },
  backBtn: { padding: 4 },
  pageTitle: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold' },
  section: { marginBottom: theme.spacing.xl },
  sectionLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.md,
  },
  topCard: {
    backgroundColor: '#121416',
    borderRadius: theme.radii.xxl,
    borderWidth: 2,
    borderColor: theme.colors.primary,
    padding: theme.spacing.lg,
  },
  optionCard: {
    backgroundColor: theme.colors.surfaceLight,
    borderRadius: theme.radii.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: '#222426',
  },
  optionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  stationName: {
    flex: 1,
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: 'bold',
    lineHeight: 24,
  },
  price: {
    color: theme.colors.text,
    fontSize: 22,
    fontWeight: 'bold',
  },
  optionGrid: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    flexWrap: 'wrap',
  },
  infoPill: {
    flex: 1,
    minWidth: 90,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: theme.radii.xl,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoLabel: {
    color: theme.colors.textMuted,
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 4,
  },
  infoValue: {
    color: theme.colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  emptyCard: {
    backgroundColor: theme.colors.surfaceLight,
    borderRadius: theme.radii.xl,
    padding: theme.spacing.lg,
    borderWidth: 1,
    borderColor: '#222426',
  },
  emptyTitle: {
    color: theme.colors.text,
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: theme.spacing.sm,
  },
  emptyText: {
    color: theme.colors.textMuted,
    fontSize: 13,
  },
});