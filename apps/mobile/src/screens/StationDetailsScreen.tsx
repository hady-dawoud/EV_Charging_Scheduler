import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  ChevronLeft,
  Navigation,
  Zap,
  Clock,
  DollarSign,
  Activity,
} from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { theme, webStyles } from '../theme';
import { RootStackParamList, UiStationRecommendation } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'StationDetails'>;

const fallbackStation: UiStationRecommendation = {
  id: 'fallback_station',
  name: 'Greenmarket 150kW Bus Charger',
  zoneId: 'zone_central_waterfront',
  transformerId: 'tx_central_market',
  distanceKm: 0.5,
  estimatedWaitMinutes: 0,
  estimatedDurationMinutes: 15,
  estimatedCostGbp: 4.59,
  headroomKw: 379.073,
  queueLength: 0,
  utilization: 0,
  score: 0.7521,
  chargerLabel: 'ultra_rapid',
  reasonTags: ['nearby', 'low_wait', 'high_headroom', 'low_cost'],
};

const formatDistance = (km: number) => `${km.toFixed(1)} km`;
const formatMinutes = (minutes: number) => `${minutes} min`;
const formatCurrency = (gbp: number) => `£${gbp.toFixed(2)}`;
const formatZoneName = (zoneId: string) =>
  zoneId.replace('zone_', '').replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase());

export default function StationDetailsScreen({ navigation, route }: Props) {
  const station = route.params?.station ?? fallbackStation;

  return (
    <View style={styles.container}>
      <View style={styles.mapBg}>
        <Image
          source={{ uri: 'https://picsum.photos/seed/map-dark/800/1200' }}
          style={styles.mapImage}
          blurRadius={2}
        />
        <View style={styles.mapOverlay} />
        <View style={styles.markerWrapper}>
          <View style={styles.markerPing} />
          <View style={[styles.markerIcon, webStyles.neonGlow]}>
            <Zap color={theme.colors.primary} fill={theme.colors.primary} size={20} />
          </View>
          <View style={[styles.markerLabel, webStyles.glass]}>
            <Text style={styles.markerText}>{station.name}</Text>
          </View>
        </View>
      </View>

      <SafeAreaView style={styles.topNav}>
        <TouchableOpacity style={[styles.navBtn, webStyles.glass]} onPress={() => navigation.goBack()}>
          <ChevronLeft color={theme.colors.text} size={24} />
        </TouchableOpacity>
        <View style={[styles.navTitle, webStyles.glass]}>
          <Text style={styles.navTitleText}>Station Details</Text>
        </View>
        <View style={{ width: 40 }} />
      </SafeAreaView>

      <View style={[styles.sheet, webStyles.glass]}>
        <View style={styles.sheetHandle} />

        <Text style={styles.stationName}>{station.name}</Text>
        <View style={styles.providerRow}>
          <Navigation color={theme.colors.textMuted} fill={theme.colors.textMuted} size={13} />
          <Text style={styles.providerText}>
            {formatZoneName(station.zoneId)} · {formatDistance(station.distanceKm)} away
          </Text>
        </View>

        <View style={styles.statsGrid}>
          <View style={[styles.statCard, webStyles.glass]}>
            <Clock color="#60a5fa" size={20} />
            <Text style={styles.statSub}>WAIT</Text>
            <Text style={styles.statVal}>{formatMinutes(station.estimatedWaitMinutes)}</Text>
          </View>

          <View style={[styles.statCard, webStyles.glass]}>
            <DollarSign color="#eab308" size={20} />
            <Text style={styles.statSub}>EST. COST</Text>
            <Text style={styles.statVal}>{formatCurrency(station.estimatedCostGbp)}</Text>
          </View>

          <View style={[styles.statCard, webStyles.glass]}>
            <Activity color={theme.colors.primary} size={20} />
            <Text style={styles.statSub}>HEADROOM</Text>
            <Text style={styles.statVal}>{station.headroomKw.toFixed(0)} kW</Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.reserveBtn, webStyles.neonGlowSmall]}
          onPress={() => navigation.navigate('ReservationConfirm')}
          activeOpacity={0.85}
        >
          <Navigation color="#000" size={20} />
          <Text style={styles.reserveBtnText}>Reserve & Navigate</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.surface },
  mapBg: { ...StyleSheet.absoluteFillObject },
  mapImage: { width: '100%', height: '100%', opacity: 0.4 },
  mapOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(10,11,13,0.3)' },
  markerWrapper: {
    position: 'absolute',
    top: '33%',
    left: '50%',
    transform: [{ translateX: -24 }, { translateY: -24 }],
    alignItems: 'center',
  },
  markerPing: {
    position: 'absolute',
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(0,255,0,0.2)',
  },
  markerIcon: {
    ...theme.neonGlow,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: theme.colors.background,
    borderWidth: 2,
    borderColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  markerLabel: {
    marginTop: 8,
    backgroundColor: 'rgba(10,11,13,0.8)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  markerText: { color: theme.colors.primary, fontSize: 10, fontWeight: 'bold', letterSpacing: 0.5 },
  topNav: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.sm,
  },
  navBtn: {
    ...theme.glass,
    width: 40,
    height: 40,
    borderRadius: theme.radii.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navTitle: {
    ...theme.glass,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: theme.radii.lg,
  },
  navTitleText: { color: theme.colors.text, fontWeight: 'bold', fontSize: 14 },
  sheet: {
    ...theme.glassDark,
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    padding: theme.spacing.xl,
    paddingBottom: 48,
  },
  sheetHandle: {
    width: 48,
    height: 4,
    backgroundColor: theme.colors.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: theme.spacing.xl,
  },
  stationName: { color: theme.colors.text, fontSize: 28, fontWeight: 'bold', marginBottom: 6 },
  providerRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: theme.spacing.xl },
  providerText: { color: theme.colors.textMuted, fontSize: 13, fontWeight: '500' },
  statsGrid: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.xl },
  statCard: {
    ...theme.glass,
    flex: 1,
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.md,
    alignItems: 'center',
    gap: 6,
  },
  statSub: { color: theme.colors.textMuted, fontSize: 9, fontWeight: 'bold', letterSpacing: 1 },
  statVal: { color: theme.colors.text, fontSize: 16, fontWeight: 'bold', textAlign: 'center' },
  reserveBtn: {
    ...theme.neonGlowSmall,
    height: 56,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.sm,
  },
  reserveBtnText: { color: '#000', fontSize: 18, fontWeight: 'bold' },
});