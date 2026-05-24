import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, CheckCircle, MapPin } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { api } from '../services/api';
import { theme, webStyles } from '../theme';
import type { ApiReservation, RootStackParamList } from '../types';

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
  const [reservation, setReservation] = useState<ApiReservation | null>(null);
  const [isCreating, setIsCreating] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const createReservation = async () => {
      setIsCreating(true);
      setError(null);

      try {
        const now = new Date();
        const reservedUntil = new Date(now.getTime() + 15 * 60 * 1000);

        const created = await api.createReservation({
          client_request_id: null,
          request_id: null,
          station_id: station.id,
          recommendation_rank: 1,
          reserved_start_at: now.toISOString(),
          reserved_until: reservedUntil.toISOString(),
          estimated_cost_gbp: station.estimatedCostGbp,
          estimated_duration_minutes: station.estimatedDurationMinutes,
          charger_label: station.chargerLabel,
          distance_km: station.distanceKm,
          score: station.score,
        });

        if (isMounted) {
          setReservation(created);
        }
      } catch (e) {
        console.error(e);
        if (isMounted) {
          setError('Could not create reservation. Try again from the recommendation screen.');
        }
      } finally {
        if (isMounted) {
          setIsCreating(false);
        }
      }
    };

    void createReservation();

    return () => {
      isMounted = false;
    };
  }, [station.id]);

  const details = useMemo(() => {
    const reservedAtIso = reservation?.reserved_start_at ?? new Date().toISOString();

    return [
      { label: 'Station', value: reservation?.station_name ?? station.name },
      { label: 'Reserved At', value: formatReservationTime(reservedAtIso) },
      {
        label: 'Est. Duration',
        value: formatMinutes(station.estimatedDurationMinutes),
      },
      {
        label: 'Est. Cost',
        value: formatCurrency(station.estimatedCostGbp),
        highlight: true,
      },
    ];
  }, [reservation, station]);

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
            {isCreating ? (
              <ActivityIndicator color={theme.colors.primary} />
            ) : (
              <CheckCircle color={error ? '#ef4444' : theme.colors.primary} size={40} />
            )}
          </View>
          <Text style={styles.successTitle}>
            {isCreating
              ? 'Creating Reservation'
              : error
                ? 'Reservation Failed'
                : 'Reservation Confirmed'}
          </Text>
          <Text style={styles.successSub}>
            {error ?? `Your spot at ${reservation?.station_name ?? station.name} has been secured.`}
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
            style={[styles.navBtn, webStyles.neonGlowSmall, isCreating && styles.disabledBtn]}
            onPress={() => navigation.navigate('Main', { screen: 'Sessions' })}
            disabled={isCreating}
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
  disabledBtn: {
    opacity: 0.6,
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
