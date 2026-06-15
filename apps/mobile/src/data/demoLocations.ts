export type DemoLocation = {
  id: string;
  name: string;
  subtitle: string;
  latitude: number;
  longitude: number;
};

export const DUNDEE_DEMO_LOCATIONS: DemoLocation[] = [
  {
    id: 'central_dundee',
    name: 'Central Dundee',
    subtitle: 'City Centre',
    latitude: 56.4620,
    longitude: -2.9707,
  },
  {
    id: 'dundee_waterfront',
    name: 'Dundee Waterfront',
    subtitle: 'V&A / Riverside Esplanade',
    latitude: 56.4575,
    longitude: -2.9670,
  },
  {
    id: 'university_west_end',
    name: 'University of Dundee',
    subtitle: 'West End',
    latitude: 56.4572,
    longitude: -2.9825,
  },
  {
    id: 'ninewells',
    name: 'Ninewells Hospital',
    subtitle: 'West Dundee',
    latitude: 56.4635,
    longitude: -3.0400,
  },
  {
    id: 'dundee_airport',
    name: 'Dundee Airport',
    subtitle: 'Riverside',
    latitude: 56.4525,
    longitude: -3.0258,
  },
  {
    id: 'lochee',
    name: 'Lochee',
    subtitle: 'North West Dundee',
    latitude: 56.4736,
    longitude: -3.0116,
  },
  {
    id: 'broughty_ferry',
    name: 'Broughty Ferry',
    subtitle: 'East Dundee',
    latitude: 56.4670,
    longitude: -2.8730,
  },
  {
    id: 'monifieth',
    name: 'Monifieth',
    subtitle: 'East of Dundee',
    latitude: 56.4823,
    longitude: -2.8172,
  },
];

export const DEFAULT_DEMO_LOCATION = DUNDEE_DEMO_LOCATIONS[0];

export type StationMapLocation = {
  latitude: number;
  longitude: number;
  address: string;
};

const STATION_COORDINATE_LOOKUP: Record<string, StationMapLocation> = {
  greenmarket_150kw_bus_charger: {
    latitude: 56.4602,
    longitude: -2.9714,
    address: 'Greenmarket, Dundee',
  },
  tx_central_market: {
    latitude: 56.4602,
    longitude: -2.9714,
    address: 'Greenmarket, Dundee',
  },
  fallback_station: {
    latitude: 56.4602,
    longitude: -2.9714,
    address: 'Greenmarket, Dundee',
  },
};

const fallbackByZone: Record<string, StationMapLocation> = {
  zone_central_waterfront: {
    latitude: 56.4578,
    longitude: -2.9670,
    address: 'Dundee Waterfront',
  },
  zone_west_end: {
    latitude: 56.4572,
    longitude: -2.9825,
    address: 'University of Dundee / West End',
  },
  zone_ninewells: {
    latitude: 56.4635,
    longitude: -3.0400,
    address: 'Ninewells Hospital, Dundee',
  },
  zone_riverside: {
    latitude: 56.4525,
    longitude: -3.0258,
    address: 'Dundee Airport / Riverside',
  },
  zone_broughty_ferry: {
    latitude: 56.4670,
    longitude: -2.8730,
    address: 'Broughty Ferry, Dundee',
  },
};

const normalizeKey = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

export const getStationMapLocation = ({
  stationId,
  stationName,
  zoneId,
  latitude,
  longitude,
}: {
  stationId: string;
  stationName: string;
  zoneId: string;
  latitude?: number | null;
  longitude?: number | null;
}): StationMapLocation => {
  if (
    typeof latitude === 'number' &&
    Number.isFinite(latitude) &&
    typeof longitude === 'number' &&
    Number.isFinite(longitude)
  ) {
    return {
      latitude,
      longitude,
      address: stationName,
    };
  }

  return (
    STATION_COORDINATE_LOOKUP[stationId] ??
    STATION_COORDINATE_LOOKUP[normalizeKey(stationId)] ??
    STATION_COORDINATE_LOOKUP[normalizeKey(stationName)] ??
    fallbackByZone[zoneId] ??
    {
      latitude: 56.4620,
      longitude: -2.9707,
      address: 'Dundee',
    }
  );
};

export const buildGoogleMapsUrl = (location: StationMapLocation, label: string) => {
  const encodedLabel = encodeURIComponent(label);
  return `https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}&query_place_id=${encodedLabel}`;
};

export const buildStaticMapUrl = (location: StationMapLocation) =>
  `https://staticmap.openstreetmap.de/staticmap.php?center=${location.latitude},${location.longitude}&zoom=15&size=800x900&markers=${location.latitude},${location.longitude},lightgreen1`;
