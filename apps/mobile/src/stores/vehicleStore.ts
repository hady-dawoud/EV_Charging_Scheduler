import { create } from 'zustand';

import { api } from '../services/api';
import type { VehicleProfile, VehicleProfileUpdateRequest } from '../types';

type VehicleState = {
  vehicle: VehicleProfile | null;
  isLoading: boolean;
  error: string | null;
  loadVehicle: () => Promise<VehicleProfile | null>;
  saveVehicle: (payload: VehicleProfileUpdateRequest) => Promise<VehicleProfile>;
};

export const fallbackVehicle: VehicleProfile = {
  id: 'fallback',
  make: 'Tesla',
  model: 'Model 3 LR',
  batteryCapacity: 82,
  currentSoC: 45,
  rangeLeft: 225,
};

export const useVehicleStore = create<VehicleState>((set) => ({
  vehicle: null,
  isLoading: false,
  error: null,

  loadVehicle: async () => {
    set({ isLoading: true, error: null });

    try {
      const vehicle = await api.getMyVehicle();
      set({ vehicle, isLoading: false });
      return vehicle;
    } catch (error) {
      console.error(error);
      set({
        isLoading: false,
        error: 'Could not load vehicle profile.',
      });
      return null;
    }
  },

  saveVehicle: async (payload) => {
    set({ isLoading: true, error: null });

    try {
      const vehicle = await api.updateMyVehicle(payload);
      set({ vehicle, isLoading: false });
      return vehicle;
    } catch (error) {
      console.error(error);
      set({
        isLoading: false,
        error: 'Could not save vehicle profile.',
      });
      throw error;
    }
  },
}));
