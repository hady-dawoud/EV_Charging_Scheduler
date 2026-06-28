import React from 'react';
import {
  requireNativeComponent,
  StyleProp,
  StyleSheet,
  Text,
  UIManager,
  View,
  ViewStyle,
} from 'react-native';
import type { StationMapLocation } from '../data/demoLocations';
import { theme } from '../theme';

type StationMapProps = {
  stationLocation: StationMapLocation;
  stationName: string;
  style?: StyleProp<ViewStyle>;
};

type NativeOsmStationMapProps = {
  latitude: number;
  longitude: number;
  stationName: string;
  stationAddress: string;
  style?: StyleProp<ViewStyle>;
};

const OsmStationMapView =
  requireNativeComponent<NativeOsmStationMapProps>('OsmStationMapView');
const hasOsmStationMapView =
  UIManager.getViewManagerConfig('OsmStationMapView') != null;

export function StationMap({ stationLocation, stationName, style }: StationMapProps) {
  if (!hasOsmStationMapView) {
    return (
      <View style={[styles.unavailableMap, style]}>
        <Text style={styles.unavailableTitle}>Map needs APK rebuild</Text>
        <Text style={styles.unavailableText}>
          Reinstall the Android app so the native OSM map view is available.
        </Text>
      </View>
    );
  }

  return (
    <OsmStationMapView
      latitude={stationLocation.latitude}
      longitude={stationLocation.longitude}
      stationAddress={stationLocation.address}
      stationName={stationName}
      style={style}
    />
  );
}

const styles = StyleSheet.create({
  unavailableMap: {
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    justifyContent: 'center',
    paddingHorizontal: theme.spacing.xl,
  },
  unavailableTitle: {
    color: theme.colors.text,
    fontSize: 16,
    fontWeight: '800',
    marginBottom: theme.spacing.xs,
    textAlign: 'center',
  },
  unavailableText: {
    color: theme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
  },
});
