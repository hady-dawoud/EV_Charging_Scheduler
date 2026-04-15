import { ReservationRecord, UiStationRecommendation } from '../types';

let currentReservation: ReservationRecord | null = null;
let pastReservations: ReservationRecord[] = [];

const buildReservation = (
  station: UiStationRecommendation,
  status: 'reserved' | 'past'
): ReservationRecord => ({
  id: `${station.id}-${Date.now()}`,
  station,
  reservedAtIso: new Date().toISOString(),
  status,
});

export const upsertReservationFromStation = (
  station: UiStationRecommendation
): ReservationRecord => {
  if (currentReservation?.station.id === station.id) {
    return currentReservation;
  }

  if (currentReservation) {
    pastReservations = [
      {
        ...currentReservation,
        status: 'past',
      },
      ...pastReservations,
    ];
  }

  currentReservation = buildReservation(station, 'reserved');
  return currentReservation;
};

export const getCurrentReservation = (): ReservationRecord | null => {
  return currentReservation;
};

export const getPastReservations = (): ReservationRecord[] => {
  return [...pastReservations];
};