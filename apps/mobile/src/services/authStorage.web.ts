const REFRESH_TOKEN_KEY = 'ev-smart-charging.refresh-token';

export const authStorage = {
  saveRefreshToken: async (refreshToken: string) => {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },

  getRefreshToken: async () => {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  clearRefreshToken: async () => {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
