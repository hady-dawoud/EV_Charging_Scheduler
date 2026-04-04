export interface User {
  id: string;
  name: string;
  email: string;
}

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

export type RootStackParamList = {
  Splash: undefined;
  Login: undefined;
  Signup: undefined;
  Main: undefined;
  ChargingRequest: undefined;
  LoadingRecommendations: undefined;
  Results: undefined;
  StationDetails: undefined;
  ReservationConfirm: undefined;
};
