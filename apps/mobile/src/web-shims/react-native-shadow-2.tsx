import React from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';

type ShadowProps = {
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  distance?: number;
  startColor?: string;
  endColor?: string;
  offset?: [number, number];
  stretch?: boolean;
  disabled?: boolean;
};

export function Shadow({ children, style }: ShadowProps) {
  return <View style={style}>{children}</View>;
}

export default Shadow;
