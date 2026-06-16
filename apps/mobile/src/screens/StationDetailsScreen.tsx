import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
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
import { WebView } from 'react-native-webview';
import { NeonButton } from '../components/NeonButton';
import { api } from '../services/api';
import { useSettingsStore } from '../stores/settingsStore';
import { formatCurrencyAmount, formatDistanceKm } from '../utils/preferencesFormat';
import { theme, webStyles } from '../theme';
import { buildGoogleMapsEmbedUrl, getStationMapLocation } from '../data/demoLocations';
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
  latitude: 56.4602,
  longitude: -2.9714,
  address: 'Greenmarket, Dundee',
};

const formatMinutes = (minutes: number) => `${minutes} min`;
const formatCurrency = (gbp: number) => `£${gbp.toFixed(2)}`;
const formatZoneName = (zoneId: string) =>
  zoneId.replace('zone_', '').replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase());

export default function StationDetailsScreen({ navigation, route }: Props) {
  const preferences = useSettingsStore((state) => state.preferences);
  const station = route.params?.station ?? fallbackStation;
  const [exactStationLocation, setExactStationLocation] = useState<{
    latitude: number;
    longitude: number;
    address: string;
    isExact: boolean;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;

    api
      .getStation(station.id)
      .then((apiStation) => {
        if (!isMounted) return;

        setExactStationLocation({
          latitude: apiStation.latitude,
          longitude: apiStation.longitude,
          address:
            apiStation.postcode != null && apiStation.postcode.length > 0
              ? `${apiStation.station_name}, ${apiStation.postcode}`
              : apiStation.station_name,
          isExact: true,
        });
      })
      .catch((error) => {
        console.error('Could not load exact station location', error);
      });

    return () => {
      isMounted = false;
    };
  }, [station.id]);
  const selectedLocationName = route.params?.selectedLocationName;
  const selectedLocationLatitude = route.params?.selectedLocationLatitude;
  const selectedLocationLongitude = route.params?.selectedLocationLongitude;
  const stationLocation =
    exactStationLocation ??
    getStationMapLocation({
      stationId: station.id,
      stationName: station.name,
      zoneId: station.zoneId,
      latitude: station.latitude,
      longitude: station.longitude,
    });
  const destinationLabel = `${station.name}, ${stationLocation.address}`;
  const mapUrl = buildGoogleMapsEmbedUrl(stationLocation);

  return (
    <View style={styles.container}>
      <View style={styles.mapBg}>
        {Platform.OS === 'web' ? (
          <View style={styles.mapImage}>
            {React.createElement('iframe', {
              key: mapUrl,
              src: mapUrl,
              title: `${station.name} map`,
              style: {
                border: 0,
                width: '100%',
                height: '100%',
              },
              loading: 'lazy',
            })}
          </View>
        ) : (
          <WebView
            key={mapUrl}
            source={{ uri: mapUrl }}
            style={styles.mapImage}
            javaScriptEnabled
            domStorageEnabled
          />
        )}

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
            {formatZoneName(station.zoneId)} · {formatDistanceKm(station.distanceKm, preferences.distanceUnit)} away
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
            <Text style={styles.statVal}>{formatCurrencyAmount(station.estimatedCostGbp, preferences.currency)}</Text>
          </View>

          <View style={[styles.statCard, webStyles.glass]}>
            <Activity color={theme.colors.primary} size={20} />
            <Text style={styles.statSub}>HEADROOM</Text>
            <Text style={styles.statVal}>{station.headroomKw.toFixed(0)} kW</Text>
          </View>
        </View>

        <NeonButton
          glow="small"
          buttonStyle={styles.reserveBtn}
          onPress={() =>
            navigation.navigate('ReservationConfirm', {
              station: {
                ...station,
                latitude: stationLocation.latitude,
                longitude: stationLocation.longitude,
                address: stationLocation.address,
              },
              selectedLocationName,
              selectedLocationLatitude,
              selectedLocationLongitude,
            })
          }
          activeOpacity={0.85}
        >
          <Navigation color="#000" size={20} />
          <Text style={styles.reserveBtnText}>Reserve & Navigate</Text>
        </NeonButton>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.surface },
  mapBg: { ...StyleSheet.absoluteFill },
  mapImage: { width: '100%', height: '100%', opacity: 0.82 },
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
  routeOriginText: {
    color: theme.colors.primary,
    fontSize: 12,
    fontWeight: '700',
    marginTop: -theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  coordinateWarningText: {
    color: '#f59e0b',
    fontSize: 11,
    lineHeight: 16,
    marginBottom: theme.spacing.lg,
  },
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
