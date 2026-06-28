import React from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Lock, Shield } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { useAuthStore } from '../stores/authStore';
import { theme, webStyles } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'PrivacySecurity'>;

export default function PrivacySecurityScreen({ navigation }: Props) {
  const user = useAuthStore((state) => state.user);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={24} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Privacy & Security</Text>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <View style={styles.cardHeader}>
            <View style={styles.cardIcon}>
              <Shield color={theme.colors.primary} size={18} />
            </View>
            <Text style={styles.cardTitle}>Account</Text>
          </View>

          <Text style={styles.infoLabel}>Signed in as</Text>
          <Text style={styles.infoValue}>{user?.email ?? 'Not signed in'}</Text>

        </View>

        <View style={[styles.card, webStyles.glass]}>
          <View style={styles.cardHeader}>
            <Lock color={theme.colors.primary} size={22} />
            <Text style={styles.cardLabel}>PASSWORD</Text>
          </View>

          <Text style={styles.infoValue}>
            Use password reset to change your password. Existing refresh tokens are revoked after a successful reset.
          </Text>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('ForgotPassword')}
            activeOpacity={0.85}
          >
            <Text style={styles.actionBtnText}>Reset Password</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: {
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    paddingBottom: 100,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.xl,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.surfaceLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pageTitle: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold' },
  card: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xl,
  },
  cardIcon: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(0,255,0,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(0,255,0,0.28)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardTitle: {
    color: theme.colors.text,
    fontSize: 17,
    fontWeight: '800',
  },
  cardLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  infoLabel: {
    color: theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    marginTop: theme.spacing.sm,
  },
  infoValue: {
    color: theme.colors.text,
    fontSize: 14,
    marginTop: 6,
    lineHeight: 20,
  },
  actionBtn: {
    marginTop: theme.spacing.lg,
    height: 48,
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: theme.colors.primary,
    backgroundColor: 'rgba(0,255,0,0.08)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionBtnText: {
    color: theme.colors.primary,
    fontWeight: '800',
  },
});
