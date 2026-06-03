const SETTINGS_STORAGE_KEY = 'ev_app_settings';

export const settingsStorage = {
  saveSettings: async (settingsJson: string) => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, settingsJson);
  },

  getSettings: async (): Promise<string | null> => {
    return window.localStorage.getItem(SETTINGS_STORAGE_KEY);
  },

  clearSettings: async () => {
    window.localStorage.removeItem(SETTINGS_STORAGE_KEY);
  },
};
