import { View, StyleSheet, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing } from '@/theme';

interface ScreenProps {
  children: React.ReactNode;
  padded?: boolean;
  style?: ViewStyle;
}

export function Screen({ children, padded = true, style }: ScreenProps) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={[styles.container, padded && styles.padded, style]}>
        {children}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  } as ViewStyle,
  container: {
    flex: 1,
    backgroundColor: colors.background,
  } as ViewStyle,
  padded: {
    paddingHorizontal: spacing.lg,
  } as ViewStyle,
});
