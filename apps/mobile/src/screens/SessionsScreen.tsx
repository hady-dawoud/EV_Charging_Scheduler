import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { History, Zap, Clock, PoundSterling } from 'lucide-react-native';

import { api } from '../services/api';
import { theme, webStyles } from '../theme';
import type { ApiReservation } from '../types';

const isWeb = Platform.OS === 'web';

const formatCurrency = (gbp: number | null | undefined) => {
  if (gbp == null) return 'Cost pending';
  return `£${gbp.toFixed(2)}`;
};

const formatMinutes = (minutes: number | null | undefined) => {
  if (minutes == null) return 'Duration pending';
  return `${Math.round(minutes)} min`;
};

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

const estimateFromReservation = (reservation: ApiReservation) => ({
  estimatedCostGbp: reservation.estimated_cost_gbp,
  estimatedDurationMinutes: reservation.estimated_duration_minutes,
  chargerLabel: reservation.charger_label ?? 'Reserved',
});

export default function SessionsScreen() {
  const [reservations, setReservations] = useState<ApiReservation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReservations = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await api.getMyReservations();
      setReservations(result);
    } catch (e) {
      console.error(e);
      setError('Could not load reservations.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadReservations();
    }, [loadReservations])
  );

  const currentReservations = reservations.filter(
    (reservation) => reservation.status !== 'cancelled' && !reservation.cancelled_at
  );

  const pastReservations = reservations.filter(
    (reservation) => reservation.status === 'cancelled' || Boolean(reservation.cancelled_at)
  );

  const latestReservation = currentReservations[0] ?? null;
  const olderReservations = currentReservations.slice(1);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.titleRow}>
          <History color={theme.colors.primary} size={28} />
          <Text style={styles.pageTitle}>My Sessions</Text>
        </View>

        {isLoading ? (
          <View style={styles.emptyCard}>
            <ActivityIndicator color={theme.colors.primary} />
          </View>
        ) : error ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>{error}</Text>
          </View>
        ) : (
          <>
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>RESERVED OPTIONS</Text>

              {latestReservation ? (
                <ReservationCard reservation={latestReservation} featured />
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyText}>No reserved option yet.</Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>PAST RESERVED OPTIONS</Text>

              {[...olderReservations, ...pastReservations].length > 0 ? (
                [...olderReservations, ...pastReservations].map((reservation) => (
                  <ReservationCard key={reservation.reservation_id} reservation={reservation} />
                ))
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyText}>No past reserved options yet.</Text>
                </View>
              )}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

type ReservationCardProps = {
  reservation: ApiReservation;
  featured?: boolean;
};

function ReservationCard({ reservation, featured = false }: ReservationCardProps) {
  const estimate = estimateFromReservation(reservation);

  if (featured) {
    return (
      <View style={[styles.upcomingCard, webStyles.glass]}>
        <View style={[styles.cardGlow, isWeb ? ({ filter: 'blur(40px)' } as any) : {}]} />
        <View style={styles.upcomingHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.upcomingName}>{reservation.station_name}</Text>
            <Text style={styles.upcomingDate}>
              {formatReservationTime(reservation.reserved_start_at)}
            </Text>
          </View>
          <View style={styles.reservedBadge}>
            <Text style={styles.reservedText}>{reservation.status}</Text>
          </View>
        </View>

        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <PoundSterling color={theme.colors.textMuted} size={15} />
            <Text style={styles.metaText}>
              {formatCurrency(estimate.estimatedCostGbp)}
            </Text>
          </View>

          <View style={styles.metaItem}>
            <Clock color={theme.colors.textMuted} size={15} />
            <Text style={styles.metaText}>
              {formatMinutes(estimate.estimatedDurationMinutes)}
            </Text>
          </View>

          <View style={styles.metaItem}>
            <Zap color={theme.colors.textMuted} size={15} />
            <Text style={styles.metaText}>{estimate.chargerLabel}</Text>
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.pastCard}>
      <View style={styles.pastHeader}>
        <Text style={styles.pastName}>{reservation.station_name}</Text>
        <Text style={styles.pastCost}>{formatCurrency(estimate.estimatedCostGbp)}</Text>
      </View>

      <View style={styles.pastMeta}>
        <Text style={styles.pastDate}>
          {formatReservationTime(reservation.reserved_start_at)}
        </Text>

        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <Clock color={theme.colors.textMuted} size={12} />
            <Text style={styles.pastMetaText}>
              {formatMinutes(estimate.estimatedDurationMinutes)}
            </Text>
          </View>

          <View style={styles.metaItem}>
            <Zap color={theme.colors.textMuted} size={12} />
            <Text style={styles.pastMetaText}>{estimate.chargerLabel}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 100 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, marginBottom: theme.spacing.xl },
  pageTitle: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold' },
  section: { marginBottom: theme.spacing.xl },
  sectionLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.md,
  },
  upcomingCard: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    borderColor: 'rgba(0,255,0,0.25)',
    padding: theme.spacing.lg,
    overflow: 'hidden',
  },
  cardGlow: {
    position: 'absolute',
    width: 128,
    height: 128,
    borderRadius: 64,
    backgroundColor: 'rgba(0,255,0,0.08)',
    top: -32,
    right: -32,
  },
  upcomingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: theme.spacing.md,
  },
  upcomingName: { color: theme.colors.text, fontSize: 17, fontWeight: 'bold', marginBottom: 2 },
  upcomingDate: { color: theme.colors.primary, fontSize: 12, fontWeight: '500' },
  reservedBadge: {
    backgroundColor: 'rgba(0,255,0,0.15)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  reservedText: { color: theme.colors.primary, fontSize: 11, fontWeight: 'bold', textTransform: 'capitalize' },
  metaRow: { flexDirection: 'row', gap: theme.spacing.lg, flexWrap: 'wrap' },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  metaText: { color: '#d1d5db', fontSize: 13 },
  pastCard: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: theme.radii.xl,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: '#222426',
    marginBottom: theme.spacing.sm,
  },
  pastHeader: { flexDirection: 'row', justifyContent: 'space-between', gap: theme.spacing.md, marginBottom: 6 },
  pastName: { flex: 1, color: theme.colors.text, fontSize: 14, fontWeight: 'bold' },
  pastCost: { color: theme.colors.text, fontSize: 14, fontWeight: 'bold' },
  pastMeta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: theme.spacing.md },
  pastDate: { color: theme.colors.textMuted, fontSize: 11, flex: 1 },
  pastMetaText: { color: theme.colors.textMuted, fontSize: 11 },
  emptyCard: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: theme.radii.xl,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: '#222426',
  },
  emptyText: {
    color: theme.colors.textMuted,
    fontSize: 13,
  },
});
