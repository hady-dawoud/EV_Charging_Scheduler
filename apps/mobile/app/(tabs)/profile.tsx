import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen } from '@/components/ui';
import { colors, spacing, borderRadius } from '@/theme';

const mockUser = {
  name: 'Guest User',
  email: 'guest@evmock.app',
};

const mockVehicle = {
  make: 'Tesla',
  model: 'Model 3',
  batteryCapacity: 75,
};

export default function ProfileScreen() {
  const router = useRouter();

  const handleExit = () => {
    router.replace('/');
  };

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={styles.title}>Profile</Text>

        {/* User Card */}
        <View style={styles.userCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>👤</Text>
          </View>
          <View style={styles.userInfo}>
            <Text style={styles.userName}>{mockUser.name}</Text>
            <Text style={styles.userEmail}>{mockUser.email}</Text>
          </View>
        </View>

        {/* Vehicle Card */}
        <View style={styles.vehicleCard}>
          <Text style={styles.sectionTitle}>Connected Vehicle</Text>
          <View style={styles.divider} />
          <Text style={styles.vehicleName}>
            {mockVehicle.make} {mockVehicle.model}
          </Text>
          <Text style={styles.vehicleDetail}>
            {mockVehicle.batteryCapacity} kWh Battery
          </Text>
        </View>

        {/* Exit Button */}
        <View style={styles.exitContainer}>
          <Pressable style={styles.exitButton} onPress={handleExit}>
            <Text style={styles.exitButtonText}>Back to Welcome</Text>
          </Pressable>
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    paddingTop: spacing['2xl'],
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing['2xl'],
  },
  userCard: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.surfaceLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.lg,
  },
  avatarText: {
    fontSize: 24,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  userEmail: {
    fontSize: 14,
    color: colors.textMuted,
  },
  vehicleCard: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    marginBottom: spacing['2xl'],
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 2,
    marginBottom: spacing.md,
  },
  divider: {
    height: 1,
    backgroundColor: colors.glassBorder,
    marginBottom: spacing.md,
  },
  vehicleName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  vehicleDetail: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  exitContainer: {
    marginTop: 'auto',
    paddingBottom: spacing['2xl'],
  },
  exitButton: {
    borderWidth: 1,
    borderColor: colors.error,
    backgroundColor: 'rgba(255, 82, 82, 0.1)',
    borderRadius: borderRadius.lg,
    paddingVertical: spacing.lg,
    alignItems: 'center',
  },
  exitButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.error,
  },
});
