import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Navigation, Zap, Battery, DollarSign } from 'lucide-react-native';
import { mockStations } from '../data/mockData';
import { theme, webStyles } from '../theme';

const { height } = Dimensions.get('window');
const station = mockStations[0];

export default function StationDetailsScreen({ navigation }: any) {
  return (
    <View style={styles.container}>
      {/* Map Background */}
      <View style={styles.mapBg}>
        <Image
          source={{ uri: 'https://picsum.photos/seed/map-dark/800/1200' }}
          style={styles.mapImage}
          blurRadius={2}
        />
        <View style={styles.mapOverlay} />
        {/* Station Marker */}
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

      {/* Top nav */}
      <SafeAreaView style={styles.topNav}>
        <TouchableOpacity style={[styles.navBtn, webStyles.glass]} onPress={() => navigation.goBack()}>
          <ChevronLeft color={theme.colors.text} size={24} />
        </TouchableOpacity>
        <View style={[styles.navTitle, webStyles.glass]}>
          <Text style={styles.navTitleText}>Station Details</Text>
        </View>
        <View style={{ width: 40 }} />
      </SafeAreaView>

      {/* Bottom Sheet */}
      <View style={[styles.sheet, webStyles.glass]}>
        <View style={styles.sheetHandle} />

        <Text style={styles.stationName}>{station.name}</Text>
        <View style={styles.providerRow}>
          <Navigation color={theme.colors.textMuted} fill={theme.colors.textMuted} size={13} />
          <Text style={styles.providerText}>{station.provider} · {station.distance} away</Text>
        </View>

        <View style={styles.statsGrid}>
          <View style={[styles.statCard, webStyles.glass]}>
            <Zap color="#60a5fa" size={20} />
            <Text style={styles.statSub}>POWER</Text>
            <Text style={styles.statVal}>{station.power}</Text>
          </View>
          <View style={[styles.statCard, webStyles.glass]}>
            <Battery color={theme.colors.primary} size={20} />
            <Text style={styles.statSub}>STALLS</Text>
            <Text style={styles.statVal}>{station.stalls}</Text>
          </View>
          <View style={[styles.statCard, webStyles.glass]}>
            <DollarSign color="#eab308" size={20} />
            <Text style={styles.statSub}>PRICE</Text>
            <Text style={styles.statVal}>{station.price}</Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.reserveBtn, webStyles.blueGlow]}
          onPress={() => navigation.navigate('ReservationConfirm')}
          activeOpacity={0.85}
        >
          <Navigation color="#fff" size={20} />
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
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: 'rgba(0,255,0,0.2)',
  },
  markerIcon: {
    ...theme.neonGlow,
    width: 48, height: 48, borderRadius: 24,
    backgroundColor: theme.colors.background,
    borderWidth: 2, borderColor: theme.colors.primary,
    alignItems: 'center', justifyContent: 'center',
  },
  markerLabel: {
    marginTop: 8,
    backgroundColor: 'rgba(10,11,13,0.8)',
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8,
  },
  markerText: { color: theme.colors.primary, fontSize: 10, fontWeight: 'bold', letterSpacing: 0.5 },
  topNav: {
    position: 'absolute', top: 0, left: 0, right: 0,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.sm,
  },
  navBtn: {
    ...theme.glass,
    width: 40, height: 40, borderRadius: theme.radii.md,
    alignItems: 'center', justifyContent: 'center',
  },
  navTitle: {
    ...theme.glass,
    paddingHorizontal: 20, paddingVertical: 8, borderRadius: theme.radii.lg,
  },
  navTitleText: { color: theme.colors.text, fontWeight: 'bold', fontSize: 14 },
  sheet: {
    ...theme.glassDark,
    position: 'absolute', bottom: 0, left: 0, right: 0,
    borderTopLeftRadius: 40, borderTopRightRadius: 40,
    padding: theme.spacing.xl, paddingBottom: 48,
  },
  sheetHandle: {
    width: 48, height: 4, backgroundColor: theme.colors.border,
    borderRadius: 2, alignSelf: 'center', marginBottom: theme.spacing.xl,
  },
  stationName: { color: theme.colors.text, fontSize: 28, fontWeight: 'bold', marginBottom: 6 },
  providerRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: theme.spacing.xl },
  providerText: { color: theme.colors.textMuted, fontSize: 13, fontWeight: '500' },
  statsGrid: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.xl },
  statCard: {
    ...theme.glass,
    flex: 1, borderRadius: theme.radii.xxl, padding: theme.spacing.md,
    alignItems: 'center', gap: 6,
  },
  statSub: { color: theme.colors.textMuted, fontSize: 9, fontWeight: 'bold', letterSpacing: 1 },
  statVal: { color: theme.colors.text, fontSize: 16, fontWeight: 'bold' },
  reserveBtn: {
    ...theme.blueGlow,
    height: 64, backgroundColor: theme.colors.blue, borderRadius: 32,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: theme.spacing.sm,
  },
  reserveBtnText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
});
