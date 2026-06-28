import { create } from 'zustand';

import { settingsStorage } from '../services/settingsStorage';
import type { AppPreferences, NotificationPreferences } from '../types';

export const defaultAppPreferences: AppPreferences = {
  distanceUnit: 'km',
  currency: 'GBP',
  notifications: {
    reservationReminders: true,
    chargingSessionUpdates: true,
    recommendationAlerts: false,
  },
};

type SettingsState = {
  preferences: AppPreferences;
  isLoaded: boolean;
  loadPreferences: () => Promise<void>;
  updatePreferences: (patch: Partial<AppPreferences>) => Promise<void>;
  updateNotifications: (patch: Partial<NotificationPreferences>) => Promise<void>;
  resetPreferences: () => Promise<void>;
};

export const useSettingsStore = create<SettingsState>((set, get) => ({
  preferences: defaultAppPreferences,
  isLoaded: false,

  loadPreferences: async () => {
    const saved = await settingsStorage.getSettings();

    if (!saved) {
      set({ preferences: defaultAppPreferences, isLoaded: true });
      return;
    }

    try {
      const parsed = JSON.parse(saved) as Partial<AppPreferences>;
      const currency =
        parsed.currency === 'EUR' || parsed.currency === 'GBP'
          ? parsed.currency
          : parsed.currency === 'EGP'
            ? 'EUR'
            : defaultAppPreferences.currency;
      const distanceUnit =
        parsed.distanceUnit === 'mi' || parsed.distanceUnit === 'km'
          ? parsed.distanceUnit
          : defaultAppPreferences.distanceUnit;

      set({
        preferences: {
          ...defaultAppPreferences,
          ...parsed,
          currency,
          distanceUnit,
          notifications: {
            ...defaultAppPreferences.notifications,
            ...(parsed.notifications ?? {}),
          },
        },
        isLoaded: true,
      });
    } catch {
      set({ preferences: defaultAppPreferences, isLoaded: true });
    }
  },

  updatePreferences: async (patch) => {
    const nextPreferences: AppPreferences = {
      ...get().preferences,
      ...patch,
      notifications: {
        ...get().preferences.notifications,
        ...(patch.notifications ?? {}),
      },
    };

    set({ preferences: nextPreferences, isLoaded: true });
    await settingsStorage.saveSettings(JSON.stringify(nextPreferences));
  },

  updateNotifications: async (patch) => {
    const current = get().preferences;
    const nextPreferences: AppPreferences = {
      ...current,
      notifications: {
        ...current.notifications,
        ...patch,
      },
    };

    set({ preferences: nextPreferences, isLoaded: true });
    await settingsStorage.saveSettings(JSON.stringify(nextPreferences));
  },

  resetPreferences: async () => {
    set({ preferences: defaultAppPreferences, isLoaded: true });
    await settingsStorage.clearSettings();
  },
}));
