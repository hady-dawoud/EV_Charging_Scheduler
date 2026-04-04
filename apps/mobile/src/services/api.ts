import { mockStations, mockSessions, mockUser, mockVehicle } from '../data/mockData';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const api = {
  login: async () => {
    await delay(1500);
    return { user: mockUser, vehicle: mockVehicle };
  },
  getRecommendations: async () => {
    await delay(3000);
    return mockStations;
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
