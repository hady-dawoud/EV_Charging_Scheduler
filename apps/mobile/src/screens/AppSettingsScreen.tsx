import React, { useEffect } from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Settings } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { useSettingsStore } from '../stores/settingsStore';
import { theme, webStyles } from '../theme';
import type { CurrencyCode, DistanceUnit, RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'AppSettings'>;

export default function AppSettingsScreen({ navigation }: Props) {
  const preferences = useSettingsStore((state) => state.preferences);
  const loadPreferences = useSettingsStore((state) => state.loadPreferences);
  const updatePreferences = useSettingsStore((state) => state.updatePreferences);
  const resetPreferences = useSettingsStore((state) => state.resetPreferences);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const renderOption = <T extends string>(
    label: string,
    value: T,
    activeValue: T,
    onPress: (value: T) => void
  ) => (
    <TouchableOpacity
      key={value}
      style={[styles.optionBtn, activeValue === value && styles.optionBtnActive]}
      onPress={() => onPress(value)}
      activeOpacity={0.8}
    >
      <Text style={[styles.optionText, activeValue === value && styles.optionTextActive]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={24} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>App Settings</Text>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <View style={styles.cardHeader}>
            <View style={styles.cardIcon}>
              <Settings color={theme.colors.primary} size={18} />
            </View>
            <Text style={styles.cardTitle}>Display Preferences</Text>
          </View>

          <Text style={styles.sectionLabel}>Distance unit</Text>
          <View style={styles.optionRow}>
            {renderOption<DistanceUnit>('Kilometres', 'km', preferences.distanceUnit, (distanceUnit) =>
              updatePreferences({ distanceUnit })
            )}
            {renderOption<DistanceUnit>('Miles', 'mi', preferences.distanceUnit, (distanceUnit) =>
              updatePreferences({ distanceUnit })
            )}
          </View>

          <Text style={styles.sectionLabel}>Currency</Text>
          <View style={styles.optionRow}>
            {renderOption<CurrencyCode>('GBP', 'GBP', preferences.currency, (currency) =>
              updatePreferences({ currency })
            )}
            {renderOption<CurrencyCode>('EUR', 'EUR', preferences.currency, (currency) =>
              updatePreferences({ currency })
            )}
          </View>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <Text style={styles.cardLabel}>ABOUT</Text>
          <Text style={styles.infoLabel}>App version</Text>
          <Text style={styles.infoValue}>1.0.0</Text>
        </View>

        <TouchableOpacity style={styles.resetBtn} onPress={resetPreferences} activeOpacity={0.8}>
          <Text style={styles.resetBtnText}>Reset App Preferences</Text>
        </TouchableOpacity>
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
    marginBottom: theme.spacing.md,
  },
  sectionLabel: {
    color: theme.colors.text,
    fontSize: 14,
    fontWeight: '700',
    marginBottom: theme.spacing.sm,
  },
  optionRow: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.lg,
  },
  optionBtn: {
    flex: 1,
    height: 44,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: 'rgba(255,255,255,0.04)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  optionBtnActive: {
    borderColor: theme.colors.primary,
    backgroundColor: 'rgba(0,255,0,0.1)',
  },
  optionText: { color: theme.colors.textMuted, fontWeight: '700' },
  optionTextActive: { color: theme.colors.primary },
  infoLabel: {
    color: theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    marginTop: theme.spacing.sm,
  },
  infoValue: {
    color: theme.colors.text,
    fontSize: 13,
    marginTop: 4,
  },
  resetBtn: {
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.xl,
    padding: theme.spacing.md,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  resetBtnText: {
    color: theme.colors.text,
    fontWeight: '700',
  },
});
