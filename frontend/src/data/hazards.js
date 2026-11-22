export const EMERGENCY_CONTACTS = {
  emergency: {
    number: "112",
    label: "Emergency services",
    note: "India's unified emergency number.",
  },
  ambulance: {
    number: "108",
    label: "Ambulance service",
    note: "Service coverage varies by state; call 112 if unavailable.",
  },
  fire: {
    number: "101",
    label: "Fire service",
    note: "Service coverage varies by area; call 112 if unavailable.",
  },
};

const CONTACTS_BY_HAZARD = {
  cyclone: ["emergency", "ambulance", "fire"],
  earthquake: ["emergency", "ambulance", "fire"],
  wildfire: ["emergency", "fire", "ambulance"],
  "industrial-incident": ["emergency", "fire", "ambulance"],
  "severe-storm": ["emergency", "fire", "ambulance"],
};

export function getEmergencyContacts(hazardId) {
  const contactIds = CONTACTS_BY_HAZARD[hazardId] ?? ["emergency", "ambulance"];
  return contactIds.map((contactId) => EMERGENCY_CONTACTS[contactId]);
}

export const HAZARDS = [
  { id: "flood", title: "Flood", focus: "River, urban, and coastal water overflow", icon: "drop", helpline: { number: "112", label: "Emergency response" } },
  { id: "cyclone", title: "Cyclone", focus: "Severe wind and coastal conditions", icon: "wind", helpline: { number: "112", label: "Emergency response" } },
  { id: "earthquake", title: "Earthquake", focus: "Seismic activity", icon: "mountain", helpline: { number: "112", label: "Emergency response" } },
  { id: "landslide", title: "Landslide", focus: "Unstable slopes and ground movement", icon: "mountain", helpline: { number: "112", label: "Emergency response" } },
  { id: "drought", title: "Drought", focus: "Prolonged water scarcity", icon: "sun", helpline: { number: "112", label: "Emergency response" } },
  { id: "heatwave", title: "Heatwave", focus: "High-temperature conditions", icon: "sun", helpline: { number: "112", label: "Emergency response" } },
  { id: "tsunami", title: "Tsunami", focus: "Sea-level changes and coastal surges", icon: "wave", helpline: { number: "112", label: "Emergency response" } },
  { id: "wildfire", title: "Wildfire", focus: "Uncontrolled vegetation fires", icon: "flame", helpline: { number: "112", label: "Emergency response" } },
  { id: "lightning", title: "Lightning", focus: "Thunderstorms in any region", icon: "bolt", helpline: { number: "112", label: "Emergency response" } },
  { id: "severe-storm", title: "Severe storm", focus: "High winds, heavy rain, and hail", icon: "wind", helpline: { number: "112", label: "Emergency response" } },
  { id: "avalanche", title: "Avalanche", focus: "Snow and mountain hazards", icon: "mountain", helpline: { number: "112", label: "Emergency response" } },
  { id: "industrial-incident", title: "Industrial or chemical incident", focus: "Hazardous material releases and industrial accidents", icon: "alert", helpline: { number: "112", label: "Emergency response" } },
  { id: "public-health", title: "Public-health emergency", focus: "Community-wide health events", icon: "health", helpline: { number: "112", label: "Emergency response" } },
  { id: "cold-wave", title: "Cold wave", focus: "Prolonged low-temperature conditions", icon: "snow", helpline: { number: "112", label: "Emergency response" } },
];
