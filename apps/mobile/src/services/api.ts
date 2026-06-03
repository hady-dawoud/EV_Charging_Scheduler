import { Platform } from 'react-native';

import { authStorage } from './authStorage';
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
  PasswordResetConfirmResponse,
  PasswordResetRequestResponse,
  CreateReservationRequest,
  RegisterRequest,
  User,
  VehicleProfile,
  VehicleProfileUpdateRequest,
} from '../types';

const LOCAL_API_BASE_URL =
  Platform.OS === 'android'
    ? 'http://10.0.2.2:8000'
    : 'http://127.0.0.1:8000';

const HOSTED_API_BASE_URL = 'https://smartevcharging.uaenorth.cloudapp.azure.com/api';

const IS_DEV_BUILD = typeof __DEV__ !== 'undefined' && __DEV__;

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  (!IS_DEV_BUILD
    ? HOSTED_API_BASE_URL
    : Platform.OS === 'web'
      ? 'http://localhost:8000'
      : LOCAL_API_BASE_URL);

let accessTokenMemory: string | null = null;
let authExpiredHandler: (() => void) | null = null;

const notifyAuthExpired = () => {
  authExpiredHandler?.();
};

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


type BackendVehicleProfile = {
  id: string;
  make: string;
  model: string;
  battery_capacity_kwh: number;
  current_soc: number;
  range_km: number;
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


const mapBackendVehicle = (vehicle: BackendVehicleProfile): VehicleProfile => ({
  id: vehicle.id,
  make: vehicle.make,
  model: vehicle.model,
  batteryCapacity: vehicle.battery_capacity_kwh,
  currentSoC: vehicle.current_soc,
  rangeLeft: vehicle.range_km,
});

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
  const token = overrideAccessToken === undefined ? accessTokenMemory : overrideAccessToken;
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

const DEVICE_ID = 'mobile-app';

const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = await authStorage.getRefreshToken();

  if (!refreshToken) {
    accessTokenMemory = null;
    await authStorage.clearRefreshToken();
    notifyAuthExpired();
    return null;
  }

  try {
    const body = await requestJson<BackendTokenResponse>(
      '/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({
          refresh_token: refreshToken,
          device_id: DEVICE_ID,
        }),
      },
      null
    );

    const mapped = mapTokenResponse(body);
    accessTokenMemory = mapped.accessToken;
    await authStorage.saveRefreshToken(mapped.refreshToken);

    return mapped.accessToken;
  } catch (error) {
    accessTokenMemory = null;
    await authStorage.clearRefreshToken();
    notifyAuthExpired();
    throw error;
  }
};

const requestJsonWithAuthRetry = async <T>(
  path: string,
  options: RequestInit = {}
): Promise<T> => {
  try {
    return await requestJson<T>(path, options);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) {
      throw error;
    }

    const refreshedAccessToken = await refreshAccessToken();

    if (!refreshedAccessToken) {
      throw error;
    }

    return requestJson<T>(path, options, refreshedAccessToken);
  }
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

const calculateRequestedEnergyKwh = (
  targetSoc: number,
  currentSoC: number,
  batteryCapacity: number
) => {
  const deltaSoc = Math.max(0, targetSoc - currentSoC) / 100;
  return Number((deltaSoc * batteryCapacity).toFixed(3));
};

export const api = {
  getBaseUrl: () => API_BASE_URL,

  setAccessToken: (accessToken: string | null) => {
    accessTokenMemory = accessToken;
  },

  setAuthExpiredHandler: (handler: (() => void) | null) => {
    authExpiredHandler = handler;
  },

  login: async (payload: LoginRequest): Promise<AuthResponse> => {
    const body = await requestJson<BackendAuthResponse>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      null
    );

    const mapped = mapAuthResponse(body);
    accessTokenMemory = mapped.accessToken;

    return mapped;
  },

  register: async (payload: RegisterRequest): Promise<AuthResponse> => {
    const body = await requestJson<BackendAuthResponse>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      null
    );

    const mapped = mapAuthResponse(body);
    accessTokenMemory = mapped.accessToken;

    return mapped;
  },


  requestPasswordReset: async (email: string): Promise<PasswordResetRequestResponse> => {
    return requestJson<PasswordResetRequestResponse>(
      '/auth/password-reset/request',
      {
        method: 'POST',
        body: JSON.stringify({ email }),
      },
      null
    );
  },

  confirmPasswordReset: async (
    token: string,
    newPassword: string
  ): Promise<PasswordResetConfirmResponse> => {
    return requestJson<PasswordResetConfirmResponse>(
      '/auth/password-reset/confirm',
      {
        method: 'POST',
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      },
      null
    );
  },

  refresh: async (refreshToken: string, deviceId: string): Promise<AuthTokens> => {
    const body = await requestJson<BackendTokenResponse>(
      '/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({
          refresh_token: refreshToken,
          device_id: deviceId,
        }),
      },
      null
    );

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


  getMyVehicle: async (): Promise<VehicleProfile> => {
    const body = await requestJsonWithAuthRetry<BackendVehicleProfile>('/vehicles/me', {
      method: 'GET',
    });

    return mapBackendVehicle(body);
  },

  updateMyVehicle: async (
    payload: VehicleProfileUpdateRequest
  ): Promise<VehicleProfile> => {
    const body = await requestJsonWithAuthRetry<BackendVehicleProfile>('/vehicles/me', {
      method: 'PUT',
      body: JSON.stringify({
        make: payload.make,
        model: payload.model,
        battery_capacity_kwh: payload.batteryCapacity,
        current_soc: payload.currentSoC,
        range_km: payload.rangeLeft,
      }),
    });

    return mapBackendVehicle(body);
  },

  logout: async (refreshToken: string) => {
    await requestJson<{ success: boolean }>(
      '/auth/logout',
      {
        method: 'POST',
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      },
      null
    );

    accessTokenMemory = null;
  },

  getRecommendations: async (
    request: MobileRecommendationRequest
  ): Promise<ApiRecommendationsResponse> => {
    const payload = {
      latitude: 56.462,
      longitude: -2.9707,
      battery_level: request.vehicleCurrentSoC,
      target_battery_level: request.targetSoc,
      battery_kwh: request.vehicleBatteryCapacity,
      requested_energy_kwh: calculateRequestedEnergyKwh(
        request.targetSoc,
        request.vehicleCurrentSoC,
        request.vehicleBatteryCapacity
      ),
      preference_mode: request.preferenceMode,
      connector_type: mapChargerType(request.chargerType),
      latest_finish_minutes_from_now: 120,
      zone_id: 'zone_central_waterfront',
      metadata: {
        channel: 'mobile-app',
      },
    };

    return requestJsonWithAuthRetry<ApiRecommendationsResponse>('/mobile/recommendations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getMyChargingSessions: async (): Promise<ApiChargingSession[]> => {
    const response = await requestJsonWithAuthRetry<ApiChargingSessionsResponse>('/sessions/me', {
      method: 'GET',
    });

    return response.sessions;
  },

  getActiveChargingSession: async (): Promise<ApiChargingSession | null> => {
    const response = await requestJsonWithAuthRetry<ApiActiveChargingSessionResponse>('/sessions/active', {
      method: 'GET',
    });

    return response.session;
  },


  createReservation: async (
    payload: CreateReservationRequest
  ): Promise<ApiReservation> => {
    return requestJsonWithAuthRetry<ApiReservation>('/reservations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getMyReservations: async (): Promise<ApiReservation[]> => {
    const response = await requestJsonWithAuthRetry<ApiReservationsResponse>('/reservations/me', {
      method: 'GET',
    });

    return response.reservations;
  },

};
