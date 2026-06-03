import React, { useEffect } from 'react';
import {
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Bell, ChevronLeft } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { useSettingsStore } from '../stores/settingsStore';
import { theme, webStyles } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'NotificationSettings'>;

export default function NotificationSettingsScreen({ navigation }: Props) {
  const notifications = useSettingsStore((state) => state.preferences.notifications);
  const loadPreferences = useSettingsStore((state) => state.loadPreferences);
  const updateNotifications = useSettingsStore((state) => state.updateNotifications);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={24} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Notifications</Text>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <View style={styles.cardHeader}>
            <Bell color={theme.colors.primary} size={22} />
            <Text style={styles.cardLabel}>NOTIFICATION PREFERENCES</Text>
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingCopy}>
              <Text style={styles.settingTitle}>Reservation reminders</Text>
              <Text style={styles.settingDesc}>Remind me before a reserved charging slot starts.</Text>
            </View>
            <Switch
              value={notifications.reservationReminders}
              onValueChange={(reservationReminders) => updateNotifications({ reservationReminders })}
            />
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingCopy}>
              <Text style={styles.settingTitle}>Charging session updates</Text>
              <Text style={styles.settingDesc}>Notify me when charging starts, completes, or changes state.</Text>
            </View>
            <Switch
              value={notifications.chargingSessionUpdates}
              onValueChange={(chargingSessionUpdates) => updateNotifications({ chargingSessionUpdates })}
            />
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingCopy}>
              <Text style={styles.settingTitle}>Recommendation alerts</Text>
              <Text style={styles.settingDesc}>Notify me when better charging options become available.</Text>
            </View>
            <Switch
              value={notifications.recommendationAlerts}
              onValueChange={(recommendationAlerts) => updateNotifications({ recommendationAlerts })}
            />
          </View>
        </View>

        <Text style={styles.noteText}>
          Preferences are saved on this device. Push delivery can be connected when notification infrastructure is added.
        </Text>
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
    marginBottom: theme.spacing.lg,
  },
  cardLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: theme.spacing.md,
    paddingVertical: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  settingCopy: { flex: 1 },
  settingTitle: {
    color: theme.colors.text,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 4,
  },
  settingDesc: {
    color: theme.colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
  },
  noteText: {
    color: theme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    paddingHorizontal: theme.spacing.sm,
  },
});
