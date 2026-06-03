import React, { useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { User, Settings, Bell, Shield, LogOut, Car, ChevronRight } from 'lucide-react-native';
import { api } from '../services/api';
import { authStorage } from '../services/authStorage';
import { useAuthStore } from '../stores/authStore';
import { fallbackVehicle, useVehicleStore } from '../stores/vehicleStore';
import { theme, webStyles } from '../theme';

const menuItems = [
  { icon: Settings, label: 'App Settings', route: 'AppSettings' },
  { icon: Bell, label: 'Notifications', route: 'NotificationSettings' },
  { icon: Shield, label: 'Privacy & Security', route: 'PrivacySecurity' },
] as const;

export default function ProfileScreen({ navigation }: any) {
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const vehicle = useVehicleStore((state) => state.vehicle);
  const loadVehicle = useVehicleStore((state) => state.loadVehicle);
  const activeVehicle = vehicle ?? fallbackVehicle;

  useEffect(() => {
    loadVehicle();
  }, [loadVehicle]);

  const handleLogout = async () => {
    const refreshToken = await authStorage.getRefreshToken();

    try {
      if (refreshToken) {
        await api.logout(refreshToken);
      }
    } catch (e) {
      console.error(e);
    } finally {
      await authStorage.clearRefreshToken();
      clearSession();
      navigation.replace('Splash');
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <Text style={styles.pageTitle}>Profile</Text>

        {/* User Card */}
        <View style={[styles.userCard, webStyles.glass]}>
          <View style={styles.avatarRing}>
            <View style={styles.avatarInner}>
              <User color="#d1d5db" size={28} />
            </View>
          </View>
          <View>
            <Text style={styles.userName}>{user?.name ?? 'EV Driver'}</Text>
            <Text style={styles.userEmail}>{user?.email ?? 'Not signed in'}</Text>
          </View>
        </View>

        {/* Vehicle Card */}
        <View style={styles.vehicleCard}>
          <View style={styles.vehicleHeader}>
            <Car color={theme.colors.primary} size={20} />
            <Text style={styles.vehicleLabel}>CONNECTED VEHICLE</Text>
          </View>
          <View style={styles.vehicleBody}>
            <View>
              <Text style={styles.vehicleName}>{activeVehicle.make} {activeVehicle.model}</Text>
              <Text style={styles.vehicleSub}>{activeVehicle.batteryCapacity} kWh Battery</Text>
            </View>
            <TouchableOpacity
              style={styles.manageBtn}
              onPress={() => navigation.navigate('ManageVehicle')}
            >
              <Text style={styles.manageBtnText}>Manage</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Menu */}
        <View style={styles.menuSection}>
          <Text style={styles.menuLabel}>PREFERENCES</Text>
          {menuItems.map((item) => (
            <TouchableOpacity
              key={item.label}
              style={styles.menuItem}
              activeOpacity={0.75}
              onPress={() => navigation.navigate(item.route)}
            >
              <View style={styles.menuItemLeft}>
                <item.icon color={theme.colors.textMuted} size={20} />
                <Text style={styles.menuItemText}>{item.label}</Text>
              </View>
              <ChevronRight color="#4b5563" size={20} />
            </TouchableOpacity>
          ))}
        </View>

        {/* Logout */}
        <TouchableOpacity
          style={styles.logoutBtn}
          onPress={handleLogout}
          activeOpacity={0.85}
        >
          <LogOut color="#ef4444" size={20} />
          <Text style={styles.logoutText}>Log Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 100 },
  pageTitle: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold', marginBottom: theme.spacing.xl },
  userCard: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
  avatarRing: {
    width: 64, height: 64, borderRadius: 32,
    borderWidth: 2, borderColor: theme.colors.primary, padding: 2,
  },
  avatarInner: {
    flex: 1, borderRadius: 28, backgroundColor: theme.colors.surface,
    alignItems: 'center', justifyContent: 'center',
  },
  userName: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold' },
  userEmail: { color: theme.colors.textMuted, fontSize: 13 },
  vehicleCard: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.xl,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  vehicleHeader: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  vehicleLabel: { color: theme.colors.textMuted, fontSize: 10, fontWeight: 'bold', letterSpacing: 2 },
  vehicleBody: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  vehicleName: { color: theme.colors.text, fontSize: 17, fontWeight: 'bold' },
  vehicleSub: { color: theme.colors.textMuted, fontSize: 13 },
  manageBtn: {
    backgroundColor: 'rgba(0,255,0,0.1)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  manageBtnText: { color: theme.colors.primary, fontSize: 12, fontWeight: 'bold' },
  menuSection: { marginBottom: theme.spacing.xl },
  menuLabel: {
    color: theme.colors.textMuted, fontSize: 10, fontWeight: 'bold',
    letterSpacing: 2, marginBottom: theme.spacing.md, paddingHorizontal: 8,
  },
  menuItem: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.03)',
    padding: theme.spacing.md, borderRadius: theme.radii.xl, marginBottom: 8,
  },
  menuItemLeft: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm },
  menuItemText: { color: theme.colors.text, fontSize: 15, fontWeight: '500' },
  logoutBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: theme.spacing.sm, padding: theme.spacing.md,
    backgroundColor: 'rgba(239,68,68,0.05)',
    borderRadius: theme.radii.xl,
    borderWidth: 1, borderColor: 'rgba(239,68,68,0.2)',
  },
  logoutText: { color: '#ef4444', fontSize: 15, fontWeight: 'bold' },
});
