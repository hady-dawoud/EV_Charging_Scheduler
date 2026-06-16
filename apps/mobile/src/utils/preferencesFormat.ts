import type { CurrencyCode, DistanceUnit } from '../types';

const GBP_TO_EUR = 1.17;
const MI_PER_KM = 0.621371;

export const getCurrencySymbol = (currency: CurrencyCode) =>
  currency === 'EUR' ? '€' : '£';

export const formatCurrencyAmount = (
  gbp: number | null | undefined,
  currency: CurrencyCode,
  fallback = 'Cost pending'
) => {
  if (gbp == null || !Number.isFinite(gbp)) {
    return fallback;
  }

  const value = currency === 'EUR' ? gbp * GBP_TO_EUR : gbp;
  return `${getCurrencySymbol(currency)}${value.toFixed(2)}`;
};

export const formatDistanceKm = (
  km: number | null | undefined,
  unit: DistanceUnit,
  fallback = 'Distance pending',
  decimals = 1
) => {
  if (km == null || !Number.isFinite(km)) {
    return fallback;
  }

  const value = unit === 'mi' ? km * MI_PER_KM : km;
  const suffix = unit === 'mi' ? 'mi' : 'km';

  return `${value.toFixed(decimals)} ${suffix}`;
};
