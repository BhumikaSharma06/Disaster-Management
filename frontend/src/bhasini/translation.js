const LOCAL_TRANSLATION_CACHE = {
  hi: {
    Before: "पहले",
    During: "दौरान",
    After: "बाद",
    "Emergency response": "आपातकालीन सहायता",
    "Emergency services": "आपातकालीन सेवाएँ",
    "Ambulance service": "एम्बुलेंस सेवा",
    "Fire service": "अग्निशमन सेवा",
  },
};

export function translateWithFallback(text, language) {
  if (language === "en") {
    return { text, source: "original" };
  }

  const cachedText = LOCAL_TRANSLATION_CACHE[language]?.[text];
  if (cachedText) {
    return { text: cachedText, source: "local-cache" };
  }

  return { text, source: "english-fallback" };
}

export function getTranslationFallbackNotice(language) {
  if (language === "en") {
    return "";
  }

  return "Bhashini is not configured yet. Cached translations are used where available; other safety text remains in English.";
}
