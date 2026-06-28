import React from 'react';
import { StyleProp, View, ViewStyle } from 'react-native';
import { buildGoogleMapsEmbedUrl, type StationMapLocation } from '../data/demoLocations';

type StationMapProps = {
  stationLocation: StationMapLocation;
  stationName: string;
  style?: StyleProp<ViewStyle>;
};

export function StationMap({ stationLocation, stationName, style }: StationMapProps) {
  const mapUrl = buildGoogleMapsEmbedUrl(stationLocation);

  return (
    <View style={style}>
      {React.createElement('iframe', {
        key: mapUrl,
        src: mapUrl,
        title: `${stationName} map`,
        style: {
          border: 0,
          width: '100%',
          height: '100%',
        },
        loading: 'lazy',
      })}
    </View>
  );
}
