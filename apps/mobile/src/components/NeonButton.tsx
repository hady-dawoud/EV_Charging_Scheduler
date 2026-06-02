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
import { Shadow } from 'react-native-shadow-2';
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

  if (isWeb) {
    return (
      <View style={[styles.frame, frameStyle]}>
        <TouchableOpacity
          {...touchableProps}
          style={[styles.button, webGlow, buttonStyle]}
        >
          {children}
        </TouchableOpacity>
      </View>
    );
  }

  const innerDistance = glow === 'small' ? 2 : 3;
  const innerStartColor = glow === 'small'
    ? 'rgba(0, 255, 0, 0.26)'
    : 'rgba(0, 255, 0, 0.39)';

  const outerDistance = glow === 'small' ? 4 : 5;
  const outerStartColor = glow === 'small'
    ? 'rgba(0, 255, 0, 0.13)'
    : 'rgba(0, 255, 0, 0.26)';

  const outer2Distance = glow === 'small' ? 6 : 7;
  const outer2StartColor = glow === 'small'
    ? 'rgba(0, 255, 0, 0.1)'
    : 'rgba(0, 255, 0, 0.13)';

  const endColor = 'rgba(0, 255, 0, 0)';

  return (
    <View style={[styles.frame, frameStyle]}>
      <Shadow
        distance={outer2Distance}
        startColor={outer2StartColor}
        endColor={endColor}
        offset={[0, 0]}
        stretch
        style={styles.shadow}
      >
        <Shadow
          distance={outerDistance}
          startColor={outerStartColor}
          endColor={endColor}
          offset={[0, 0]}
          stretch
          style={styles.shadow}
        >
          <Shadow
            distance={innerDistance}
            startColor={innerStartColor}
            endColor={endColor}
            offset={[0, 0]}
            stretch
            style={styles.shadow}
          >
            <TouchableOpacity
              {...touchableProps}
              style={[styles.button, buttonStyle]}
            >
              {children}
            </TouchableOpacity>
          </Shadow>
        </Shadow>
      </Shadow>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    minHeight: 56,
    overflow: 'visible',
    width: '100%',
  },
  shadow: {
    width: '100%',
    borderRadius: 16,
  },
  button: {
    height: 56,
  },
});
