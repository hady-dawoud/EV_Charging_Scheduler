import type { NavigatorScreenParams } from '@react-navigation/native';

export interface User {
  id: string;
  name: string;
  email: string;
}


export type LoginRequest = {
  email: string;
  password: string;
  device_id: string;
};

export type RegisterRequest = {
  full_name: string;
  email: string;
  password: string;
};

export type AuthTokens = {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
};

export type AuthResponse = AuthTokens & {
  user: User;
};

export interface Vehicle {
  id: string;
  make: string;
  model: string;
  batteryCapacity: number;
  currentSoC: number;
  rangeLeft: number;
}

export interface ChargingStation {
  id: string;
  name: string;
  provider: string;
  distance: string;
  power: string;
  stalls: string;
  price: string;
  totalTime?: string;
  totalPrice?: string;
  isCheapest?: boolean;
  isFastest?: boolean;
  isRecommended?: boolean;
  type: 'AC' | 'DC';
  status: 'open' | 'closed';
  address: string;
  waitingTime: string;
}

export type RecommendationPreferenceMode = 'cheapest' | 'fastest' | 'closest';
export type RecommendationChargerType = 'any' | 'ac' | 'dc';

export type MobileRecommendationRequest = {
  targetSoc: number;
  preferenceMode: RecommendationPreferenceMode;
  chargerType: RecommendationChargerType;
};

export type ApiRecommendationOption = {
  station_id: string;
  station_name: string;
  zone_id: string;
  transformer_id: string;
  score: number;
  distance_km: number;
  estimated_wait_minutes: number;
  estimated_duration_minutes: number;
  estimated_cost_gbp: number;
  transformer_headroom_kw: number;
  current_queue: number;
  utilization: number;
  charger_compatible: boolean;
  reason_tags: string[];
  metadata: Record<string, unknown>;
};

export type ApiRecommendationBundle = {
  request_id: string;
  client_request_id: string;
  simulated_timestamp: string;
  zone_id: string;
  top_recommendation: ApiRecommendationOption | null;
  alternatives: ApiRecommendationOption[];
  congestion_note: string | null;
  debug_reasoning_summary: string;
  source_type: string;
  metadata: Record<string, unknown>;
};

export type ApiRecommendationsResponse = ApiRecommendationBundle;

export type UiStationRecommendation = {
  id: string;
  name: string;
  zoneId: string;
  transformerId: string;
  distanceKm: number;
  estimatedWaitMinutes: number;
  estimatedDurationMinutes: number;
  estimatedCostGbp: number;
  headroomKw: number;
  queueLength: number;
  utilization: number;
  score: number;
  chargerLabel: string;
  reasonTags: string[];
};


export type ApiReservation = {
  reservation_id: string;
  status: 'confirmed' | 'active' | 'completed' | 'cancelled' | 'expired' | string;
  station_id: string;
  station_name: string;
  client_request_id: string | null;
  request_id: string | null;
  recommendation_rank: number | null;
  reserved_start_at: string;
  reserved_until: string;
  cancelled_at: string | null;
  estimated_cost_gbp: number | null;
  estimated_duration_minutes: number | null;
  charger_label: string | null;
  distance_km: number | null;
  score: number | null;
  created_at: string;
};

export type ApiReservationsResponse = {
  reservations: ApiReservation[];
};

export type CreateReservationRequest = {
  client_request_id: string | null;
  request_id: string | null;
  station_id: string;
  recommendation_rank: number;
  reserved_start_at: string;
  reserved_until?: string | null;
  estimated_cost_gbp?: number | null;
  estimated_duration_minutes?: number | null;
  charger_label?: string | null;
  distance_km?: number | null;
  score?: number | null;
};


export type ApiChargingSession = {
  session_id: string;
  status: 'active' | 'completed' | 'stale_active' | string;
  station_id: string;
  station_name: string;
  reservation_id: string | null;
  client_request_id: string | null;
  request_id: string | null;
  started_at: string;
  ended_at: string | null;
  energy_kwh: number;
  cost_total: number | null;
  connector_type: string | null;
  charger_power_kw: number | null;
  created_at: string;
};

export type ApiChargingSessionsResponse = {
  sessions: ApiChargingSession[];
};

export type ApiActiveChargingSessionResponse = {
  session: ApiChargingSession | null;
};

export type ReservationRecord = {
  id: string;
  station: UiStationRecommendation;
  reservedAtIso: string;
  status: 'reserved' | 'past';
};

export type MainTabsParamList = {
  Home: undefined;
  Sessions: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Splash: undefined;
  Login: undefined;
  Signup: undefined;
  Main: NavigatorScreenParams<MainTabsParamList> | undefined;
  ChargingRequest: undefined;
  LoadingRecommendations: { request: MobileRecommendationRequest };
  Results: { result: ApiRecommendationsResponse };
  StationDetails: { station?: UiStationRecommendation } | undefined;
  ReservationConfirm: { station: UiStationRecommendation };
};