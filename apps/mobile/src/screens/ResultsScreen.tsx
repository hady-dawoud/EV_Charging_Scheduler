import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Navigation, Zap, Clock } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { theme, webStyles } from '../theme';
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

const mapOptionToUiStation = (
  option: ApiRecommendationOption
): UiStationRecommendation => ({
  id: asString(option.station_id, 'unknown_station'),
  name: asString(option.station_name, 'Unknown station'),
  zoneId: asString(option.zone_id, 'unknown_zone'),
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
});

const formatDistance = (km: number) => `${asNumber(km).toFixed(1)} km`;
const formatMinutes = (minutes: number) => `${Math.round(asNumber(minutes))} min`;
const formatCurrency = (gbp: number) => `£${asNumber(gbp).toFixed(2)}`;
const formatPercent = (value: number) => `${Math.round(asNumber(value) * 100)}%`;

export default function ResultsScreen({ navigation, route }: Props) {
  const bundle = route.params?.result ?? null;

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
            <Text style={styles.emptyTitle}>No recommendation bundle returned</Text>
            <Text style={styles.emptyText}>
              The API call succeeded, but the app did not receive a usable recommendation object.
            </Text>
            <Text style={styles.debugLabel}>Raw result</Text>
            <Text style={styles.debugText}>
              {JSON.stringify(bundle, null, 2)}
            </Text>
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

        {bundle.debug_reasoning_summary ? (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>LIVE RUNTIME SUMMARY</Text>
            <Text style={styles.summaryText}>{bundle.debug_reasoning_summary}</Text>
          </View>
        ) : null}

        {top ? (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>TOP RECOMMENDATION</Text>
            <TouchableOpacity
              style={[styles.topCard, webStyles.neonGlow]}
              onPress={() => navigation.navigate('StationDetails', { station: top })}
              activeOpacity={0.85}
            >
              <View style={styles.topCardHeader}>
                <View style={{ flex: 1 }}>
                  <View style={styles.badgeRow}>
                    <Zap color={theme.colors.primary} fill={theme.colors.primary} size={12} />
                    <Text style={styles.badgeText}>LIVE RECOMMENDATION</Text>
                  </View>
                  <Text style={styles.stationName}>{top.name}</Text>
                  <Text style={styles.stationSub}>
                    {top.chargerLabel} · {formatDistance(top.distanceKm)} away
                  </Text>
                </View>
                <Text style={styles.price}>{formatCurrency(top.estimatedCostGbp)}</Text>
              </View>

              <View style={styles.statsRow}>
                <View style={styles.statBox}>
                  <Clock color={theme.colors.textMuted} size={20} />
                  <View>
                    <Text style={styles.statValue}>
                      {formatMinutes(top.estimatedDurationMinutes)}
                    </Text>
                    <Text style={styles.statSub}>CHARGE TIME</Text>
                  </View>
                </View>

                <View style={styles.statBox}>
                  <Navigation color={theme.colors.textMuted} size={20} />
                  <View>
                    <Text style={styles.statValue}>
                      {formatMinutes(top.estimatedWaitMinutes)}
                    </Text>
                    <Text style={styles.statSub}>WAIT TIME</Text>
                  </View>
                </View>
              </View>

              <View style={styles.statsRow}>
                <View style={styles.statBox}>
                  <Zap color={theme.colors.textMuted} size={20} />
                  <View>
                    <Text style={styles.statValue}>
                      {asNumber(top.headroomKw).toFixed(0)} kW
                    </Text>
                    <Text style={styles.statSub}>HEADROOM</Text>
                  </View>
                </View>

                <View style={styles.statBox}>
                  <Zap color={theme.colors.textMuted} size={20} />
                  <View>
                    <Text style={styles.statValue}>{formatPercent(top.utilization)}</Text>
                    <Text style={styles.statSub}>UTILIZATION</Text>
                  </View>
                </View>
              </View>
            </TouchableOpacity>
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
              <TouchableOpacity
                key={station.id}
                style={styles.altCard}
                onPress={() => navigation.navigate('StationDetails', { station })}
                activeOpacity={0.85}
              >
                <View style={styles.altHeader}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.altName}>{station.name}</Text>
                    <Text style={styles.altSub}>{station.chargerLabel}</Text>
                  </View>
                  <Text style={styles.altPrice}>
                    {formatCurrency(station.estimatedCostGbp)}
                  </Text>
                </View>

                <View style={styles.altMeta}>
                  <View style={styles.metaItem}>
                    <Clock color={theme.colors.textMuted} size={13} />
                    <Text style={styles.metaText}>
                      {formatMinutes(station.estimatedDurationMinutes)}
                    </Text>
                  </View>

                  <View style={styles.dot} />

                  <View style={styles.metaItem}>
                    <Navigation color={theme.colors.textMuted} fill={theme.colors.textMuted} size={13} />
                    <Text style={styles.metaText}>{formatDistance(station.distanceKm)}</Text>
                  </View>

                  <View style={styles.dot} />

                  <View style={styles.metaItem}>
                    <Zap color={theme.colors.primary} fill={theme.colors.primary} size={13} />
                    <Text style={styles.metaText}>
                      wait {formatMinutes(station.estimatedWaitMinutes)}
                    </Text>
                  </View>
                </View>
              </TouchableOpacity>
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
  summaryCard: {
    backgroundColor: theme.colors.surfaceLight,
    borderRadius: theme.radii.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.xl,
    borderWidth: 1,
    borderColor: '#222426',
  },
  summaryLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.sm,
  },
  summaryText: {
    color: theme.colors.text,
    fontSize: 13,
    lineHeight: 20,
  },
  section: { marginBottom: theme.spacing.xl },
  sectionLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.md,
  },
  topCard: {
    ...theme.neonGlow,
    backgroundColor: '#121416',
    borderRadius: theme.radii.xxl,
    borderWidth: 2,
    borderColor: theme.colors.primary,
    padding: theme.spacing.lg,
  },
  topCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
  badgeText: { color: theme.colors.primary, fontSize: 10, fontWeight: 'bold', letterSpacing: 1 },
  stationName: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold', marginBottom: 2 },
  stationSub: { color: theme.colors.textMuted, fontSize: 12 },
  price: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold' },
  statsRow: { flexDirection: 'row', gap: theme.spacing.md, marginBottom: theme.spacing.md },
  statBox: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: theme.radii.xl,
    padding: theme.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
  },
  statValue: { color: theme.colors.text, fontSize: 14, fontWeight: 'bold' },
  statSub: { color: theme.colors.textMuted, fontSize: 9, fontWeight: 'bold', letterSpacing: 1 },
  altCard: {
    backgroundColor: theme.colors.surfaceLight,
    borderRadius: theme.radii.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: '#222426',
  },
  altHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  altName: { color: theme.colors.text, fontSize: 15, fontWeight: 'bold' },
  altSub: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2 },
  altPrice: { color: '#d1d5db', fontSize: 14, fontWeight: 'bold' },
  altMeta: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, flexWrap: 'wrap' },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { color: theme.colors.textMuted, fontSize: 12, fontWeight: '500' },
  dot: { width: 4, height: 4, borderRadius: 2, backgroundColor: '#374151' },
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
  emptyText: { color: theme.colors.textMuted, fontSize: 13, marginBottom: theme.spacing.md },
  debugLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 6,
  },
  debugText: {
    color: theme.colors.text,
    fontSize: 11,
    lineHeight: 16,
  },
});