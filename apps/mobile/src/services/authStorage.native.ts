import * as Keychain from 'react-native-keychain';

const REFRESH_TOKEN_SERVICE = 'ev-smart-charging.refresh-token';

export const authStorage = {
  saveRefreshToken: async (refreshToken: string) => {
    await Keychain.setGenericPassword('refresh_token', refreshToken, {
      service: REFRESH_TOKEN_SERVICE,
    });
  },

  getRefreshToken: async () => {
    const result = await Keychain.getGenericPassword({
      service: REFRESH_TOKEN_SERVICE,
    });

    if (!result) {
      return null;
    }

    return result.password;
  },

  clearRefreshToken: async () => {
    await Keychain.resetGenericPassword({
      service: REFRESH_TOKEN_SERVICE,
    });
  },
};
