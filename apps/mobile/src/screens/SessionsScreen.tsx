import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { History, Zap, Clock } from 'lucide-react-native';
import { mockSessions } from '../data/mockData';
import { theme, webStyles } from '../theme';

const isWeb = Platform.OS === 'web';

export default function SessionsScreen() {
  const upcoming = mockSessions.filter((s) => s.status === 'upcoming');
  const past = mockSessions.filter((s) => s.status === 'completed');

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.titleRow}>
          <History color={theme.colors.primary} size={28} />
          <Text style={styles.pageTitle}>My Sessions</Text>
        </View>

        {/* Upcoming */}
        {upcoming.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>UPCOMING RESERVATION</Text>
            {upcoming.map((s) => (
              <View key={s.id} style={[styles.upcomingCard, webStyles.glass]}>
                <View style={[styles.cardGlow, isWeb ? { filter: 'blur(40px)' } as any : {}]} />
                <View style={styles.upcomingHeader}>
                  <View>
                    <Text style={styles.upcomingName}>{s.stationName}</Text>
                    <Text style={styles.upcomingDate}>{s.date}</Text>
                  </View>
                  <View style={styles.reservedBadge}>
                    <Text style={styles.reservedText}>Reserved</Text>
                  </View>
                </View>
                <View style={styles.metaRow}>
                  <View style={styles.metaItem}>
                    <Zap color={theme.colors.textMuted} size={15} />
                    <Text style={styles.metaText}>Est. {s.energyAdded}</Text>
                  </View>
                  <View style={styles.metaItem}>
                    <Clock color={theme.colors.textMuted} size={15} />
                    <Text style={styles.metaText}>{s.duration}</Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Past */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>PAST SESSIONS</Text>
          {past.map((s) => (
            <View key={s.id} style={styles.pastCard}>
              <View style={styles.pastHeader}>
                <Text style={styles.pastName}>{s.stationName}</Text>
                <Text style={styles.pastCost}>{s.cost}</Text>
              </View>
              <View style={styles.pastMeta}>
                <Text style={styles.pastDate}>{s.date}</Text>
                <View style={styles.metaRow}>
                  <View style={styles.metaItem}>
                    <Zap color={theme.colors.textMuted} size={12} />
                    <Text style={styles.pastMetaText}>{s.energyAdded}</Text>
                  </View>
                  <View style={styles.metaItem}>
                    <Clock color={theme.colors.textMuted} size={12} />
                    <Text style={styles.pastMetaText}>{s.duration}</Text>
                  </View>
                </View>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 100 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, marginBottom: theme.spacing.xl },
  pageTitle: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold' },
  section: { marginBottom: theme.spacing.xl },
  sectionLabel: {
    color: theme.colors.textMuted, fontSize: 10, fontWeight: 'bold',
    letterSpacing: 2, marginBottom: theme.spacing.md,
  },
  upcomingCard: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    borderColor: 'rgba(0,255,0,0.25)',
    padding: theme.spacing.lg,
    overflow: 'hidden',
  },
  cardGlow: {
    position: 'absolute', width: 128, height: 128,
    borderRadius: 64, backgroundColor: 'rgba(0,255,0,0.08)',
    top: -32, right: -32,
  },
  upcomingHeader: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: theme.spacing.md,
  },
  upcomingName: { color: theme.colors.text, fontSize: 17, fontWeight: 'bold', marginBottom: 2 },
  upcomingDate: { color: theme.colors.primary, fontSize: 12, fontWeight: '500' },
  reservedBadge: {
    backgroundColor: 'rgba(0,255,0,0.15)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  reservedText: { color: theme.colors.primary, fontSize: 11, fontWeight: 'bold' },
  metaRow: { flexDirection: 'row', gap: theme.spacing.lg },
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
  pastHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  pastName: { color: theme.colors.text, fontSize: 14, fontWeight: 'bold' },
  pastCost: { color: theme.colors.text, fontSize: 14, fontWeight: 'bold' },
  pastMeta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  pastDate: { color: theme.colors.textMuted, fontSize: 11 },
  pastMetaText: { color: theme.colors.textMuted, fontSize: 11 },
});
