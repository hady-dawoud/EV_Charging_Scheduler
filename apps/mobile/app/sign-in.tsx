import { useState } from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Button } from '@/components/ui';
import { colors, spacing, borderRadius } from '@/theme';

export default function SignInScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSignIn = () => {
    router.replace('/home');
  };

  const handleBack = () => {
    router.back();
  };

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={styles.title}>Sign In</Text>
        <Text style={styles.subtitle}>Welcome back to evMock</Text>

        <View style={styles.form}>
          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Email</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={colors.textMuted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Password</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="Enter your password"
              placeholderTextColor={colors.textMuted}
              secureTextEntry
            />
          </View>
        </View>

        <View style={styles.buttons}>
          <Button title="Sign In" onPress={handleSignIn} />
          <Button title="Back" onPress={handleBack} variant="secondary" />
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
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  subtitle: {
    fontSize: 16,
    color: colors.textSecondary,
    marginBottom: spacing['3xl'],
  },
  form: {
    gap: spacing.lg,
    marginBottom: spacing['3xl'],
  },
  inputContainer: {
    gap: spacing.sm,
  },
  inputLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 2,
  },
  input: {
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontSize: 16,
    color: colors.textPrimary,
    minHeight: 56,
  },
  buttons: {
    gap: spacing.md,
  },
});
