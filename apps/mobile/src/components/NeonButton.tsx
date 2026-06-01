import React from 'react';
import {
  Platform,
  StyleProp,
  StyleSheet,
  TouchableOpacity,
  TouchableOpacityProps,
  View,
  ViewStyle,
} from 'react-native';
import Svg, { Defs, RadialGradient, Rect, Stop } from 'react-native-svg';
import { webStyles } from '../theme';

const isWeb = Platform.OS === 'web';

type NeonButtonProps = TouchableOpacityProps & {
  buttonStyle?: StyleProp<ViewStyle>;
  children: React.ReactNode;
  frameStyle?: StyleProp<ViewStyle>;
  glow?: 'normal' | 'small';
};

export function NeonButton({
  buttonStyle,
  children,
  frameStyle,
  glow = 'normal',
  ...touchableProps
}: NeonButtonProps) {
  const webGlow = glow === 'small' ? webStyles.neonGlowSmall : webStyles.neonGlow;

  return (
    <View style={[styles.frame, frameStyle]}>
      {!isWeb && (
        <Svg
          width="100%"
          height="100%"
          viewBox="0 0 360 96"
          preserveAspectRatio="none"
          style={styles.nativeGlow}
          pointerEvents="none"
        >
          <Defs>
            <RadialGradient id="neonButtonGlow" cx="50%" cy="50%" rx="58%" ry="64%">
              <Stop offset="0%" stopColor="#00FF00" stopOpacity={glow === 'small' ? '0.16' : '0.24'} />
              <Stop offset="48%" stopColor="#00FF00" stopOpacity={glow === 'small' ? '0.09' : '0.14'} />
              <Stop offset="76%" stopColor="#00FF00" stopOpacity={glow === 'small' ? '0.035' : '0.055'} />
              <Stop offset="100%" stopColor="#00FF00" stopOpacity="0" />
            </RadialGradient>
          </Defs>
          <Rect x="0" y="0" width="360" height="96" rx="32" fill="url(#neonButtonGlow)" opacity="0.38" />
          <Rect x="10" y="10" width="340" height="76" rx="24" fill="url(#neonButtonGlow)" opacity="0.5" />
          <Rect x="20" y="20" width="320" height="56" rx="16" fill="url(#neonButtonGlow)" />
        </Svg>
      )}
      <TouchableOpacity
        {...touchableProps}
        style={[styles.button, isWeb && webGlow, buttonStyle]}
      >
        {children}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    height: 56,
    overflow: 'visible',
    width: '100%',
  },
  nativeGlow: {
    bottom: -20,
    left: -20,
    position: 'absolute',
    right: -20,
    top: -20,
  },
  button: {
    height: 56,
  },
});
