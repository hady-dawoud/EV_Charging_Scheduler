import React, { useState } from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Eye, EyeOff, KeyRound, Lock } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { NeonButton } from '../components/NeonButton';
import { api } from '../services/api';
import { theme, webStyles } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ResetPassword'>;

export default function ResetPasswordScreen({ navigation, route }: Props) {
  const [token, setToken] = useState(route.params?.token ?? '');
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(
    route.params?.token ? 'Reset token loaded. Enter a new password.' : null
  );
  const [error, setError] = useState<string | null>(null);

  const handleConfirmReset = async () => {
    setIsLoading(true);
    setError(null);
    setMessage(null);

    if (newPassword.length < 8) {
      setIsLoading(false);
      setError('Password must be at least 8 characters.');
      return;
    }

    try {
      await api.confirmPasswordReset(token.trim(), newPassword);

      setMessage('Password reset successful. Sign in with your new password.');
      setNewPassword('');

      setTimeout(() => {
        navigation.replace('Login');
      }, 900);
    } catch (e) {
      console.error(e);
      setError('Reset token is invalid, expired, or already used.');
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
        <Text style={styles.title}>Set new password</Text>
        <Text style={styles.subtitle}>
          Paste your reset token and choose a new password.
        </Text>
      </View>

      <View style={[styles.card, webStyles.glass]}>
        <View style={styles.inputRow}>
          <KeyRound color={theme.colors.textMuted} size={20} style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="Reset token"
            placeholderTextColor={theme.colors.textMuted}
            value={token}
            onChangeText={setToken}
            autoCapitalize="none"
            multiline
          />
        </View>

        <View style={styles.inputRow}>
          <Lock color={theme.colors.textMuted} size={20} style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            placeholder="New password"
            placeholderTextColor={theme.colors.textMuted}
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry={!showPassword}
            autoCapitalize="none"
          />
          <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeBtn}>
            {showPassword ? (
              <EyeOff color={theme.colors.textMuted} size={20} />
            ) : (
              <Eye color={theme.colors.textMuted} size={20} />
            )}
          </TouchableOpacity>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}
        {message ? <Text style={styles.messageText}>{message}</Text> : null}
      </View>

      <NeonButton
        buttonStyle={styles.primaryBtn}
        frameStyle={styles.primaryBtnFrame}
        onPress={handleConfirmReset}
        disabled={isLoading || !token.trim()}
        activeOpacity={0.85}
      >
        {isLoading ? (
          <ActivityIndicator color="#000" />
        ) : (
          <Text style={styles.primaryBtnText}>Reset Password</Text>
        )}
      </NeonButton>
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
    minHeight: 56,
    paddingHorizontal: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  inputIcon: {
    marginRight: theme.spacing.sm,
  },
  input: {
    flex: 1,
    color: theme.colors.text,
    fontSize: 16,
    paddingVertical: theme.spacing.sm,
  },
  eyeBtn: {
    padding: theme.spacing.xs,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 13,
    marginTop: theme.spacing.xs,
  },
  messageText: {
    color: theme.colors.textMuted,
    fontSize: 13,
    marginTop: theme.spacing.xs,
    lineHeight: 18,
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
});
