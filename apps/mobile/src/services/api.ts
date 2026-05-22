import { Platform } from 'react-native';
import { mockSessions, mockUser, mockVehicle } from '../data/mockData';
import {
  ApiRecommendationsResponse,
  MobileRecommendationRequest,
} from '../types';

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(() => resolve(), ms));

const LOCAL_API_BASE_URL =
  Platform.OS === 'android'
    ? 'http://10.0.2.2:8000'
    : 'http://127.0.0.1:8000';

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || LOCAL_API_BASE_URL;


const mapChargerType = (chargerType: MobileRecommendationRequest['chargerType']) => {
  switch (chargerType) {
    case 'ac':
      return 'AC';
    case 'dc':
      return 'Rapid';
    default:
      return 'Any';
  }
};

const calculateRequestedEnergyKwh = (targetSoc: number) => {
  const deltaSoc = Math.max(0, targetSoc - mockVehicle.currentSoC) / 100;
  return Number((deltaSoc * mockVehicle.batteryCapacity).toFixed(3));
};

export const api = {
  login: async () => {
    await delay(1500);
    return { user: mockUser, vehicle: mockVehicle };
  },

  getRecommendations: async (
    request: MobileRecommendationRequest
  ): Promise<ApiRecommendationsResponse> => {
    const now = new Date();
    const latestFinish = new Date(now.getTime() + 2 * 60 * 60 * 1000);
    const requestIdSuffix = Date.now().toString();

    const payload = {
      client_request_id: `mobile-${requestIdSuffix}`,
      request_timestamp: now.toISOString(),
      current_latitude: 56.462,
      current_longitude: -2.9707,
      target_soc: request.targetSoc,
      current_soc: mockVehicle.currentSoC,
      battery_kwh: mockVehicle.batteryCapacity,
      requested_energy_kwh: calculateRequestedEnergyKwh(request.targetSoc),
      preference_mode: request.preferenceMode,
      charger_type: mapChargerType(request.chargerType),
      latest_finish_ts: latestFinish.toISOString(),
      source_type: 'external_live',
      request_id: `mobile-live-${requestIdSuffix}`,
      zone_id: 'zone_central_waterfront',
      metadata: {
        channel: 'mobile-app',
      },
    };

    const response = await fetch(`${API_BASE_URL}/recommendations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Recommendations request failed (${response.status}): ${errorText}`
      );
    }

    return response.json();
  },

  getSessions: async () => {
    await delay(800);
    return mockSessions;
  },

  reserveStation: async (_stationId: string) => {
    await delay(1500);
    return { success: true, reservationId: Math.random().toString(36).substr(2, 9) };
  },
};
