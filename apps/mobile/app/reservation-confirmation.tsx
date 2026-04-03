import { View, Text, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen, Button } from '@/components/ui';
import { colors, spacing, borderRadius } from '@/theme';

export default function ReservationConfirmationScreen() {
  const router = useRouter();
  const { stationName } = useLocalSearchParams<{ stationName: string }>();

  const handleBackToDashboard = () => {
    router.replace('/dashboard');
  };

  return (
    <Screen>
      <View style={styles.content}>
        <View style={styles.successSection}>
          <View style={styles.checkCircle}>
            <Text style={styles.checkMark}>✓</Text>
          </View>
          <Text style={styles.successTitle}>Reservation Confirmed</Text>
          <Text style={styles.successSubtitle}>Your charging spot is reserved</Text>
        </View>

        <View style={styles.card}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Station</Text>
            <Text style={styles.detailValue}>{stationName}</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Time</Text>
            <Text style={styles.detailValue}>Today, 3:30 PM</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Est. Duration</Text>
            <Text style={styles.detailValue}>45 min</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Est. Cost</Text>
            <Text style={styles.priceValue}>$8.50</Text>
          </View>
        </View>

        <View style={styles.ctaContainer}>
          <Button title="Back to Dashboard" onPress={handleBackToDashboard} />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    paddingTop: spacing['4xl'],
  },
  successSection: {
    alignItems: 'center',
    marginBottom: spacing['3xl'],
  },
  checkCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.success,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xl,
    shadowColor: colors.glowGreen,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 12,
    elevation: 4,
  },
  checkMark: {
    fontSize: 40,
    color: colors.background,
    fontWeight: '700',
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  successSubtitle: {
    fontSize: 16,
    color: colors.textSecondary,
  },
  card: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
  },
  detailLabel: {
    fontSize: 14,
    color: colors.textMuted,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textPrimary,
    textAlign: 'right',
    flex: 1,
    marginLeft: spacing.md,
  },
  priceValue: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.accent,
  },
  divider: {
    height: 1,
    backgroundColor: colors.glassBorder,
  },
  ctaContainer: {
    marginTop: 'auto',
    paddingBottom: spacing['2xl'],
  },
});
