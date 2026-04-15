import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, MapPin, Zap, Minus, Plus } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { theme, webStyles } from '../theme';
import {
  RecommendationChargerType,
  RecommendationPreferenceMode,
  RootStackParamList,
} from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ChargingRequest'>;

export default function ChargingRequestScreen({ navigation }: Props) {
  const [targetSoC, setTargetSoC] = useState(80);
  const [optMode, setOptMode] =
    useState<RecommendationPreferenceMode>('cheapest');
  const [chargerType, setChargerType] =
    useState<RecommendationChargerType>('any');

  const handleFindRecommendations = () => {
    navigation.navigate('LoadingRecommendations', {
      request: {
        targetSoc: targetSoC,
        preferenceMode: optMode,
        chargerType,
      },
    });
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={24} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Charging Request</Text>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <Text style={styles.cardLabel}>CURRENT LOCATION</Text>
          <View style={styles.locationRow}>
            <MapPin color={theme.colors.primary} size={20} />
            <Text style={styles.locationText}>Central Dundee (Demo Runtime)</Text>
          </View>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <Text style={styles.cardLabel}>TARGET CHARGE</Text>
          <View style={styles.targetControls}>
            <TouchableOpacity
              style={styles.controlBtn}
              onPress={() => setTargetSoC((p) => Math.max(0, p - 5))}
            >
              <Minus color={theme.colors.textMuted} size={24} />
            </TouchableOpacity>
            <Text style={styles.targetValue}>{targetSoC}%</Text>
            <TouchableOpacity
              style={styles.controlBtn}
              onPress={() => setTargetSoC((p) => Math.min(100, p + 5))}
            >
              <Plus color={theme.colors.textMuted} size={24} />
            </TouchableOpacity>
          </View>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <Text style={styles.cardLabel}>OPTIMIZATION MODE</Text>
          <View style={styles.segmented}>
            {(['cheapest', 'fastest', 'closest'] as RecommendationPreferenceMode[]).map((mode) => (
              <TouchableOpacity
                key={mode}
                style={[styles.segment, optMode === mode && styles.segmentActive]}
                onPress={() => setOptMode(mode)}
              >
                <Text style={[styles.segmentText, optMode === mode && styles.segmentTextActive]}>
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <Text style={styles.cardLabel}>CHARGER TYPE</Text>
          <View style={styles.typeGrid}>
            {(['any', 'ac', 'dc'] as RecommendationChargerType[]).map((type) => (
              <TouchableOpacity
                key={type}
                style={[styles.typeBtn, chargerType === type && styles.typeBtnActive]}
                onPress={() => setChargerType(type)}
              >
                <Zap
                  color={chargerType === type ? theme.colors.primary : theme.colors.textMuted}
                  size={18}
                />
                <Text style={[styles.typeBtnText, chargerType === type && { color: theme.colors.primary }]}>
                  {type.toUpperCase()}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <TouchableOpacity
          style={[styles.primaryBtn, webStyles.neonGlow]}
          onPress={handleFindRecommendations}
          activeOpacity={0.85}
        >
          <Zap color="#000" fill="#000" size={20} />
          <Text style={styles.primaryBtnText}>Find Best Options</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 40 },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md, marginBottom: theme.spacing.xl },
  backBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: theme.colors.surfaceLight,
    alignItems: 'center', justifyContent: 'center',
  },
  pageTitle: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold' },
  card: {
    ...theme.glass,
    borderRadius: theme.radii.xxl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  cardLabel: {
    color: theme.colors.textMuted, fontSize: 10, fontWeight: 'bold',
    letterSpacing: 2, marginBottom: theme.spacing.md,
  },
  locationRow: {
    flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm,
    backgroundColor: 'rgba(255,255,255,0.05)', padding: 12,
    borderRadius: theme.radii.md, borderWidth: 1, borderColor: theme.colors.border,
  },
  locationText: { color: theme.colors.text, fontSize: 14, fontWeight: '500' },
  targetControls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    paddingHorizontal: theme.spacing.md,
  },
  controlBtn: {
    width: 48,
    height: 48,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  targetValue: { color: theme.colors.text, fontSize: 48, fontWeight: 'bold' },
  segmented: {
    flexDirection: 'row', backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: theme.radii.md, padding: 4,
    borderWidth: 1, borderColor: theme.colors.border,
  },
  segment: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: theme.radii.sm },
  segmentActive: { backgroundColor: 'rgba(255,255,255,0.1)' },
  segmentText: { color: theme.colors.textMuted, fontSize: 13, fontWeight: '500' },
  segmentTextActive: { color: theme.colors.text },
  typeGrid: { flexDirection: 'row', gap: theme.spacing.sm },
  typeBtn: {
    flex: 1, height: 70, borderRadius: theme.radii.lg,
    backgroundColor: 'rgba(255,255,255,0.05)',
    alignItems: 'center', justifyContent: 'center', gap: 6,
    borderWidth: 1, borderColor: theme.colors.border,
  },
  typeBtnActive: { backgroundColor: 'rgba(0,255,0,0.1)', borderColor: theme.colors.primary },
  typeBtnText: { color: theme.colors.textMuted, fontSize: 11, fontWeight: 'bold' },
  primaryBtn: {
    height: 56, backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.lg, flexDirection: 'row',
    alignItems: 'center', justifyContent: 'center', gap: theme.spacing.sm,
  },
  primaryBtnText: { color: '#000', fontSize: 18, fontWeight: 'bold' },
});