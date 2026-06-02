import React, { useEffect } from 'react';
import { StatusBar, StyleSheet, View } from 'react-native';
import { createNavigationContainerRef, NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { api } from './src/services/api';
import { useAuthStore } from './src/stores/authStore';
import { theme } from './src/theme';
import type { RootStackParamList } from './src/types';
import MainTabs from './src/components/MainTabs';
import SplashScreen from './src/screens/SplashScreen';
import LoginScreen from './src/screens/LoginScreen';
import SignupScreen from './src/screens/SignupScreen';
import ChargingRequestScreen from './src/screens/ChargingRequestScreen';
import LoadingRecommendationsScreen from './src/screens/LoadingRecommendationsScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import StationDetailsScreen from './src/screens/StationDetailsScreen';
import ReservationConfirmScreen from './src/screens/ReservationConfirmScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();
const navigationRef = createNavigationContainerRef<RootStackParamList>();

export default function App() {
  const expireSession = useAuthStore((state) => state.expireSession);

  useEffect(() => {
    api.setAuthExpiredHandler(() => {
      expireSession('Session expired. Please sign in again.');

      if (navigationRef.isReady()) {
        navigationRef.reset({
          index: 0,
          routes: [{ name: 'Login' }],
        });
      }
    });

    return () => {
      api.setAuthExpiredHandler(null);
    };
  }, [expireSession]);

  return (
    <View style={styles.root}>
      <NavigationContainer
        ref={navigationRef}
        theme={{
          dark: true,
          colors: {
            primary: theme.colors.primary,
            background: theme.colors.background,
            card: theme.colors.surface,
            text: theme.colors.text,
            border: theme.colors.border,
            notification: theme.colors.primary,
          },
        }}
      >
        <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
        <Stack.Navigator
          initialRouteName="Splash"
          screenOptions={{ headerShown: false, animation: 'fade' }}
        >
          <Stack.Screen name="Splash" component={SplashScreen} />
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Signup" component={SignupScreen} />
          <Stack.Screen name="Main" component={MainTabs} />
          <Stack.Screen name="ChargingRequest" component={ChargingRequestScreen} />
          <Stack.Screen name="LoadingRecommendations" component={LoadingRecommendationsScreen} />
          <Stack.Screen name="Results" component={ResultsScreen} />
          <Stack.Screen name="StationDetails" component={StationDetailsScreen} />
          <Stack.Screen name="ReservationConfirm" component={ReservationConfirmScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
});
