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

export interface Session {
  id: string;
  stationName: string;
  date: string;
  cost: string;
  energyAdded: string;
  duration: string;
  status: 'completed' | 'active' | 'upcoming';
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