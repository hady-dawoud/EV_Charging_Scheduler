import React, { useCallback, useEffect, useMemo, useState } from 'react';
import zapRouteLogo from '../assets/branding/zaproute-logo-wide.png';
import type { ImageSourcePropType } from 'react-native';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
  Image,
  PanResponder,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Zap, Car } from 'lucide-react-native';
import Svg, { Circle } from 'react-native-svg';
import { NeonButton } from '../components/NeonButton';
import { api } from '../services/api';
import { theme, webStyles } from '../theme';
import { fallbackVehicle, useVehicleStore } from '../stores/vehicleStore';
import type { ApiChargingSession, ApiReservation } from '../types';

const isWeb = Platform.OS === 'web';
const zapRouteLogoSource: ImageSourcePropType =
  Platform.OS === 'web'
    ? { uri: zapRouteLogo as string }
    : (zapRouteLogo as unknown as ImageSourcePropType);


const clampSoC = (value: number) => Math.max(0, Math.min(100, value));

export default function HomeScreen({ navigation }: any) {
  const vehicle = useVehicleStore((state) => state.vehicle);
  const loadVehicle = useVehicleStore((state) => state.loadVehicle);
  const saveVehicle = useVehicleStore((state) => state.saveVehicle);
  const activeVehicle = vehicle ?? fallbackVehicle;
  const [draftSoC, setDraftSoC] = useState(Math.round(activeVehicle.currentSoC));
  const [isSavingSoC, setIsSavingSoC] = useState(false);
  const [socMessage, setSocMessage] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<ApiChargingSession | null>(null);
  const [openReservation, setOpenReservation] = useState<ApiReservation | null>(null);
  const hasSocChange = draftSoC !== Math.round(activeVehicle.currentSoC);
  const batteryProgress = clampSoC(draftSoC) / 100;

  const estimatedRangeLeft = useMemo(() => {
    const currentSoC = Math.max(0, Math.min(100, activeVehicle.currentSoC));

    if (currentSoC <= 0 || activeVehicle.rangeLeft <= 0) {
      return activeVehicle.rangeLeft;
    }

    const estimatedFullRange = activeVehicle.rangeLeft / (currentSoC / 100);
    return Math.round(Math.max(0, estimatedFullRange * (draftSoC / 100)));
  }, [activeVehicle.currentSoC, activeVehicle.rangeLeft, draftSoC]);

  useEffect(() => {
    loadVehicle();
  }, [loadVehicle]);

  const loadChargingBlockers = useCallback(async () => {
    try {
      const [session, reservations] = await Promise.all([
        api.getActiveChargingSession(),
        api.getMyReservations(),
      ]);

      const reservation = reservations.find(
        (item) =>
          (item.status === 'confirmed' || item.status === 'active') &&
          !item.cancelled_at
      ) ?? null;

      setActiveSession(session);
      setOpenReservation(reservation);
    } catch (error) {
      console.error(error);
      setActiveSession(null);
      setOpenReservation(null);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadChargingBlockers();
    }, [loadChargingBlockers])
  );

  useEffect(() => {
    setDraftSoC(Math.round(activeVehicle.currentSoC));
  }, [activeVehicle.currentSoC]);

  const updateDraftSoC = useCallback((nextSoC: number) => {
    setSocMessage(null);
    setDraftSoC(clampSoC(Math.round(nextSoC)));
  }, []);


  const handleSaveSoC = async () => {
    if (!hasSocChange || isSavingSoC) {
      return;
    }

    setIsSavingSoC(true);
    setSocMessage(null);

    try {
      await saveVehicle({
        make: activeVehicle.make,
        model: activeVehicle.model,
        batteryCapacity: activeVehicle.batteryCapacity,
        currentSoC: draftSoC,
        rangeLeft: estimatedRangeLeft,
      });

      setSocMessage('Saved');
    } catch (error) {
      console.error(error);
      setSocMessage('Save failed');
    } finally {
      setIsSavingSoC(false);
    }
  };

  const RADIUS = 96;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
  const SVG_SIZE = 220;

  const handleRingGesture = useCallback((event: any) => {
    if (isSavingSoC) {
      return;
    }

    const { locationX, locationY } = event.nativeEvent;
    const center = SVG_SIZE / 2;
    const dx = locationX - center;
    const dy = locationY - center;
    const distanceFromCenter = Math.sqrt(dx * dx + dy * dy);

    // Only react when the user is touching near the ring, not the center text.
    if (distanceFromCenter < 64 || distanceFromCenter > 126) {
      return;
    }

    const angleRadians = Math.atan2(dy, dx);
    const angleDegrees = (angleRadians * 180) / Math.PI;

    // Top of the ring = 0%, then clockwise to 100%.
    const normalizedDegrees = (angleDegrees + 90 + 360) % 360;
    const nextSoC = Math.round((normalizedDegrees / 360) * 100);

    updateDraftSoC(nextSoC);
  }, [isSavingSoC, updateDraftSoC]);

  const ringPanResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => !isSavingSoC,
        onMoveShouldSetPanResponder: () => !isSavingSoC,
        onPanResponderGrant: handleRingGesture,
        onPanResponderMove: handleRingGesture,
      }),
    [handleRingGesture, isSavingSoC]
  );

  const chargingBlockReason = activeSession
    ? 'You already have an active charging session. Stop it before requesting another charger.'
    : openReservation
      ? 'You already have a reserved charger. Start or cancel it before requesting another charger.'
      : null;

  const chargingBlockLabel = activeSession
    ? 'Session Active'
    : openReservation
      ? 'Reservation Active'
      : 'Find Chargers';

  const handleFindChargers = () => {
    if (chargingBlockReason) {
      if (isWeb && typeof window !== 'undefined') {
        window.alert(chargingBlockReason);
      } else {
        Alert.alert('Charging unavailable', chargingBlockReason);
      }

      navigation.navigate('Main', { screen: 'Sessions' });
      return;
    }

    navigation.navigate('ChargingRequest');
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logo}>
            <Image
            source={zapRouteLogoSource}
            style={styles.headerLogoWide}
            resizeMode="contain"
          />
          </View>
          <View style={styles.badge}>
            <View style={[styles.badgeDot, webStyles.neonGlowSmall]} />
            <Text style={styles.badgeText}>Vehicle Connected</Text>
          </View>
        </View>

        {/* Battery Ring */}
        <View style={styles.ringWrapper}>
          <View style={styles.outerRing} />
          <View style={isWeb ? { filter: 'drop-shadow(0 0 10px rgba(0,255,0,0.6))' } as any : styles.nativeRingGlowFrame}>
            <Svg width={SVG_SIZE} height={SVG_SIZE} viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}>
              <Circle
                cx={SVG_SIZE / 2}
                cy={SVG_SIZE / 2}
                r={RADIUS}
                fill="transparent"
                stroke="rgba(0,255,0,0.2)"
                strokeWidth={10}
              />

              {!isWeb ? (
                <>
                  <Circle
                    cx={SVG_SIZE / 2}
                    cy={SVG_SIZE / 2}
                    r={RADIUS}
                    fill="transparent"
                    stroke="rgba(0,255,0,0.10)"
                    strokeWidth={24}
                    strokeDasharray={CIRCUMFERENCE}
                    strokeDashoffset={CIRCUMFERENCE * (1 - batteryProgress)}
                    strokeLinecap="round"
                    rotation="-90"
                    origin={`${SVG_SIZE / 2}, ${SVG_SIZE / 2}`}
                  />
                  <Circle
                    cx={SVG_SIZE / 2}
                    cy={SVG_SIZE / 2}
                    r={RADIUS}
                    fill="transparent"
                    stroke="rgba(0,255,0,0.18)"
                    strokeWidth={16}
                    strokeDasharray={CIRCUMFERENCE}
                    strokeDashoffset={CIRCUMFERENCE * (1 - batteryProgress)}
                    strokeLinecap="round"
                    rotation="-90"
                    origin={`${SVG_SIZE / 2}, ${SVG_SIZE / 2}`}
                  />
                </>
              ) : null}

              <Circle
                cx={SVG_SIZE / 2}
                cy={SVG_SIZE / 2}
                r={RADIUS}
                fill="transparent"
                stroke={theme.colors.primary}
                strokeWidth={10}
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={CIRCUMFERENCE * (1 - batteryProgress)}
                strokeLinecap="round"
                rotation="-90"
                origin={`${SVG_SIZE / 2}, ${SVG_SIZE / 2}`}
              />
            </Svg>
            <View style={styles.ringGestureLayer} {...ringPanResponder.panHandlers} />
          </View>
          <View style={styles.ringInner}>
            <Text style={styles.batteryPct}>{draftSoC}%</Text>
            <Text style={styles.batteryRange}>~{estimatedRangeLeft} km range</Text>

            {hasSocChange ? (
              <TouchableOpacity
                style={[
                  styles.ringSaveBtn,
                  isSavingSoC && styles.ringSaveBtnDisabled,
                ]}
                onPress={handleSaveSoC}
                disabled={isSavingSoC}
                activeOpacity={0.85}
              >
                <Text style={styles.ringSaveBtnText}>
                  {isSavingSoC ? 'Saving...' : 'Save'}
                </Text>
              </TouchableOpacity>
            ) : socMessage ? (
              <Text style={styles.inlineSocMessage}>{socMessage}</Text>
            ) : null}
          </View>
        </View>
        {/* Connected Vehicle */}
        <View style={[styles.vehicleCard, webStyles.glass]}>
          <Text style={styles.cardLabel}>CONNECTED VEHICLE</Text>
          <View style={styles.vehicleRow}>
            <View style={styles.vehicleIcon}>
              <Car color={theme.colors.primary} size={24} />
            </View>
            <View style={styles.vehicleInfo}>
              <Text style={styles.vehicleName}>{activeVehicle.make} {activeVehicle.model}</Text>
              <Text style={styles.vehicleSub}>{activeVehicle.batteryCapacity} kWh Battery</Text>
            </View>
          </View>
        </View>

        {chargingBlockReason ? (
          <View style={[styles.activeSessionNotice, webStyles.glass]}>
            <Text style={styles.activeSessionNoticeTitle}>
              {activeSession ? 'Charging session active' : 'Reservation active'}
            </Text>
            <Text style={styles.activeSessionNoticeText}>
              {chargingBlockReason}
            </Text>
          </View>
        ) : null}

        {/* CTA */}
        <NeonButton
          buttonStyle={[styles.primaryBtn, chargingBlockReason && styles.primaryBtnDisabled]}
          onPress={handleFindChargers}
          activeOpacity={0.85}
        >
          <Zap color="#000" fill="#000" size={20} />
          <Text style={styles.primaryBtnText}>{chargingBlockLabel}</Text>
        </NeonButton>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: {
    flex: 1,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    paddingBottom: theme.spacing.lg,
    alignItems: 'center',
  },
  header: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xl,
  },
  logo: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm },
  headerLogoWide: {
    width: 150,
    height: 50,
  },
  logoText: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold' },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceLight,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: theme.radii.full,
    borderWidth: 1,
    borderColor: '#333538',
    gap: 6,
  },
  badgeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.primary,
  },
  badgeText: { color: theme.colors.textMuted, fontSize: 11, fontWeight: '600' },
  ringWrapper: {
    width: 220,
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
    borderRadius: 110,
    position: 'relative',
    overflow: 'visible',
  },
  outerRing: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    borderWidth: 10,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  nativeRingGlowFrame: {
    width: 220,
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringInner: {
    position: 'absolute',
    alignItems: 'center',
    zIndex: 5,
  },
  batteryPct: { color: theme.colors.text, fontSize: 48, fontWeight: 'bold' },
  batteryRange: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2 },
  ringGestureLayer: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    top: 0,
    left: 0,
    zIndex: 3,
  },
  ringSaveBtn: {
    marginTop: 8,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: theme.radii.full,
    backgroundColor: 'rgba(0,255,0,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(0,255,0,0.32)',
    zIndex: 6,
  },
  ringSaveBtnDisabled: {
    opacity: 0.55,
  },
  ringSaveBtnText: {
    color: theme.colors.primary,
    fontSize: 12,
    fontWeight: '800',
  },
  inlineSocMessage: {
    color: theme.colors.primary,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 8,
  },
  fineSocControls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.md,
    marginTop: -theme.spacing.sm,
    marginBottom: theme.spacing.lg,
  },
  fineSocBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: theme.colors.surfaceLight,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fineSocBtnDisabled: {
    opacity: 0.45,
  },
  fineSocLabel: {
    color: theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '600',
  },
  vehicleCard: {
    ...theme.glass,
    width: '100%',
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  cardLabel: {
    color: theme.colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: theme.spacing.md,
  },
  vehicleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
  },
  vehicleIcon: {
    width: 48,
    height: 48,
    borderRadius: theme.radii.md,
    backgroundColor: 'rgba(0,255,0,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  vehicleInfo: {
    flex: 1,
  },
  vehicleName: {
    color: theme.colors.text,
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  vehicleSub: {
    color: theme.colors.textMuted,
    fontSize: 12,
  },
  vehicleSoc: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(0,255,0,0.1)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: theme.radii.full,
  },
  vehicleSocText: {
    color: theme.colors.primary,
    fontSize: 13,
    fontWeight: 'bold',
  },
  activeSessionNotice: {
    ...theme.glass,
    width: '100%',
    borderRadius: theme.radii.xl,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.lg,
    borderColor: 'rgba(245,158,11,0.32)',
  },
  activeSessionNoticeTitle: {
    color: '#f59e0b',
    fontSize: 13,
    fontWeight: '800',
    marginBottom: 4,
  },
  activeSessionNoticeText: {
    color: theme.colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
  },
  primaryBtnDisabled: {
    opacity: 0.55,
  },
  primaryBtn: {
    width: '100%',
    height: 56,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.sm,
  },
  primaryBtnText: { color: '#000', fontSize: 18, fontWeight: 'bold' },
});
