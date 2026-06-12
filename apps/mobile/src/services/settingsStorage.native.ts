import * as Keychain from 'react-native-keychain';

const SETTINGS_STORAGE_SERVICE = 'ev_app_settings';

export const settingsStorage = {
  saveSettings: async (settingsJson: string) => {
    await Keychain.setGenericPassword('app_settings', settingsJson, {
      service: SETTINGS_STORAGE_SERVICE,
    });
  },

  getSettings: async (): Promise<string | null> => {
    const result = await Keychain.getGenericPassword({
      service: SETTINGS_STORAGE_SERVICE,
    });

    if (!result) {
      return null;
    }

    return result.password;
  },

  clearSettings: async () => {
    await Keychain.resetGenericPassword({
      service: SETTINGS_STORAGE_SERVICE,
    });
  },
};
