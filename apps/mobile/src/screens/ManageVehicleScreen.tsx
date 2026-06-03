import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardTypeOptions,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Car, ChevronLeft } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { NeonButton } from '../components/NeonButton';
import { fallbackVehicle, useVehicleStore } from '../stores/vehicleStore';
import { theme, webStyles } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ManageVehicle'>;

type FieldProps = {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: KeyboardTypeOptions;
};

function Field({ label, value, onChangeText, keyboardType = 'default' }: FieldProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        placeholderTextColor={theme.colors.textMuted}
      />
    </View>
  );
}

export default function ManageVehicleScreen({ navigation }: Props) {
  const vehicle = useVehicleStore((state) => state.vehicle);
  const isLoading = useVehicleStore((state) => state.isLoading);
  const error = useVehicleStore((state) => state.error);
  const loadVehicle = useVehicleStore((state) => state.loadVehicle);
  const saveVehicle = useVehicleStore((state) => state.saveVehicle);

  const activeVehicle = vehicle ?? fallbackVehicle;

  const [make, setMake] = useState(activeVehicle.make);
  const [model, setModel] = useState(activeVehicle.model);
  const [batteryCapacity, setBatteryCapacity] = useState(String(activeVehicle.batteryCapacity));
  const [currentSoC, setCurrentSoC] = useState(String(activeVehicle.currentSoC));
  const [rangeLeft, setRangeLeft] = useState(String(activeVehicle.rangeLeft));
  const [localError, setLocalError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    loadVehicle();
  }, [loadVehicle]);

  useEffect(() => {
    const nextVehicle = vehicle ?? fallbackVehicle;
    setMake(nextVehicle.make);
    setModel(nextVehicle.model);
    setBatteryCapacity(String(nextVehicle.batteryCapacity));
    setCurrentSoC(String(nextVehicle.currentSoC));
    setRangeLeft(String(nextVehicle.rangeLeft));
  }, [vehicle]);

  const parseNumber = (value: string) => Number(value.replace(',', '.'));

  const handleSave = async () => {
    setLocalError(null);
    setSavedMessage(null);

    const parsedBatteryCapacity = parseNumber(batteryCapacity);
    const parsedCurrentSoC = parseNumber(currentSoC);
    const parsedRangeLeft = parseNumber(rangeLeft);

    if (!make.trim() || !model.trim()) {
      setLocalError('Make and model are required.');
      return;
    }

    if (!Number.isFinite(parsedBatteryCapacity) || parsedBatteryCapacity <= 0) {
      setLocalError('Battery capacity must be greater than 0.');
      return;
    }

    if (!Number.isFinite(parsedCurrentSoC) || parsedCurrentSoC < 0 || parsedCurrentSoC > 100) {
      setLocalError('Current charge must be between 0 and 100.');
      return;
    }

    if (!Number.isFinite(parsedRangeLeft) || parsedRangeLeft < 0) {
      setLocalError('Range must be 0 or greater.');
      return;
    }

    try {
      await saveVehicle({
        make: make.trim(),
        model: model.trim(),
        batteryCapacity: parsedBatteryCapacity,
        currentSoC: parsedCurrentSoC,
        rangeLeft: parsedRangeLeft,
      });

      setSavedMessage('Vehicle profile saved.');
    } catch {
      setLocalError('Could not save vehicle profile.');
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={24} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Manage Vehicle</Text>
        </View>

        <View style={[styles.card, webStyles.glass]}>
          <View style={styles.cardHeader}>
            <Car color={theme.colors.primary} size={22} />
            <Text style={styles.cardLabel}>VEHICLE PROFILE</Text>
          </View>

          <Field label="Make" value={make} onChangeText={setMake} />
          <Field label="Model" value={model} onChangeText={setModel} />
          <Field
            label="Battery capacity (kWh)"
            value={batteryCapacity}
            onChangeText={setBatteryCapacity}
            keyboardType="numeric"
          />
          <Field
            label="Current charge (%)"
            value={currentSoC}
            onChangeText={setCurrentSoC}
            keyboardType="numeric"
          />
          <Field
            label="Estimated range (km)"
            value={rangeLeft}
            onChangeText={setRangeLeft}
            keyboardType="numeric"
          />

          {localError || error ? <Text style={styles.errorText}>{localError ?? error}</Text> : null}
          {savedMessage ? <Text style={styles.successText}>{savedMessage}</Text> : null}
        </View>

        <NeonButton
          buttonStyle={styles.primaryBtn}
          onPress={handleSave}
          disabled={isLoading}
          activeOpacity={0.85}
        >
          {isLoading ? (
            <ActivityIndicator color="#000" />
          ) : (
            <Text style={styles.primaryBtnText}>Save Vehicle</Text>
          )}
        </NeonButton>
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
  pageTitle: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: 'bold',
  },
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
  field: {
    marginBottom: theme.spacing.md,
  },
  fieldLabel: {
    color: theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 8,
  },
  input: {
    height: 52,
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surfaceLight,
    color: theme.colors.text,
    paddingHorizontal: theme.spacing.md,
    fontSize: 15,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 13,
    marginTop: theme.spacing.xs,
  },
  successText: {
    color: theme.colors.primary,
    fontSize: 13,
    marginTop: theme.spacing.xs,
    fontWeight: '700',
  },
  primaryBtn: {
    height: 56,
    backgroundColor: theme.colors.primary,
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
