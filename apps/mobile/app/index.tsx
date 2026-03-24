import { View, Text, StyleSheet, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Button } from '@/components/ui';
import { colors, spacing } from '@/theme';

export default function WelcomeScreen() {
  const router = useRouter();

  const handleSignIn = () => {
    Alert.alert('Coming Soon', 'Sign in will be available in a future update.');
  };

  const handleCreateAccount = () => {
    Alert.alert('Coming Soon', 'Account creation will be available in a future update.');
  };

  const handleContinueAsGuest = () => {
    router.push('/dashboard');
  };

  return (
    <Screen>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>evMock</Text>
          <Text style={styles.tagline}>
            Smart EV Charging, Optimized for Cost, Time, and Grid Load
          </Text>
        </View>

        <View style={styles.buttons}>
          <Button title="Sign In" onPress={handleSignIn} />
          <Button
            title="Create Account"
            onPress={handleCreateAccount}
            variant="secondary"
          />
          <Button
            title="Continue as Guest"
            onPress={handleContinueAsGuest}
            variant="secondary"
          />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing['4xl'],
  },
  title: {
    fontSize: 48,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: spacing.lg,
  },
  tagline: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
  },
  buttons: {
    gap: spacing.md,
  },
});
