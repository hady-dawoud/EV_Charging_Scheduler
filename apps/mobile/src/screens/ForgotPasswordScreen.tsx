import React, { useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Mail } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { NeonButton } from '../components/NeonButton';
import { api } from '../services/api';
import { theme, webStyles } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ForgotPassword'>;

const isWeb = Platform.OS === 'web';

export default function ForgotPasswordScreen({ navigation }: Props) {
  const [email, setEmail] = useState('alex.mercer@example.com');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [developmentToken, setDevelopmentToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRequestReset = async () => {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    setDevelopmentToken(null);

    try {
      const result = await api.requestPasswordReset(email.trim());

      setMessage(result.message);
      setDevelopmentToken(result.development_reset_token ?? null);

      if (result.development_reset_token) {
        navigation.navigate('ResetPassword', {
          token: result.development_reset_token,
          email: email.trim(),
        });
      }
    } catch (e) {
      console.error(e);
      setError('Could not request password reset.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
        <ChevronLeft color={theme.colors.text} size={24} />
      </TouchableOpacity>

      <View style={styles.header}>
        <Text style={styles.title}>Reset password</Text>
        <Text style={styles.subtitle}>
          Enter your account email and we’ll generate reset instructions.
        </Text>
      </View>

      <View style={[styles.card, webStyles.glass]}>
        <View style={styles.inputRow}>
          <Mail color={theme.colors.textMuted} size={20} style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="Email address"
            placeholderTextColor={theme.colors.textMuted}
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}
        {message ? <Text style={styles.messageText}>{message}</Text> : null}

        {developmentToken && isWeb ? (
          <Text style={styles.devTokenText}>Development reset token generated.</Text>
        ) : null}
      </View>

      <NeonButton
        buttonStyle={styles.primaryBtn}
        frameStyle={styles.primaryBtnFrame}
        onPress={handleRequestReset}
        disabled={isLoading}
        activeOpacity={0.85}
      >
        {isLoading ? (
          <ActivityIndicator color="#000" />
        ) : (
          <Text style={styles.primaryBtnText}>Continue</Text>
        )}
      </NeonButton>

      <TouchableOpacity
        style={styles.secondaryBtn}
        onPress={() => navigation.navigate('ResetPassword')}
      >
        <Text style={styles.secondaryBtnText}>Already have a reset token?</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: theme.colors.background,
    paddingHorizontal: theme.spacing.lg,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.surfaceLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.xl,
  },
  header: {
    marginBottom: theme.spacing.xl,
  },
  title: {
    color: theme.colors.text,
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: 16,
    lineHeight: 22,
  },
  card: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.xl,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceLight,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.lg,
    height: 56,
    paddingHorizontal: theme.spacing.md,
  },
  inputIcon: {
    marginRight: theme.spacing.sm,
  },
  input: {
    flex: 1,
    color: theme.colors.text,
    fontSize: 16,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 13,
    marginTop: theme.spacing.md,
  },
  messageText: {
    color: theme.colors.textMuted,
    fontSize: 13,
    marginTop: theme.spacing.md,
    lineHeight: 18,
  },
  devTokenText: {
    color: theme.colors.primary,
    fontSize: 12,
    marginTop: theme.spacing.md,
    fontWeight: '600',
  },
  primaryBtnFrame: {
    marginBottom: theme.spacing.md,
  },
  primaryBtn: {
    backgroundColor: theme.colors.primary,
    height: 56,
    borderRadius: theme.radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryBtnText: {
    color: '#000',
    fontSize: 18,
    fontWeight: 'bold',
  },
  secondaryBtn: {
    alignItems: 'center',
    paddingVertical: theme.spacing.md,
  },
  secondaryBtnText: {
    color: theme.colors.primary,
    fontWeight: '700',
  },
});
