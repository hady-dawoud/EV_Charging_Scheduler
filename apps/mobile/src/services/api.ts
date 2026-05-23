import { Platform } from 'react-native';

import { mockVehicle } from '../data/mockData';
import type {
  ApiActiveChargingSessionResponse,
  ApiChargingSession,
  ApiChargingSessionsResponse,
  ApiRecommendationsResponse,
  ApiReservationsResponse,
  ApiReservation,
  AuthResponse,
  AuthTokens,
  LoginRequest,
  MobileRecommendationRequest,
  CreateReservationRequest,
  RegisterRequest,
  User,
} from '../types';

const LOCAL_API_BASE_URL =
  Platform.OS === 'android'
    ? 'http://10.0.2.2:8000'
    : 'http://127.0.0.1:8000';

const API_BASE_URL =
  Platform.OS === 'web'
    ? 'http://localhost:8000'
    : LOCAL_API_BASE_URL;

let accessTokenMemory: string | null = null;

type BackendUser = {
  id: string;
  full_name: string;
  email: string;
};

type BackendAuthResponse = {
  user: BackendUser;
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type BackendTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

class ApiError extends Error {
  status: number;
  body: string;

  constructor(message: string, status: number, body: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

const mapBackendUser = (user: BackendUser): User => ({
  id: user.id,
  name: user.full_name,
  email: user.email,
});

const mapAuthResponse = (body: BackendAuthResponse): AuthResponse => ({
  user: mapBackendUser(body.user),
  accessToken: body.access_token,
  refreshToken: body.refresh_token,
  tokenType: body.token_type,
});

const mapTokenResponse = (body: BackendTokenResponse): AuthTokens => ({
  accessToken: body.access_token,
  refreshToken: body.refresh_token,
  tokenType: body.token_type,
});

const requestJson = async <T>(
  path: string,
  options: RequestInit = {},
  overrideAccessToken?: string | null
): Promise<T> => {
  const token = overrideAccessToken ?? accessTokenMemory;
  const headers = new Headers(options.headers);

  headers.set('Accept', 'application/json');

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const responseText = await response.text();

  if (!response.ok) {
    throw new ApiError(
      `Request failed (${response.status})`,
      response.status,
      responseText
    );
  }

  if (!responseText) {
    return undefined as T;
  }

  return JSON.parse(responseText) as T;
};

const mapChargerType = (chargerType: MobileRecommendationRequest['chargerType']) => {
  switch (chargerType) {
    case 'ac':
      return 'ac';
    case 'dc':
      return 'rapid';
    default:
      return 'Any';
  }
};

const calculateRequestedEnergyKwh = (targetSoc: number) => {
  const deltaSoc = Math.max(0, targetSoc - mockVehicle.currentSoC) / 100;
  return Number((deltaSoc * mockVehicle.batteryCapacity).toFixed(3));
};

export const api = {
  setAccessToken: (accessToken: string | null) => {
    accessTokenMemory = accessToken;
  },

  login: async (payload: LoginRequest): Promise<AuthResponse> => {
    const body = await requestJson<BackendAuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    const mapped = mapAuthResponse(body);
    accessTokenMemory = mapped.accessToken;

    return mapped;
  },

  register: async (payload: RegisterRequest): Promise<AuthResponse> => {
    const body = await requestJson<BackendAuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    const mapped = mapAuthResponse(body);
    accessTokenMemory = mapped.accessToken;

    return mapped;
  },

  refresh: async (refreshToken: string, deviceId: string): Promise<AuthTokens> => {
    const body = await requestJson<BackendTokenResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({
        refresh_token: refreshToken,
        device_id: deviceId,
      }),
    });

    const mapped = mapTokenResponse(body);
    accessTokenMemory = mapped.accessToken;

    return mapped;
  },

  getMe: async (accessToken?: string): Promise<User> => {
    const body = await requestJson<BackendUser>(
      '/auth/me',
      {
        method: 'GET',
      },
      accessToken
    );

    return mapBackendUser(body);
  },

  logout: async (refreshToken: string) => {
    await requestJson<{ success: boolean }>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    accessTokenMemory = null;
  },

  getRecommendations: async (
    request: MobileRecommendationRequest
  ): Promise<ApiRecommendationsResponse> => {
    const payload = {
      latitude: 56.462,
      longitude: -2.9707,
      battery_level: mockVehicle.currentSoC,
      target_battery_level: request.targetSoc,
      battery_kwh: mockVehicle.batteryCapacity,
      requested_energy_kwh: calculateRequestedEnergyKwh(request.targetSoc),
      preference_mode: request.preferenceMode,
      connector_type: mapChargerType(request.chargerType),
      latest_finish_minutes_from_now: 120,
      zone_id: 'zone_central_waterfront',
      metadata: {
        channel: 'mobile-app',
      },
    };

    return requestJson<ApiRecommendationsResponse>('/mobile/recommendations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getMyChargingSessions: async (): Promise<ApiChargingSession[]> => {
    const response = await requestJson<ApiChargingSessionsResponse>('/sessions/me', {
      method: 'GET',
    });

    return response.sessions;
  },

  getActiveChargingSession: async (): Promise<ApiChargingSession | null> => {
    const response = await requestJson<ApiActiveChargingSessionResponse>('/sessions/active', {
      method: 'GET',
    });

    return response.session;
  },


  createReservation: async (
    payload: CreateReservationRequest
  ): Promise<ApiReservation> => {
    return requestJson<ApiReservation>('/reservations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getMyReservations: async (): Promise<ApiReservation[]> => {
    const response = await requestJson<ApiReservationsResponse>('/reservations/me', {
      method: 'GET',
    });

    return response.reservations;
  },

};
