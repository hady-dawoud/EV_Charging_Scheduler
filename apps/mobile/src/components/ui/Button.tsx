import {
  Pressable,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, spacing, borderRadius } from '@/theme';

type ButtonVariant = 'primary' | 'secondary';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
  style,
}: ButtonProps) {
  const isPrimary = variant === 'primary';
  const isDisabled = disabled || loading;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        isPrimary ? styles.primary : styles.secondary,
        isDisabled && styles.disabled,
        pressed && !isDisabled && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator
          color={isPrimary ? colors.background : colors.primary}
          size="small"
        />
      ) : (
        <Text
          style={[
            styles.text,
            isPrimary ? styles.textPrimary : styles.textSecondary,
            isDisabled && styles.textDisabled,
          ]}
        >
          {title}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing['2xl'],
    borderRadius: borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
  } as ViewStyle,
  primary: {
    backgroundColor: colors.primary,
  } as ViewStyle,
  secondary: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: colors.primary,
  } as ViewStyle,
  disabled: {
    opacity: 0.5,
  } as ViewStyle,
  pressed: {
    opacity: 0.8,
  } as ViewStyle,
  text: {
    fontSize: 16,
    fontWeight: '600',
  } as TextStyle,
  textPrimary: {
    color: colors.background,
  } as TextStyle,
  textSecondary: {
    color: colors.primary,
  } as TextStyle,
  textDisabled: {
    opacity: 0.7,
  } as TextStyle,
});
