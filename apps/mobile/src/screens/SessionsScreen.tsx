import React, { useCallback, useMemo, useState } from 'react';
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
import { History, Zap, Clock, PoundSterling, CheckCircle, AlertTriangle } from 'lucide-react-native';

import { api } from '../services/api';
import { theme, webStyles } from '../theme';
import type { ApiChargingSession, ApiReservation } from '../types';

const isWeb = Platform.OS === 'web';

const formatCurrency = (gbp: number | null | undefined) => {
  if (gbp == null) return 'Cost pending';
  return `£${gbp.toFixed(2)}`;
};

const formatMinutes = (minutes: number | null | undefined) => {
  if (minutes == null) return 'Duration pending';
  return `${Math.round(minutes)} min`;
};

const formatKwh = (kwh: number | null | undefined) => {
  if (kwh == null) return 'Energy pending';
  return `${kwh.toFixed(1)} kWh`;
};

const formatDateTime = (iso: string) => {
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

const durationFromSession = (session: ApiChargingSession) => {
  const start = new Date(session.started_at).getTime();
  const end = session.ended_at ? new Date(session.ended_at).getTime() : Date.now();
  const minutes = Math.max(0, Math.round((end - start) / 60000));
  return `${minutes} min`;
};

export default function SessionsScreen() {
  const [reservations, setReservations] = useState<ApiReservation[]>([]);
  const [sessions, setSessions] = useState<ApiChargingSession[]>([]);
  const [activeSession, setActiveSession] = useState<ApiChargingSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [reservationResult, sessionResult, activeResult] = await Promise.all([
        api.getMyReservations(),
        api.getMyChargingSessions(),
        api.getActiveChargingSession(),
      ]);

      setReservations(reservationResult);
      setSessions(sessionResult);
      setActiveSession(activeResult);
    } catch (e) {
      console.error(e);
      setError('Could not load sessions.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadDashboard();
    }, [loadDashboard])
  );

  const sessionsByReservationId = useMemo(() => {
    const map = new Map<string, ApiChargingSession>();

    sessions.forEach((session) => {
      if (session.reservation_id) {
        map.set(session.reservation_id, session);
      }
    });

    return map;
  }, [sessions]);

  const reservationsById = useMemo(() => {
    const map = new Map<string, ApiReservation>();

    reservations.forEach((reservation) => {
      map.set(reservation.reservation_id, reservation);
    });

    return map;
  }, [reservations]);

  const waitingReservations = reservations.filter(
    (reservation) =>
      reservation.status === 'confirmed' &&
      !reservation.cancelled_at &&
      !sessionsByReservationId.has(reservation.reservation_id)
  );

  const closedReservations = reservations.filter(
    (reservation) =>
      reservation.status === 'expired' ||
      reservation.status === 'cancelled' ||
      Boolean(reservation.cancelled_at)
  );

  const activeSessions = useMemo(() => {
    const byId = new Map<string, ApiChargingSession>();

    if (activeSession) {
      byId.set(activeSession.session_id, activeSession);
    }

    sessions
      .filter((session) => session.status === 'active')
      .forEach((session) => byId.set(session.session_id, session));

    return [...byId.values()];
  }, [activeSession, sessions]);

  const staleSessions = sessions.filter((session) => session.status === 'stale_active');
  const completedSessions = sessions.filter((session) => session.status === 'completed');

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

              {waitingReservations.length > 0 ? (
                waitingReservations.map((reservation) => (
                  <ReservationCard key={reservation.reservation_id} reservation={reservation} />
                ))
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyText}>No reservation waiting for charger confirmation.</Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>ACTIVE CHARGING</Text>

              {activeSessions.length > 0 ? (
                activeSessions.map((session) => (
                  <ChargingSessionCard
                    key={session.session_id}
                    session={session}
                    reservation={session.reservation_id ? reservationsById.get(session.reservation_id) : null}
                  />
                ))
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyText}>No active charging session.</Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>ATTENTION NEEDED</Text>

              {staleSessions.length > 0 || closedReservations.length > 0 ? (
                <>
                  {staleSessions.map((session) => (
                    <ChargingSessionCard
                      key={session.session_id}
                      session={session}
                      reservation={session.reservation_id ? reservationsById.get(session.reservation_id) : null}
                    />
                  ))}
                  {closedReservations.map((reservation) => (
                    <ClosedReservationCard
                      key={reservation.reservation_id}
                      reservation={reservation}
                    />
                  ))}
                </>
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyText}>No expired reservations or stale sessions.</Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>COMPLETED CHARGING</Text>

              {completedSessions.length > 0 ? (
                completedSessions.map((session) => (
                  <ChargingSessionCard
                    key={session.session_id}
                    session={session}
                    reservation={session.reservation_id ? reservationsById.get(session.reservation_id) : null}
                  />
                ))
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyText}>No completed charging sessions yet.</Text>
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
};

function ReservationCard({ reservation }: ReservationCardProps) {
  const estimate = estimateFromReservation(reservation);

  return (
    <View style={[styles.upcomingCard, webStyles.glass]}>
      <View style={[styles.cardGlow, isWeb ? ({ filter: 'blur(40px)' } as any) : {}]} />
      <View style={styles.upcomingHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.upcomingName}>{reservation.station_name}</Text>
          <Text style={styles.upcomingDate}>
            {formatDateTime(reservation.reserved_start_at)}
          </Text>
        </View>
        <View style={styles.reservedBadge}>
          <Text style={styles.reservedText}>Waiting</Text>
        </View>
      </View>

      <Text style={styles.statusHint}>
        Waiting for charger-side start confirmation. The session will appear automatically when charging begins.
      </Text>

      <ReservationMeta reservation={reservation} />
    </View>
  );
}

function ClosedReservationCard({ reservation }: ReservationCardProps) {
  return (
    <View style={styles.pastCard}>
      <View style={styles.pastHeader}>
        <Text style={styles.pastName}>{reservation.station_name}</Text>
        <View style={styles.warningBadge}>
          <AlertTriangle color="#f59e0b" size={12} />
          <Text style={styles.warningText}>{reservation.status}</Text>
        </View>
      </View>

      <Text style={styles.statusHint}>
        {reservation.status === 'expired'
          ? 'Reservation expired because no charger-side start confirmation arrived in time.'
          : 'Reservation is no longer active.'}
      </Text>

      <ReservationMeta reservation={reservation} small />
    </View>
  );
}

function ReservationMeta({
  reservation,
  small = false,
}: {
  reservation: ApiReservation;
  small?: boolean;
}) {
  const estimate = estimateFromReservation(reservation);
  const textStyle = small ? styles.pastMetaText : styles.metaText;
  const iconSize = small ? 12 : 15;

  return (
    <View style={styles.metaRow}>
      <View style={styles.metaItem}>
        <PoundSterling color={theme.colors.textMuted} size={iconSize} />
        <Text style={textStyle}>{formatCurrency(estimate.estimatedCostGbp)}</Text>
      </View>

      <View style={styles.metaItem}>
        <Clock color={theme.colors.textMuted} size={iconSize} />
        <Text style={textStyle}>{formatMinutes(estimate.estimatedDurationMinutes)}</Text>
      </View>

      <View style={styles.metaItem}>
        <Zap color={theme.colors.textMuted} size={iconSize} />
        <Text style={textStyle}>{estimate.chargerLabel}</Text>
      </View>
    </View>
  );
}

type ChargingSessionCardProps = {
  session: ApiChargingSession;
  reservation?: ApiReservation | null;
};

function ChargingSessionCard({ session, reservation }: ChargingSessionCardProps) {
  const isActive = session.status === 'active';
  const isStale = session.status === 'stale_active';

  return (
    <View style={isActive ? [styles.upcomingCard, webStyles.glass] : styles.pastCard}>
      <View style={styles.pastHeader}>
        <Text style={isActive ? styles.upcomingName : styles.pastName}>{session.station_name}</Text>
        <Text style={styles.pastCost}>{formatCurrency(session.cost_total ?? reservation?.estimated_cost_gbp)}</Text>
      </View>

      {isActive ? (
        <Text style={styles.statusHint}>
          Charging is active. Completion will be recorded automatically when charger-side stop confirmation is received.
        </Text>
      ) : null}

      {isStale ? (
        <Text style={styles.statusHint}>
          Charger-side stop confirmation has not arrived. This session needs provider/admin review.
        </Text>
      ) : null}

      <View style={styles.pastMeta}>
        <Text style={styles.pastDate}>
          {isActive ? `Started ${formatDateTime(session.started_at)}` : formatDateTime(session.started_at)}
        </Text>

        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <Clock color={theme.colors.textMuted} size={12} />
            <Text style={styles.pastMetaText}>{durationFromSession(session)}</Text>
          </View>

          <View style={styles.metaItem}>
            <Zap color={theme.colors.textMuted} size={12} />
            <Text style={styles.pastMetaText}>
              {session.connector_type ?? reservation?.charger_label ?? 'Charging'}
            </Text>
          </View>

          <View style={styles.metaItem}>
            <CheckCircle color={theme.colors.textMuted} size={12} />
            <Text style={styles.pastMetaText}>{formatKwh(session.energy_kwh)}</Text>
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
    marginBottom: theme.spacing.sm,
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
  upcomingName: { color: theme.colors.text, fontSize: 17, fontWeight: 'bold', marginBottom: 2, flex: 1 },
  upcomingDate: { color: theme.colors.primary, fontSize: 12, fontWeight: '500' },
  statusHint: {
    color: theme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    marginBottom: theme.spacing.md,
  },
  reservedBadge: {
    backgroundColor: 'rgba(0,255,0,0.15)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  reservedText: { color: theme.colors.primary, fontSize: 11, fontWeight: 'bold', textTransform: 'capitalize' },
  warningBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(245,158,11,0.12)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  warningText: { color: '#f59e0b', fontSize: 11, fontWeight: 'bold', textTransform: 'capitalize' },
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
  pastMeta: { gap: theme.spacing.sm },
  pastDate: { color: theme.colors.textMuted, fontSize: 11 },
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
