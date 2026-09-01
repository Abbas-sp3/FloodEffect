import type { EmergencyFacility, ViewState } from '../types';

export const KP3_INITIAL_VIEW_STATE: ViewState = {
  longitude: 77.4985,
  latitude: 28.4728,
  zoom: 14.2,
  pitch: 0,
  bearing: 0,
};

export const KP3_VIEW_STATE_2D: Partial<ViewState> = {
  pitch: 0,
  bearing: 0,
  transitionDuration: 800,
};

export const KP3_VIEW_STATE_3D: Partial<ViewState> = {
  pitch: 60,
  bearing: -20,
  zoom: 15.2,
  transitionDuration: 800,
};

export const KP3_EMERGENCY_INFRA: EmergencyFacility[] = [
  // Hospitals — Real Greater Noida / KP3 facilities
  { name: 'Sharda Hospital & Trauma Center', type: 'hospital', lon: 77.4920, lat: 28.4770 },
  { name: 'Kailash Hospital Greater Noida', type: 'hospital', lon: 77.5090, lat: 28.4650 },
  { name: 'Yatharth Super Speciality Hospital', type: 'hospital', lon: 77.4950, lat: 28.4680 },
  { name: 'GIMS (Govt Institute of Medical Sciences)', type: 'hospital', lon: 77.5010, lat: 28.4810 },

  // Police Stations — Real Greater Noida stations
  { name: 'Knowledge Park Police Station', type: 'police', lon: 77.4980, lat: 28.4720 },
  { name: 'Beta-2 Police Station', type: 'police', lon: 77.5120, lat: 28.4760 },
  { name: 'Pari Chowk Traffic Police Booth', type: 'police', lon: 77.5085, lat: 28.4645 },

  // Fire Stations
  { name: 'Surajpur Fire Station', type: 'fire', lon: 77.5050, lat: 28.4680 },
  { name: 'Ecotech-1 Fire Station', type: 'fire', lon: 77.4890, lat: 28.4620 },

  // Evacuation Shelters in Knowledge Park 3
  { name: 'Galgotias Campus Auditorium', type: 'shelter', lon: 77.4980, lat: 28.4735 },
  { name: 'Alpha-1 Community Centre Shelter', type: 'shelter', lon: 77.5090, lat: 28.4650 },
  { name: 'Accurate Sports Complex Shelter', type: 'shelter', lon: 77.4930, lat: 28.4610 },
  { name: 'GIMS Stadium Shelter', type: 'shelter', lon: 77.5010, lat: 28.4810 },
];
