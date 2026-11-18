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
  {
    id: "flood",
    title: "Flood",
    focus: "River, urban, and coastal water overflow",
    icon: "drop",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Track local water and weather advisories.", "Move medicines, documents, and essential supplies to a dry, elevated place."],
      during: ["Move to higher ground when advised.", "Never walk, swim, or drive through floodwater.", "Stay away from fallen power lines and electrical equipment in water."],
      after: ["Return only when authorities say it is safe.", "Avoid floodwater and damaged buildings; use safe drinking water."],
    },
  },
  {
    id: "cyclone",
    title: "Cyclone",
    focus: "Severe wind and coastal conditions",
    icon: "wind",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Follow official weather bulletins and evacuation instructions.", "Secure loose outdoor items and keep essential medicines, water, and documents ready."],
      during: ["Stay indoors, away from windows and glass.", "Do not go outside during a lull; strong winds may return.", "Move to an official shelter if instructed."],
      after: ["Wait for the official all-clear before going outside or returning home.", "Avoid floodwater, damaged structures, and fallen power lines."],
    },
  },
  {
    id: "earthquake",
    title: "Earthquake",
    focus: "Seismic activity",
    icon: "mountain",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Secure heavy furniture and identify safe cover away from windows.", "Keep shoes, a torch, water, and essential medicines accessible."],
      during: ["Drop, cover, and hold on; protect your head and neck.", "Stay indoors away from windows; if outside, move to an open area away from buildings and wires.", "Do not use lifts."],
      after: ["Expect aftershocks and leave damaged buildings carefully.", "Check for injuries and hazards; follow official instructions."],
    },
  },
  {
    id: "landslide",
    title: "Landslide",
    focus: "Unstable slopes and ground movement",
    icon: "mountain",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Watch for official warnings and signs such as new ground cracks or tilting trees.", "Know more than one way to leave the area."],
      during: ["Move quickly away from the path of moving soil, rocks, or debris if safe to do so.", "Avoid valleys, stream channels, and bridges near the slide."],
      after: ["Stay away from the slide area; additional movement may follow.", "Report damaged utilities and follow local authority guidance."],
    },
  },
  {
    id: "drought",
    title: "Drought",
    focus: "Prolonged water scarcity",
    icon: "sun",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Follow local water-use advisories and store drinking water safely.", "Plan for livestock, crops, and people who may need extra water support."],
      during: ["Use safe drinking water and follow public health advisories.", "Seek local assistance if household water or essential supplies run low.", "Avoid open flames where vegetation is dry."],
      after: ["Follow local guidance on water quality and rationing.", "Resume agricultural or water use according to local advisories."],
    },
  },
  {
    id: "heatwave",
    title: "Heatwave",
    focus: "High-temperature conditions",
    icon: "sun",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Check local heat advisories and identify a cool place to go.", "Plan outdoor work for cooler hours and check on people at higher risk."],
      during: ["Move to a cool or shaded place, rest, and drink water regularly if safe to do so.", "Wear light clothing and avoid strenuous activity during the hottest hours.", "Confusion, fainting, or very high body temperature needs urgent medical help."],
      after: ["Seek medical care if symptoms continue or worsen.", "Continue checking on vulnerable people as advised by health authorities."],
    },
  },
  {
    id: "tsunami",
    title: "Tsunami",
    focus: "Sea-level changes and coastal surges",
    icon: "wave",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Know the route to high ground and follow tsunami warning information.", "After strong or long coastal shaking, be ready to move inland or uphill."],
      during: ["Move to high ground or inland immediately when warned or after strong coastal shaking.", "Stay away from beaches, estuaries, and waterways; do not wait to watch the waves."],
      after: ["Remain in a safe area until authorities issue an all-clear.", "Expect multiple waves and follow official return instructions."],
    },
  },
  {
    id: "wildfire",
    title: "Wildfire",
    focus: "Uncontrolled vegetation fires",
    icon: "flame",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Know local evacuation routes and keep essential items ready.", "Clear dry leaves and combustible material around the home where safe and permitted."],
      during: ["Leave early when authorities advise evacuation; follow their route instructions.", "Avoid smoke and do not enter a fire area to retrieve belongings.", "If trapped, call emergency services and follow dispatcher instructions."],
      after: ["Return only after authorities declare the area safe.", "Avoid hot spots, damaged trees, and downed power lines."],
    },
  },
  {
    id: "lightning",
    title: "Lightning",
    focus: "Thunderstorms in any region",
    icon: "bolt",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Check thunderstorm advisories and identify a substantial enclosed shelter.", "Pause outdoor activity when thunder is heard."],
      during: ["Go indoors or into a hard-topped vehicle; avoid open fields, isolated trees, and water.", "If no shelter is available, crouch low with feet together; do not lie flat.", "Wait 30 minutes after the last thunder before resuming outdoor activity."],
      after: ["Avoid damaged power lines and report fires or injuries.", "Give first aid if trained and call emergency services for serious injuries."],
    },
  },
  {
    id: "severe-storm",
    title: "Severe storm",
    focus: "High winds, heavy rain, and hail",
    icon: "wind",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Follow weather warnings and secure loose outdoor objects.", "Identify an interior room away from windows."],
      during: ["Stay indoors and away from glass; move to a sturdy interior space.", "Avoid travel, underpasses, and areas with fallen wires or debris.", "Follow evacuation instructions if flooding or structural danger develops."],
      after: ["Wait for official safety updates before travelling.", "Avoid downed wires, damaged buildings, and flooded roads."],
    },
  },
  {
    id: "avalanche",
    title: "Avalanche",
    focus: "Snow and mountain hazards",
    icon: "mountain",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Check official mountain and snow advisories before travel.", "Avoid closed slopes and follow local route restrictions."],
      during: ["Move out of the slide path if possible and alert others.", "Once safe, contact emergency rescue services and provide the location."],
      after: ["Do not re-enter the slide area; further avalanches may occur.", "Leave rescue operations to trained teams and follow official instructions."],
    },
  },
  {
    id: "industrial-incident",
    title: "Industrial or chemical incident",
    focus: "Hazardous material releases and industrial accidents",
    icon: "alert",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Know local warning signals and the nearest official shelter guidance.", "Keep essential medicines and emergency contacts accessible."],
      during: ["Follow official evacuation or shelter-in-place instructions immediately.", "Avoid the visible plume or spill area; do not touch unknown substances.", "Call emergency services and share your location and observed hazard."],
      after: ["Do not return until authorities declare the area safe.", "Follow public health instructions about exposure, cleanup, and water safety."],
    },
  },
  {
    id: "public-health",
    title: "Public-health emergency",
    focus: "Community-wide health events",
    icon: "health",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Follow advisories from public-health authorities.", "Keep essential medicines and verified health-service contacts available."],
      during: ["Use trusted health sources and follow current prevention advice.", "Seek medical care for severe symptoms; call emergency services for immediate danger.", "Avoid spreading unverified reports."],
      after: ["Continue health precautions for the period advised by authorities.", "Use official channels for care, recovery support, and updated guidance."],
    },
  },
  {
    id: "cold-wave",
    title: "Cold wave",
    focus: "Prolonged low-temperature conditions",
    icon: "snow",
    helpline: { number: "112", label: "Emergency response" },
    guidance: {
      before: ["Check local cold-weather advisories and prepare warm clothing and bedding.", "Check on older adults, infants, and people without reliable shelter."],
      during: ["Stay warm and dry; use heating equipment only as directed and ventilate fuel-burning devices.", "Seek a warm shelter if your home is unsafe or unheated.", "Call emergency services for suspected hypothermia or immediate danger."],
      after: ["Continue local precautions while low temperatures persist.", "Get medical advice for cold-related symptoms."],
    },
  },
];
