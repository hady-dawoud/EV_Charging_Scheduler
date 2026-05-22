import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, CheckCircle, MapPin } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { theme, webStyles } from '../theme';
import { ReservationRecord, RootStackParamList } from '../types';
import { upsertReservationFromStation } from '../data/reservationStore';

type Props = NativeStackScreenProps<RootStackParamList, 'ReservationConfirm'>;

const formatCurrency = (gbp: number) => `£${gbp.toFixed(2)}`;
const formatMinutes = (minutes: number) => `${Math.round(minutes)} min`;

const formatReservationTime = (iso: string) => {
  const dt = new Date(iso);
  return dt.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

export default function ReservationConfirmScreen({ navigation, route }: Props) {
  const { station } = route.params;
  const [reservation, setReservation] = useState<ReservationRecord | null>(null);

  useEffect(() => {
    const saved = upsertReservationFromStation(station);
    setReservation(saved);
  }, [station]);

  const details = useMemo(() => {
    if (!reservation) return [];

    return [
      { label: 'Station', value: reservation.station.name },
      { label: 'Reserved At', value: formatReservationTime(reservation.reservedAtIso) },
      {
        label: 'Est. Duration',
        value: formatMinutes(reservation.station.estimatedDurationMinutes),
      },
      {
        label: 'Est. Cost',
        value: formatCurrency(reservation.station.estimatedCostGbp),
        highlight: true,
      },
    ];
  }, [reservation]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={24} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Confirmation</Text>
        </View>

        <View style={styles.successSection}>
          <View style={styles.checkCircle}>
            <CheckCircle color={theme.colors.primary} size={40} />
          </View>
          <Text style={styles.successTitle}>Reservation Confirmed</Text>
          <Text style={styles.successSub}>
            Your spot at {reservation?.station.name ?? station.name} has been secured.
          </Text>
        </View>

        <View style={[styles.detailsCard, webStyles.glass]}>
          <Text style={styles.cardLabel}>SESSION DETAILS</Text>
          {details.map((item, i) => (
            <View
              key={item.label}
              style={[styles.detailRow, i < details.length - 1 && styles.detailRowBorder]}
            >
              <Text style={styles.detailLabel}>{item.label}</Text>
              <Text style={[styles.detailValue, item.highlight && { color: theme.colors.primary }]}>
                {item.value}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.navBtn, webStyles.neonGlowSmall]}
            onPress={() => navigation.navigate('Main', { screen: 'Sessions' })}
            activeOpacity={0.85}
          >
            <MapPin color="#000" size={20} />
            <Text style={styles.navBtnText}>View Sessions</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.homeBtn}
            onPress={() => navigation.navigate('Main', { screen: 'Home' })}
            activeOpacity={0.85}
          >
            <Text style={styles.homeBtnText}>Back to Home</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 40 },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md, marginBottom: theme.spacing.xl },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.surfaceLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pageTitle: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold' },
  successSection: { alignItems: 'center', marginBottom: theme.spacing.xl, paddingTop: theme.spacing.md },
  checkCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(0,255,0,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
  },
  successTitle: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold', marginBottom: 8 },
  successSub: { color: theme.colors.textMuted, textAlign: 'center', fontSize: 14, lineHeight: 20 },
  detailsCard: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.xl,
  },
  cardLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.lg,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  detailRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  detailLabel: { color: theme.colors.textMuted, fontSize: 14 },
  detailValue: { color: theme.colors.text, fontSize: 14, fontWeight: 'bold', flexShrink: 1, textAlign: 'right' },
  actions: { gap: theme.spacing.md },
  navBtn: {
    ...theme.neonGlowSmall,
    height: 56,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  navBtnText: { color: '#000', fontSize: 18, fontWeight: 'bold' },
  homeBtn: {
    height: 56,
    backgroundColor: theme.colors.surfaceLight,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  homeBtnText: { color: theme.colors.text, fontSize: 18, fontWeight: 'bold' },
});