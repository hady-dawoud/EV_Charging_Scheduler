export type Station = {
  id: string;
  name: string;
  address: string;
  distance: number;
  chargerType: string;
  powerKw: number;
  pricePerKwh: number;
  availableStalls: number;
  totalStalls: number;
  hours: string;
};

export const mockStations: Station[] = [
  {
    id: '1',
    name: 'EcoCharge Downtown',
    address: '123 Main Street, Downtown District',
    distance: 1.2,
    chargerType: 'DC',
    powerKw: 150,
    pricePerKwh: 0.25,
    availableStalls: 2,
    totalStalls: 4,
    hours: '24/7',
  },
  {
    id: '2',
    name: 'GreenPower Mall',
    address: '456 Shopping Center Blvd, Level B2',
    distance: 2.8,
    chargerType: 'AC',
    powerKw: 22,
    pricePerKwh: 0.18,
    availableStalls: 3,
    totalStalls: 6,
    hours: '6:00 AM - 11:00 PM',
  },
  {
    id: '3',
    name: 'FastVolt Highway',
    address: 'Highway 101, Exit 42 Rest Area',
    distance: 4.5,
    chargerType: 'DC',
    powerKw: 350,
    pricePerKwh: 0.32,
    availableStalls: 1,
    totalStalls: 2,
    hours: '24/7',
  },
  {
    id: '4',
    name: 'CityCharge Central',
    address: '789 Central Ave, Parking Garage A',
    distance: 3.1,
    chargerType: 'DC',
    powerKw: 50,
    pricePerKwh: 0.22,
    availableStalls: 4,
    totalStalls: 8,
    hours: '5:00 AM - 12:00 AM',
  },
];
