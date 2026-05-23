import { create } from 'zustand';

import { api } from '../services/api';
import type { User } from '../types';

type AuthState = {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  setSession: (user: User, accessToken: string) => void;
  clearSession: () => void;
  setBootstrapping: (value: boolean) => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isBootstrapping: true,

  setSession: (user, accessToken) => {
    api.setAccessToken(accessToken);

    set({
      user,
      accessToken,
      isAuthenticated: true,
      isBootstrapping: false,
    });
  },

  clearSession: () => {
    api.setAccessToken(null);

    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isBootstrapping: false,
    });
  },

  setBootstrapping: (value) => {
    set({ isBootstrapping: value });
  },
}));
