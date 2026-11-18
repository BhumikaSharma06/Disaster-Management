const INDIA_BOUNDS = {
  south: 6.5,
  north: 37.5,
  west: 68,
  east: 97.5,
};

const LANGUAGE_OPTIONS = {
  en: { label: "English", nativeLabel: "English" },
  hi: { label: "Hindi", nativeLabel: "हिन्दी" },
};

const REGION_LANGUAGE_OPTIONS = {
  IN: ["en", "hi"],
};

export function getLanguageOptionsForLocation(latitude, longitude) {
  const { south, north, west, east } = INDIA_BOUNDS;
  const isInIndia =
    latitude >= south &&
    latitude <= north &&
    longitude >= west &&
    longitude <= east;

  if (!isInIndia) {
    return {
      regionCode: null,
      regionLabel: "Location outside supported regions",
      languageCodes: ["en"],
      isApproximate: false,
    };
  }

  return {
    regionCode: "IN",
    regionLabel: "India · approximate country-level match",
    languageCodes: REGION_LANGUAGE_OPTIONS.IN,
    isApproximate: true,
  };
}

export function getLanguageLabel(languageCode) {
  return LANGUAGE_OPTIONS[languageCode]?.nativeLabel ?? languageCode;
}

export function detectDeviceRegion(onDetected, onUnavailable) {
  if (!navigator.geolocation) {
    onUnavailable?.("Device location is not available in this browser.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      onDetected(
        getLanguageOptionsForLocation(coords.latitude, coords.longitude),
      );
    },
    () => {
      onUnavailable?.(
        "Location permission was not granted; showing general language options.",
      );
    },
    { enableHighAccuracy: false, maximumAge: 600_000, timeout: 10_000 },
  );
}
