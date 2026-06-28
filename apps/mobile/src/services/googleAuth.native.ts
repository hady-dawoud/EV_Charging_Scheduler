import { GoogleSignin } from '@react-native-google-signin/google-signin';

import { GOOGLE_WEB_CLIENT_ID } from '../config/google';

let isConfigured = false;

const configureGoogleSignin = () => {
  if (isConfigured) {
    return;
  }

  GoogleSignin.configure({
    webClientId: GOOGLE_WEB_CLIENT_ID,
    offlineAccess: false,
  });

  isConfigured = true;
};

export const signInWithGoogle = async (): Promise<string> => {
  configureGoogleSignin();

  await GoogleSignin.hasPlayServices({
    showPlayServicesUpdateDialog: true,
  });

  await GoogleSignin.signIn();

  const tokens = await GoogleSignin.getTokens();

  if (!tokens.idToken) {
    throw new Error('Google did not return an ID token.');
  }

  return tokens.idToken;
};
