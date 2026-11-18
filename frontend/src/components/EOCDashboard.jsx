import { useState, useMemo, useEffect, useRef } from "react";
import "./EOCDashboard.css";

// 14 Designated Shelters with real-world coordinates and capacities from seed.py
const INITIAL_SHELTERS = [
  // Supaul
  { id: "s1", name: "Birpur Model High School & Flood Shelter", district: "Supaul", capacity: 600, occupied: 410, lon: 86.935, lat: 26.52, medicalStaff: 4, foodDays: 4, contact: "+91-6275-224101", status: "operational" },
  { id: "s2", name: "Supaul Zila High School Relief Centre", district: "Supaul", capacity: 850, occupied: 720, lon: 86.605, lat: 26.126, medicalStaff: 6, foodDays: 3, contact: "+91-6275-222450", status: "operational" },
  { id: "s3", name: "Nirmali Community Disaster Centre", district: "Supaul", capacity: 450, occupied: 415, lon: 86.592, lat: 26.315, medicalStaff: 3, foodDays: 2, contact: "+91-6275-231120", status: "near_full" },
  { id: "s4", name: "Pipra Block Relief Camp", district: "Supaul", capacity: 400, occupied: 290, lon: 86.72, lat: 26.18, medicalStaff: 2, foodDays: 5, contact: "+91-6275-245300", status: "operational" },
  // Saharsa
  { id: "s5", name: "Saharsa Stadium Emergency Relief Camp", district: "Saharsa", capacity: 1200, occupied: 820, lon: 86.598, lat: 25.883, medicalStaff: 8, foodDays: 6, contact: "+91-6478-223400", status: "operational" },
  { id: "s6", name: "Simri Bakhtiarpur High School", district: "Saharsa", capacity: 600, occupied: 510, lon: 86.583, lat: 25.75, medicalStaff: 4, foodDays: 3, contact: "+91-6478-241210", status: "operational" },
  { id: "s7", name: "Nauhatta Panchayat Bhawan Shelter", district: "Saharsa", capacity: 350, occupied: 310, lon: 86.49, lat: 25.98, medicalStaff: 2, foodDays: 2, contact: "+91-6478-251009", status: "near_full" },
  { id: "s8", name: "Mahishi Community Health Centre", district: "Saharsa", capacity: 400, occupied: 275, lon: 86.45, lat: 25.85, medicalStaff: 5, foodDays: 4, contact: "+91-6478-261150", status: "operational" },
  // Madhepura
  { id: "s9", name: "Madhepura Town Hall & Relief Camp", district: "Madhepura", capacity: 750, occupied: 390, lon: 86.79, lat: 25.922, medicalStaff: 5, foodDays: 5, contact: "+91-6476-222140", status: "operational" },
  { id: "s10", name: "Alamnagar High School Flood Shelter", district: "Madhepura", capacity: 500, occupied: 430, lon: 86.9, lat: 25.55, medicalStaff: 3, foodDays: 3, contact: "+91-6476-234200", status: "operational" },
  { id: "s11", name: "Chausa Community Disaster Relief Camp", district: "Madhepura", capacity: 400, occupied: 180, lon: 87.02, lat: 25.52, medicalStaff: 2, foodDays: 7, contact: "+91-6476-248100", status: "operational" },
  // Purnia
  { id: "s12", name: "Purnia Zila School Relief Center", district: "Purnia", capacity: 1000, occupied: 520, lon: 87.47, lat: 25.78, medicalStaff: 7, foodDays: 6, contact: "+91-6454-222300", status: "operational" },
  { id: "s13", name: "Baisi Flood Evacuation Centre", district: "Purnia", capacity: 600, occupied: 420, lon: 87.75, lat: 25.833, medicalStaff: 4, foodDays: 4, contact: "+91-6454-235110", status: "operational" },
  { id: "s14", name: "Dagarua High School Disaster Shelter", district: "Purnia", capacity: 450, occupied: 210, lon: 87.6, lat: 25.8, medicalStaff: 3, foodDays: 5, contact: "+91-6454-241080", status: "operational" },
];

// River Telemetry and Gauge Stations
const GAUGE_STATIONS = [
  { id: "g1", name: "Birpur Barrage (Kosi)", district: "Supaul", lon: 86.935, lat: 26.52, discharge: 8420, dangerLevel: 8000, warningLevel: 4500, status: "danger", trend: "+140 m³/s / hr", type: "discharge" },
  { id: "g2", name: "Baltara Gauge (Kosi)", district: "Saharsa", lon: 86.75, lat: 25.68, waterLevel: 34.25, dangerLevel: 33.85, warningLevel: 33.15, status: "danger", trend: "+0.15 m / 3 hr", type: "stage" },
  { id: "g3", name: "Kursela Gauge (Confluence)", district: "Katihar/Purnia", lon: 87.25, lat: 25.43, waterLevel: 30.8, dangerLevel: 31.4, warningLevel: 30.0, status: "warning", trend: "+0.08 m / 3 hr", type: "stage" },
  { id: "g4", name: "Baisi Telemetry Station", district: "Purnia", lon: 87.75, lat: 25.83, waterLevel: 31.1, dangerLevel: 32.5, warningLevel: 31.5, status: "normal", trend: "Stable", type: "stage" },
];

// Active Emergency Distress SOS Requests
const INITIAL_SOS_REQUESTS = [
  {
    id: "SOS-101",
    district: "Supaul",
    village: "Nirmali Ward 4 (Near Embankment)",
    need: "Medical Evacuation",
    severity: "critical",
    score: 96,
    people: 3,
    details: "Elderly resident with acute respiratory distress, village access road submerged under 1.4m floodwater.",
    time: "8 mins ago",
    status: "pending",
    lon: 86.595,
    lat: 26.31,
    matchedResponder: null,
  },
  {
    id: "SOS-102",
    district: "Supaul",
    village: "Pipra Panchayat, Low-lying टोला",
    need: "Rescue / Evacuation",
    severity: "critical",
    score: 93,
    people: 5,
    details: "Family including 2 infants marooned on tin rooftop. Water level rising fast near Kosi bend.",
    time: "14 mins ago",
    status: "pending",
    lon: 86.71,
    lat: 26.175,
    matchedResponder: null,
  },
  {
    id: "SOS-103",
    district: "Saharsa",
    village: "Mahishi Block, Diara Region",
    need: "Clean Water & Dry Ration",
    severity: "high",
    score: 82,
    people: 18,
    details: "Handpumps inundated, no potable water for 24 hours. Diarrhea outbreak concern.",
    time: "32 mins ago",
    status: "pending",
    lon: 86.46,
    lat: 25.86,
    matchedResponder: null,
  },
  {
    id: "SOS-104",
    district: "Saharsa",
    village: "Simri Bakhtiarpur, Southern Ring",
    need: "Medical Evacuation",
    severity: "critical",
    score: 91,
    people: 2,
    details: "Full-term pregnant woman needing transport to Saharsa District Hospital. Bridge approach cut off.",
    time: "41 mins ago",
    status: "dispatched",
    lon: 86.575,
    lat: 25.74,
    matchedResponder: { name: "SDRF Rescue Inflatable #3", eta: "10 mins", phone: "+91-98012-33410" },
  },
  {
    id: "SOS-105",
    district: "Madhepura",
    village: "Alamnagar Diara Settlement",
    need: "Cattle & Family Evacuation",
    severity: "moderate",
    score: 72,
    people: 8,
    details: "Livestock and 8 farmers on raised agricultural bandh. Water stable but fodder exhausted.",
    time: "1 hr ago",
    status: "pending",
    lon: 86.885,
    lat: 25.56,
    matchedResponder: null,
  },
];

// Available First Responders & Volunteer Assets
const RESCUE_ASSETS = [
  { id: "r1", name: "NDRF Motorized Boat #2", base: "Nirmali Block HQ", district: "Supaul", capacity: 8, lon: 86.592, lat: 26.315, status: "available", contact: "+91-94318-00102" },
  { id: "r2", name: "SDRF Quick Response Platoon 1", base: "Supaul Police Lines", district: "Supaul", capacity: 12, lon: 86.605, lat: 26.126, status: "available", contact: "+91-94318-00105" },
  { id: "r3", name: "Pipra Disaster Volunteer Squad", base: "Pipra Middle School", district: "Supaul", capacity: 6, lon: 86.72, lat: 26.18, status: "available", contact: "+91-98350-22100" },
  { id: "r4", name: "SDRF Motorized Boat #5", base: "Saharsa Stadium Camp", district: "Saharsa", capacity: 10, lon: 86.598, lat: 25.883, status: "available", contact: "+91-94318-00201" },
  { id: "r5", name: "Alamnagar Flood Relief Boat #1", base: "Alamnagar Thana", district: "Madhepura", capacity: 8, lon: 86.9, lat: 25.55, status: "available", contact: "+91-94318-00304" },
];

// 72-Hour ML Hydrograph Discharge Forecast (Birpur Barrage)
const HYDROGRAPH_SERIES = [
  { time: "-48h", discharge: 5200, label: "T-48h" },
  { time: "-36h", discharge: 5850, label: "T-36h" },
  { time: "-24h", discharge: 6700, label: "T-24h" },
  { time: "-12h", discharge: 7600, label: "T-12h" },
  { time: "Now", discharge: 8420, label: "Current (Danger)", isNow: true },
  { time: "+12h", discharge: 8750, label: "+12h Forecast", isForecast: true },
  { time: "+24h", discharge: 8850, label: "+24h (XGBoost)", isForecast: true },
  { time: "+48h", discharge: 9120, label: "+48h (Peak Crest)", isForecast: true },
  { time: "+72h", discharge: 7940, label: "+72h (Receding)", isForecast: true },
];

// Multilingual CAP Warning Broadcasts
const CAP_BROADCAST_TEMPLATES = {
  extreme: {
    en: "FLASH RED ALERT: Severe flood surge exceeding 8,400 m³/s at Birpur Barrage. Embankment risk in Supaul & Saharsa. Evacuate low-lying river areas immediately to designated high-ground shelters. Dial 112 for rescue.",
    hi: "अत्यधिक गंभीर चेतावनी (रेड अलर्ट): बीरपुर बैराज पर कोसी का बहाव 8,400 घनमीटर/सेकंड पार कर गया है। सुपौल और सहरसा में तटबंध के निचले इलाके तुरंत खाली कर सुरक्षित आश्रय स्थलों पर पहुँचे। सहायता हेतु 112 डायल करें।",
    mai: "अत्यंत गंभीर चेतावनी (लाल चेतावनी): बीरपुर बैराज पर कोसीक पानि 8,400 घनमीटर/सेकंडसँ बेसी भ गेल अछि। सुपौल आ सहरसा मे तटबंधक निचुलका गाम तुरंत खाली कए ऊँच शरणस्थल जाउ। मद्दति लेल 112 पर फोन करू।",
  },
  warning: {
    en: "FLOOD WATCH: Upstream Kosi water discharge rising rapidly. Residents of Supaul, Saharsa, and Madhepura riverine areas should prepare emergency kits, secure cattle, and locate nearest shelters.",
    hi: "बाढ़ सतर्कता (ऑरेंज अलर्ट): ऊपरी कोसी में जलप्रवाह तेजी से बढ़ रहा है। सुपौल, सहरसा और मधेपुरा के तटबंधीय क्षेत्रों के नागरिक जरूरी दवाइयाँ, आवश्यक सामान सुरक्षित रखें और नजदीकी राहत शिविरों की जानकारी रखें।",
    mai: "बाढ़ि सतर्कता: कोसी मे जलप्रवाह तेजीसँ बढ़ि रहल अछि। सुपौल, सहरसा आ मधेपुराक नदी कछार केर लोक जरूरी सामान सुरक्षित राखू आ नजदीकी शरणस्थल पर नजरि राखू।",
  },
};

function getAvailableSpeechVoices(synthesis) {
  const voices = synthesis.getVoices();
  if (voices.length > 0) return Promise.resolve(voices);

  return new Promise((resolve) => {
    let timeoutId;
    const finish = () => {
      window.clearTimeout(timeoutId);
      synthesis.removeEventListener("voiceschanged", handleVoicesChanged);
      resolve(synthesis.getVoices());
    };
    const handleVoicesChanged = () => {
      if (synthesis.getVoices().length > 0) finish();
    };

    synthesis.addEventListener("voiceschanged", handleVoicesChanged);
    timeoutId = window.setTimeout(finish, 1500);
  });
}

export default function EOCDashboard({ language = "en" }) {
  const [activeTab, setActiveTab] = useState("map");
  const [selectedDistrict, setSelectedDistrict] = useState("all");
  const [inundationLevel, setInundationLevel] = useState(75); // 0 to 100%
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [sosList, setSosList] = useState(INITIAL_SOS_REQUESTS);
  const [sheltersList, setSheltersList] = useState(INITIAL_SHELTERS);
  const [layerFilters, setLayerFilters] = useState({
    inundation: true,
    shelters: true,
    stations: true,
    sos: true,
    corridors: true,
  });

  // CAP broadcast form
  const [broadcastTarget, setBroadcastTarget] = useState("Supaul & Saharsa");
  const [broadcastSeverity, setBroadcastSeverity] = useState("extreme");
  const [broadcastPrepared, setBroadcastPrepared] = useState(false);
  const [speakingLanguage, setSpeakingLanguage] = useState(null);
  const [speechNotice, setSpeechNotice] = useState("");
  const speechUtteranceRef = useRef(null);
  const speechRequestRef = useRef(0);

  useEffect(() => () => {
    speechRequestRef.current += 1;
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }, []);

  async function speakAlert(text, languageKey) {
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      setSpeechNotice("Text-to-speech is not supported in this browser.");
      return;
    }

    const synthesis = window.speechSynthesis;
    const requestId = speechRequestRef.current + 1;
    speechRequestRef.current = requestId;
    const voiceLanguage = languageKey === "en" ? "en" : "hi";
    const preferredLocale = languageKey === "en" ? "en-IN" : "hi-IN";
    synthesis.cancel();
    speechUtteranceRef.current = null;
    setSpeakingLanguage(languageKey);
    setSpeechNotice("Loading an available voice…");

    const voices = await getAvailableSpeechVoices(synthesis);
    if (speechRequestRef.current !== requestId) return;
    const matchingVoices = voices.filter((voice) =>
      voice.lang.toLowerCase().split("-")[0] === voiceLanguage
    );
    const selectedVoice = matchingVoices.sort((a, b) => {
      const aExact = a.lang.toLowerCase() === preferredLocale.toLowerCase() ? 1 : 0;
      const bExact = b.lang.toLowerCase() === preferredLocale.toLowerCase() ? 1 : 0;
      return bExact - aExact || Number(b.localService) - Number(a.localService);
    })[0];

    if (!selectedVoice) {
      setSpeakingLanguage(null);
      setSpeechNotice(
        `No ${languageKey === "en" ? "English" : "Hindi"} voice is available. Install a matching voice in your device's speech settings and try again.`
      );
      return;
    }

    synthesis.cancel();
    const spokenText = text
      .replace(/m³\/s/g, "cubic metres per second")
      .replace(/घनमीटर\/सेकंड/g, "घन मीटर प्रति सेकंड");
    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.voice = selectedVoice;
    utterance.lang = selectedVoice.lang || preferredLocale;
    utterance.rate = languageKey === "en" ? 0.92 : 0.82;
    speechUtteranceRef.current = utterance;
    setSpeakingLanguage(languageKey);
    setSpeechNotice(
      languageKey === "mai"
        ? "Playing the Maithili text with a Hindi voice; a Maithili voice may not be available on this device."
        : ""
    );

    const finishSpeaking = () => {
      if (speechUtteranceRef.current !== utterance || speechRequestRef.current !== requestId) return;
      speechUtteranceRef.current = null;
      setSpeakingLanguage(null);
    };
    utterance.onend = finishSpeaking;
    utterance.onerror = (event) => {
      finishSpeaking();
      if (event.error !== "canceled" && event.error !== "interrupted") {
        setSpeechNotice("Speech playback failed. Check your device's speech settings and try again.");
      }
    };

    try {
      synthesis.speak(utterance);
    } catch {
      finishSpeaking();
      setSpeechNotice("Speech playback could not start. Check your device's speech settings and try again.");
    }
  }

  function handleSpeechButton(text, languageKey) {
    if (speakingLanguage === languageKey) {
      window.speechSynthesis.cancel();
      speechRequestRef.current += 1;
      speechUtteranceRef.current = null;
      setSpeakingLanguage(null);
      setSpeechNotice("Playback stopped.");
      return;
    }
    speakAlert(text, languageKey);
  }

  const effectiveDischarge = 8420;

  // Compute dynamic stats
  const stats = useMemo(() => {
    const totalShelterCapacity = sheltersList.reduce((acc, s) => acc + s.capacity, 0);
    const totalOccupied = sheltersList.reduce((acc, s) => acc + s.occupied, 0);
    const pendingSos = sosList.filter((s) => s.status === "pending").length;
    const dispatchedSos = sosList.filter((s) => s.status === "dispatched").length;
    const exposedPeople = Math.round((effectiveDischarge / 8000) * 342000);

    return {
      discharge: effectiveDischarge,
      dischargeDiff: effectiveDischarge - 8000,
      totalCapacity: totalShelterCapacity,
      totalOccupied,
      occupancyPct: Math.round((totalOccupied / totalShelterCapacity) * 100),
      pendingSos,
      dispatchedSos,
      exposedPeople: Math.max(45000, exposedPeople),
      activeResponders: RESCUE_ASSETS.filter((asset) => asset.status === "available").length,
    };
  }, [sheltersList, sosList, effectiveDischarge]);

  // Auto-Match algorithm for SOS: Finds closest available asset
  function handleAutoMatch(sosId) {
    const targetSos = sosList.find((s) => s.id === sosId);
    if (!targetSos) return;

    // Filter available assets in same district or nearby
    const candidates = RESCUE_ASSETS.filter((a) => a.status === "available");
    if (candidates.length === 0) {
      alert("No available first responder assets currently in range.");
      return;
    }

    // Euclidean distance calculation (lon, lat)
    const sorted = [...candidates].sort((a, b) => {
      const distA = Math.hypot(a.lon - targetSos.lon, a.lat - targetSos.lat);
      const distB = Math.hypot(b.lon - targetSos.lon, b.lat - targetSos.lat);
      return distA - distB;
    });

    const bestMatch = sorted[0];
    const distanceKm = (Math.hypot(bestMatch.lon - targetSos.lon, bestMatch.lat - targetSos.lat) * 111).toFixed(2);
    const etaMin = Math.max(5, Math.round(distanceKm * 6));

    setSosList((prev) =>
      prev.map((item) =>
        item.id === sosId
          ? {
              ...item,
              matchedResponder: {
                name: bestMatch.name,
                base: bestMatch.base,
                distance: `${distanceKm} km`,
                eta: `${etaMin} mins`,
                phone: bestMatch.contact,
              },
            }
          : item
      )
    );
  }

  // Dispatch Responder
  function handleDispatch(sosId) {
    setSosList((prev) =>
      prev.map((item) => (item.id === sosId ? { ...item, status: "dispatched" } : item))
    );
  }

  // Transform lon/lat into SVG coordinates
  // Bounds: lon 86.30 to 87.90 (span 1.6), lat 25.35 to 26.70 (span 1.35)
  function project(lon, lat) {
    const x = ((lon - 86.3) / 1.6) * 820 + 40;
    const y = 560 - ((lat - 25.35) / 1.35) * 510;
    return { x, y };
  }

  // Filtered lists according to selected district
  const filteredShelters = useMemo(() => {
    if (selectedDistrict === "all") return sheltersList;
    return sheltersList.filter((s) => s.district === selectedDistrict);
  }, [sheltersList, selectedDistrict]);

  const filteredGauges = useMemo(() => {
    if (selectedDistrict === "all") return GAUGE_STATIONS;
    return GAUGE_STATIONS.filter((g) => g.district.includes(selectedDistrict));
  }, [selectedDistrict]);

  const filteredSos = useMemo(() => {
    if (selectedDistrict === "all") return sosList;
    return sosList.filter((s) => s.district === selectedDistrict);
  }, [sosList, selectedDistrict]);

  return (
    <div className="eoc-root">
      {/* 1. TOP COMMAND BAR */}
      <header className="eoc-command-bar">
        <div className="eoc-brand-cluster">
          <div className="eoc-radar-badge">
            <span className="eoc-radar-pulse" />
            <span className="eoc-radar-icon">EOC</span>
          </div>
          <div>
            <div className="eoc-system-title">
              <strong>District Operations Center</strong>
              <span className="eoc-badge-level eoc-badge-critical">
                {stats.discharge >= 8000 ? "ABOVE DANGER MARK" : stats.discharge >= 4500 ? "ELEVATED" : "NORMAL"}
              </span>
            </div>
            <p className="eoc-jurisdiction">
              LOWER KOSI BASIN <span aria-hidden="true">·</span> Supaul, Saharsa, Madhepura & Purnia
            </p>
          </div>
        </div>

        <div className="eoc-bar-controls">
          <div className="eoc-control-group">
            <label className="eoc-label-small">DISTRICT SECTOR</label>
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="eoc-select"
            >
              <option value="all">All Sectors (4 Districts)</option>
              <option value="Supaul">Supaul (Upstream Embankment)</option>
              <option value="Saharsa">Saharsa (Mid-Basin Diara)</option>
              <option value="Madhepura">Madhepura (Southern Plains)</option>
              <option value="Purnia">Purnia (Eastern Inflow)</option>
            </select>
          </div>
        </div>
      </header>

      {/* 2. SITUATION SUMMARY */}
      <section className="eoc-kpi-grid">
        <div className={`eoc-kpi-card ${stats.discharge >= 8000 ? "kpi-danger" : stats.discharge >= 4500 ? "kpi-warning" : "kpi-normal"}`}>
          <div className="kpi-top">
            <span className="kpi-icon">🌊</span>
            <span className="kpi-tag">{stats.discharge >= 8000 ? "ABOVE DANGER" : "MONITORED"}</span>
          </div>
          <div className="kpi-value">{stats.discharge.toLocaleString()} <span className="kpi-unit">m³/s</span></div>
          <div className="kpi-title">Birpur Barrage Discharge</div>
          <div className="kpi-sub">
            CWC Danger Mark: 8,000 m³/s (<strong>{stats.dischargeDiff > 0 ? `+${stats.dischargeDiff} m³/s` : "Normal"}</strong>)
          </div>
        </div>

        <div className="eoc-kpi-card kpi-neutral">
          <div className="kpi-top">
            <span className="kpi-icon">👥</span>
            <span className="kpi-tag">AT-RISK POPULATION</span>
          </div>
          <div className="kpi-value">{stats.exposedPeople.toLocaleString()}</div>
          <div className="kpi-title">Population at risk</div>
          <div className="kpi-sub">Estimate across 42 low-lying panchayats</div>
        </div>

        <div className="eoc-kpi-card kpi-shelter">
          <div className="kpi-top">
            <span className="kpi-icon">🏠</span>
            <span className="kpi-tag">{stats.occupancyPct}% OCCUPIED</span>
          </div>
          <div className="kpi-value">{stats.totalOccupied.toLocaleString()} <span className="kpi-unit">/ {stats.totalCapacity.toLocaleString()}</span></div>
          <div className="kpi-title">14 Designated Shelters</div>
          <div className="kpi-sub">
            {stats.totalCapacity - stats.totalOccupied} available bed capacity remaining
          </div>
        </div>

        <div className="eoc-kpi-card kpi-sos">
          <div className="kpi-top">
            <span className="kpi-icon">🆘</span>
            <span className="kpi-tag">{stats.pendingSos} PENDING ACTION</span>
          </div>
          <div className="kpi-value">{stats.pendingSos} <span className="kpi-unit">Active</span></div>
          <div className="kpi-title">Citizen Distress SOS Queue</div>
          <div className="kpi-sub">
            {stats.dispatchedSos} {stats.dispatchedSos === 1 ? "rescue team" : "rescue teams"} currently en route
          </div>
        </div>

        <div className="eoc-kpi-card kpi-responder">
          <div className="kpi-top">
            <span className="kpi-icon">🚤</span>
            <span className="kpi-tag">READY</span>
          </div>
          <div className="kpi-value">{stats.activeResponders} <span className="kpi-unit">Units</span></div>
          <div className="kpi-title">Available response assets</div>
          <div className="kpi-sub">NDRF / SDRF units listed in this area</div>
        </div>
      </section>

      {/* 3. NAVIGATION TABS FOR EOC */}
      <nav className="eoc-nav-tabs">
        <button
          className={`eoc-tab-btn ${activeTab === "map" ? "active" : ""}`}
          onClick={() => setActiveTab("map")}
        >
          GIS Situation Map
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "triage" ? "active" : ""}`}
          onClick={() => setActiveTab("triage")}
        >
          Priority SOS Queue ({stats.pendingSos})
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "hydro" ? "active" : ""}`}
          onClick={() => setActiveTab("hydro")}
        >
          72-hour Hydrograph & Forecast
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "shelters" ? "active" : ""}`}
          onClick={() => setActiveTab("shelters")}
        >
          Shelter Capacity ({sheltersList.length})
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "broadcast" ? "active" : ""}`}
          onClick={() => setActiveTab("broadcast")}
        >
          Multilingual Alert Bulletin
        </button>
      </nav>

      {/* TAB CONTENT 1: GIS SITUATION MAP */}
      {activeTab === "map" && (
        <div className="eoc-map-view">
          <div className="eoc-map-toolbar">
            <div className="eoc-map-layers">
              <span className="toolbar-label">GIS LAYERS:</span>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.inundation}
                  onChange={(e) => setLayerFilters({ ...layerFilters, inundation: e.target.checked })}
                />
                🌊 Flood Inundation Buffer
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.shelters}
                  onChange={(e) => setLayerFilters({ ...layerFilters, shelters: e.target.checked })}
                />
                🏠 Safe Shelters (14)
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.stations}
                  onChange={(e) => setLayerFilters({ ...layerFilters, stations: e.target.checked })}
                />
                📍 Gauge Telemetry (4)
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.sos}
                  onChange={(e) => setLayerFilters({ ...layerFilters, sos: e.target.checked })}
                />
                🚨 Distress SOS Beacons
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.corridors}
                  onChange={(e) => setLayerFilters({ ...layerFilters, corridors: e.target.checked })}
                />
                🛣️ Safe Evacuation Corridors
              </label>
            </div>

            <div className="eoc-inundation-slider">
              <span className="toolbar-label">WATER DISCHARGE SEVERITY:</span>
              <input
                type="range"
                min="20"
                max="100"
                value={inundationLevel}
                onChange={(e) => setInundationLevel(Number(e.target.value))}
                className="slider-input"
              />
              <span className="slider-val">{inundationLevel}%</span>
            </div>
          </div>

          <div className="eoc-map-stage">
            <svg
              className="eoc-gis-svg"
              viewBox="0 0 900 600"
              preserveAspectRatio="xMidYMid meet"
              aria-label="Lower Kosi GIS Map"
            >
              <defs>
                {/* River water gradient */}
                <linearGradient id="kosiGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e90ff" stopOpacity="0.9" />
                  <stop offset="50%" stopColor="#0077be" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#0a4b78" stopOpacity="0.9" />
                </linearGradient>

                {/* Inundation zone pattern */}
                <pattern id="floodHatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                  <line x1="0" y1="0" x2="0" y2="8" stroke="#ff3838" strokeWidth="2.5" strokeOpacity="0.25" />
                </pattern>

                {/* Radar pulse for SOS */}
                <radialGradient id="sosGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#ff0000" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#ff0000" stopOpacity="0" />
                </radialGradient>
              </defs>

              {/* Map Canvas Background */}
              <rect width="900" height="600" fill="#10252c" rx="8" />

              {/* 1. DISTRICT BOUNDARIES */}
              {/* Supaul (NW) */}
              <g className="district-group">
                <path
                  d="M 120 70 L 450 70 L 450 280 L 120 280 Z"
                  fill="#14323b"
                  stroke="#285664"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <text x="140" y="100" fill="#76a8b7" fontSize="13" fontWeight="bold" letterSpacing="1">
                  SUPAUL DISTRICT (UPSTREAM KOSI)
                </text>
              </g>

              {/* Saharsa (SW) */}
              <g className="district-group">
                <path
                  d="M 65 280 L 360 280 L 360 480 L 65 480 Z"
                  fill="#122d36"
                  stroke="#285664"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <text x="85" y="310" fill="#76a8b7" fontSize="13" fontWeight="bold" letterSpacing="1">
                  SAHARSA DISTRICT (DIARA EMBANKMENT)
                </text>
              </g>

              {/* Madhepura (Center-South) */}
              <g className="district-group">
                <path
                  d="M 360 280 L 580 280 L 580 540 L 360 540 Z"
                  fill="#153640"
                  stroke="#285664"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <text x="380" y="310" fill="#76a8b7" fontSize="13" fontWeight="bold" letterSpacing="1">
                  MADHEPURA DISTRICT
                </text>
              </g>

              {/* Purnia (East) */}
              <g className="district-group">
                <path
                  d="M 580 180 L 880 180 L 880 540 L 580 540 Z"
                  fill="#112932"
                  stroke="#285664"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <text x="600" y="210" fill="#76a8b7" fontSize="13" fontWeight="bold" letterSpacing="1">
                  PURNIA DISTRICT (EASTERN SECTOR)
                </text>
              </g>

              {/* 2. DYNAMIC FLOOD INUNDATION POLYGON */}
              {layerFilters.inundation && (
                <g className="inundation-layer">
                  {/* Outer danger buffer scaled by slider */}
                  <path
                    d={`M 365 110 
                       Q ${300 - inundationLevel * 0.4} 190, ${220 - inundationLevel * 0.5} 270 
                       Q ${170 - inundationLevel * 0.4} 340, ${210 - inundationLevel * 0.3} 420 
                       Q ${320 + inundationLevel * 0.3} 470, ${520 + inundationLevel * 0.3} 540
                       L ${550 - inundationLevel * 0.2} 550
                       Q ${370 - inundationLevel * 0.2} 490, ${280 - inundationLevel * 0.2} 430
                       Q ${260 + inundationLevel * 0.5} 350, ${320 + inundationLevel * 0.4} 260
                       Q ${430 + inundationLevel * 0.3} 180, 375 110 Z`}
                    fill="url(#floodHatch)"
                    stroke="#ff4d4d"
                    strokeWidth="1.8"
                    strokeOpacity="0.8"
                  />
                  <path
                    d={`M 365 110 
                       Q 300 190, 220 270 
                       Q 170 340, 210 420 
                       Q 320 470, 520 540
                       L 535 540
                       Q 335 470, 230 420
                       Q 190 340, 240 270
                       Q 320 190, 375 110 Z`}
                    fill="#ff2222"
                    fillOpacity={0.15 + (inundationLevel / 100) * 0.25}
                  />
                  <text x="250" y="380" fill="#ff6b6b" fontSize="11" fontWeight="bold">
                    ⚠️ ACTIVE FLOOD ZONE ({stats.discharge} m³/s)
                  </text>
                </g>
              )}

              {/* 3. KOSI RIVER COURSE */}
              <g className="kosi-river-main">
                <path
                  id="kosiMainPath"
                  d="M 370 115 
                     Q 320 195, 230 270 
                     Q 180 340, 220 425 
                     Q 300 480, 525 540"
                  fill="none"
                  stroke="url(#kosiGradient)"
                  strokeWidth={14 + (inundationLevel / 100) * 12}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* River water flow pulse effect */}
                <path
                  d="M 370 115 
                     Q 320 195, 230 270 
                     Q 180 340, 220 425 
                     Q 300 480, 525 540"
                  fill="none"
                  stroke="#a8e6ff"
                  strokeWidth="3"
                  strokeDasharray="12 16"
                  strokeDashoffset="10"
                  className="river-pulse"
                />
                <text x="390" y="145" fill="#69c0ff" fontSize="12" fontWeight="bold">
                  Kosi River ➔
                </text>
                <text x="440" y="525" fill="#69c0ff" fontSize="11">
                  Towards Kursela Confluence ➔
                </text>
              </g>

              {/* 4. SAFE EVACUATION CORRIDORS */}
              {layerFilters.corridors && (
                <g className="evacuation-corridors">
                  {/* Route 1: Nirmali to Birpur Model School */}
                  <line x1="202" y1="270" x2="367" y2="119" stroke="#52c41a" strokeWidth="2.5" strokeDasharray="6 4" />
                  {/* Route 2: Pipra to Supaul Zila School */}
                  <line x1="262" y1="250" x2="202" y2="271" stroke="#52c41a" strokeWidth="2.5" strokeDasharray="6 4" />
                  {/* Route 3: Mahishi to Saharsa Stadium */}
                  <line x1="120" y1="380" x2="199" y2="364" stroke="#52c41a" strokeWidth="2.5" strokeDasharray="6 4" />
                  {/* Route 4: Alamnagar to Madhepura Town Hall */}
                  <line x1="350" y1="480" x2="295" y2="349" stroke="#52c41a" strokeWidth="2.5" strokeDasharray="6 4" />
                </g>
              )}

              {/* 5. GAUGE STATIONS */}
              {layerFilters.stations &&
                filteredGauges.map((g) => {
                  const { x, y } = project(g.lon, g.lat);
                  const isDanger = g.status === "danger";
                  return (
                    <g
                      key={g.id}
                      className="gauge-node"
                      transform={`translate(${x}, ${y})`}
                      onClick={() => setSelectedFeature({ type: "station", data: g })}
                      style={{ cursor: "pointer" }}
                    >
                      <circle r="12" fill={isDanger ? "#cf1322" : "#faad14"} fillOpacity="0.3" className="node-halo" />
                      <circle r="7" fill={isDanger ? "#f5222d" : "#ffc53d"} stroke="#fff" strokeWidth="2" />
                      <text x="12" y="4" fill="#ffffff" fontSize="11" fontWeight="bold">
                        {g.name}
                      </text>
                      <text x="12" y="16" fill={isDanger ? "#ff7875" : "#ffe58f"} fontSize="10">
                        {g.type === "discharge" ? `${g.discharge} m³/s (🔴 DANGER)` : `${g.waterLevel}m (Stage)`}
                      </text>
                    </g>
                  );
                })}

              {/* 6. EMERGENCY SHELTERS */}
              {layerFilters.shelters &&
                filteredShelters.map((s) => {
                  const { x, y } = project(s.lon, s.lat);
                  const occRatio = s.occupied / s.capacity;
                  const markerColor = occRatio >= 0.85 ? "#ff4d4f" : occRatio >= 0.65 ? "#faad14" : "#52c41a";

                  return (
                    <g
                      key={s.id}
                      className="shelter-node"
                      transform={`translate(${x}, ${y})`}
                      onClick={() => setSelectedFeature({ type: "shelter", data: s })}
                      style={{ cursor: "pointer" }}
                    >
                      <rect x="-8" y="-8" width="16" height="16" rx="3" fill={markerColor} stroke="#fff" strokeWidth="1.5" />
                      <text x="0" y="3" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">
                        H
                      </text>
                      <text x="10" y="-2" fill="#d9f7be" fontSize="10" fontWeight="500">
                        {s.name.split(" ")[0]} ({s.occupied}/{s.capacity})
                      </text>
                    </g>
                  );
                })}

              {/* 7. ACTIVE SOS BEACONS */}
              {layerFilters.sos &&
                filteredSos.map((sos) => {
                  const { x, y } = project(sos.lon, sos.lat);
                  const isCritical = sos.severity === "critical";

                  return (
                    <g
                      key={sos.id}
                      className="sos-beacon-node"
                      transform={`translate(${x}, ${y})`}
                      onClick={() => setSelectedFeature({ type: "sos", data: sos })}
                      style={{ cursor: "pointer" }}
                    >
                      <circle r="18" fill="url(#sosGlow)" className="sos-pulse" />
                      <circle r="8" fill={isCritical ? "#f5222d" : "#fa8c16"} stroke="#fff" strokeWidth="2" />
                      <text x="0" y="3" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">
                        !
                      </text>
                      <text x="12" y="-2" fill="#ffa39e" fontSize="10" fontWeight="bold">
                        {sos.id} ({sos.need})
                      </text>
                    </g>
                  );
                })}
            </svg>

            {/* MAP LEGEND */}
            <div className="eoc-map-legend">
              <span className="legend-title">MAP SYMBOLS:</span>
              <span><span className="leg-dot leg-danger" /> Gauge at Danger</span>
              <span><span className="leg-dot leg-shelter-good" /> Shelter &lt;65%</span>
              <span><span className="leg-dot leg-shelter-full" /> Shelter &gt;85%</span>
              <span><span className="leg-dot leg-sos" /> Active Distress SOS</span>
              <span><span className="leg-line leg-corridor" /> Safe Corridor</span>
            </div>
          </div>

          {/* INSPECTION DRAWER FOR SELECTED FEATURE */}
          {selectedFeature && (
            <div className="eoc-inspect-panel">
              <div className="inspect-head">
                <strong>
                  {selectedFeature.type === "shelter" && "🏠 Designated Shelter Details"}
                  {selectedFeature.type === "station" && "📍 Hydrological Gauge Telemetry"}
                  {selectedFeature.type === "sos" && "🚨 Active SOS Distress Ticket"}
                </strong>
                <button className="inspect-close" onClick={() => setSelectedFeature(null)}>✕</button>
              </div>

              {selectedFeature.type === "shelter" && (
                <div className="inspect-body">
                  <h3>{selectedFeature.data.name}</h3>
                  <p>District: <strong>{selectedFeature.data.district}</strong> · Emergency Contact: <code>{selectedFeature.data.contact}</code></p>
                  <div className="inspect-stat-row">
                    <div>Capacity: <strong>{selectedFeature.data.capacity} beds</strong></div>
                    <div>Occupancy: <strong>{selectedFeature.data.occupied} ({Math.round((selectedFeature.data.occupied / selectedFeature.data.capacity) * 100)}%)</strong></div>
                    <div>Food Rations: <strong>{selectedFeature.data.foodDays} days buffer</strong></div>
                    <div>Medical Officers: <strong>{selectedFeature.data.medicalStaff} on duty</strong></div>
                  </div>
                  <div className="inspect-progress-track">
                    <div
                      className="inspect-progress-fill"
                      style={{
                        width: `${(selectedFeature.data.occupied / selectedFeature.data.capacity) * 100}%`,
                        backgroundColor: (selectedFeature.data.occupied / selectedFeature.data.capacity) > 0.85 ? "#f5222d" : "#52c41a",
                      }}
                    />
                  </div>
                </div>
              )}

              {selectedFeature.type === "station" && (
                <div className="inspect-body">
                  <h3>{selectedFeature.data.name}</h3>
                  <p>Monitoring Authority: <strong>Central Water Commission (CWC) / Bihar WRD</strong></p>
                  <div className="inspect-stat-row">
                    <div>Current Flow: <strong className="text-danger">{selectedFeature.data.discharge || selectedFeature.data.waterLevel} {selectedFeature.data.type === "discharge" ? "m³/s" : "meters"}</strong></div>
                    <div>Danger Threshold: <strong>{selectedFeature.data.dangerLevel}</strong></div>
                    <div>Warning Threshold: <strong>{selectedFeature.data.warningLevel}</strong></div>
                    <div>Trend: <strong>{selectedFeature.data.trend}</strong></div>
                  </div>
                </div>
              )}

              {selectedFeature.type === "sos" && (
                <div className="inspect-body">
                  <div className="inspect-tag-row">
                    <span className="badge-sos-id">{selectedFeature.data.id}</span>
                    <span className="badge-severity-critical">{selectedFeature.data.severity.toUpperCase()}</span>
                    <span>Triage Priority Score: <strong>{selectedFeature.data.score}/100</strong></span>
                  </div>
                  <h3>{selectedFeature.data.village} ({selectedFeature.data.district})</h3>
                  <p className="inspect-desc">{selectedFeature.data.details}</p>
                  <p>Reported: <strong>{selectedFeature.data.time}</strong> · Victims affected: <strong>{selectedFeature.data.people} persons</strong></p>

                  <div className="inspect-action-bar">
                    {selectedFeature.data.status === "pending" ? (
                      <>
                        <button
                          className="btn-auto-match"
                          onClick={() => handleAutoMatch(selectedFeature.data.id)}
                        >
                          ⚡ Auto-Match Nearest Rescue Team
                        </button>
                        {selectedFeature.data.matchedResponder && (
                          <div className="matched-box">
                            <strong>Matched: {selectedFeature.data.matchedResponder.name}</strong> ({selectedFeature.data.matchedResponder.distance}, ETA: {selectedFeature.data.matchedResponder.eta})
                            <button
                              className="btn-dispatch"
                              onClick={() => handleDispatch(selectedFeature.data.id)}
                            >
                              Dispatch Now
                            </button>
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="badge-dispatched">✅ RESCUE TEAM DISPATCHED & EN ROUTE</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 2: SOS TRIAGE & RESPONSE MATCHING */}
      {activeTab === "triage" && (
        <div className="eoc-triage-view">
          <div className="triage-header">
            <div>
              <h2>Citizen distress queue</h2>
              <p>Review incoming requests by urgency, location, and support needs.</p>
            </div>
          </div>

          <div className="triage-table-wrapper">
            <table className="triage-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Priority</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Victims</th>
                  <th>Situation Details</th>
                  <th>Responder Match & Dispatch</th>
                </tr>
              </thead>
              <tbody>
                {filteredSos.map((sos) => (
                  <tr key={sos.id} className={sos.severity === "critical" ? "row-critical" : "row-normal"}>
                    <td><code>{sos.id}</code></td>
                    <td>
                      <span className={`pill-score ${sos.severity}`}>
                        {sos.score} · {sos.severity.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <strong>{sos.district}</strong>
                      <div className="cell-sub">{sos.village}</div>
                    </td>
                    <td><span className="badge-category">{sos.need}</span></td>
                    <td><strong>{sos.people}</strong></td>
                    <td className="cell-details">{sos.details}</td>
                    <td>
                      {sos.status === "dispatched" ? (
                        <div className="dispatched-label">
                          <span>🟢 Dispatched</span>
                          <small>{sos.matchedResponder?.name || "SDRF Unit"}</small>
                        </div>
                      ) : (
                        <div className="match-actions">
                          {sos.matchedResponder ? (
                            <div className="match-ready">
                              <small>Matched: {sos.matchedResponder.name} ({sos.matchedResponder.eta})</small>
                              <button
                                className="btn-dispatch-compact"
                                onClick={() => handleDispatch(sos.id)}
                              >
                                Dispatch Team
                              </button>
                            </div>
                          ) : (
                            <button
                              className="btn-match-compact"
                              onClick={() => handleAutoMatch(sos.id)}
                            >
                              ⚡ Auto-Match
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT 3: HYDROGRAPH & 72H ML FORECAST */}
      {activeTab === "hydro" && (
        <div className="eoc-hydro-view">
          <div className="hydro-header">
            <div>
              <h2>Birpur Barrage 72-Hour Flood Discharge Forecast</h2>
              <p>Powered by XGBoost Machine Learning model trained on Bihar Surface Water daily discharge records.</p>
            </div>
            <div className="hydro-badges">
              <span className="badge-model">Model: XGBoost Regressor (v2.1)</span>
              <span className="badge-split">Chronological Holdout (2024–2025)</span>
            </div>
          </div>

          <div className="hydro-chart-panel">
            <svg className="hydro-svg" viewBox="0 0 840 320" aria-label="Discharge Hydrograph">
              {/* Gridlines */}
              <line x1="60" y1="40" x2="800" y2="40" stroke="#254854" strokeWidth="1" strokeDasharray="3 3" />
              <text x="15" y="45" fill="#88adb9" fontSize="10">10,000 m³</text>

              <line x1="60" y1="90" x2="800" y2="90" stroke="#f5222d" strokeWidth="1.5" strokeDasharray="5 3" />
              <text x="10" y="94" fill="#f5222d" fontSize="10" fontWeight="bold">8,000 (DANGER)</text>

              <line x1="60" y1="180" x2="800" y2="180" stroke="#faad14" strokeWidth="1.2" strokeDasharray="4 4" />
              <text x="10" y="184" fill="#faad14" fontSize="10">4,500 (WARNING)</text>

              <line x1="60" y1="260" x2="800" y2="260" stroke="#254854" strokeWidth="1" />
              <text x="15" y="264" fill="#88adb9" fontSize="10">2,000 m³</text>

              {/* Shaded Danger zone */}
              <rect x="60" y="40" width="740" height="50" fill="#f5222d" fillOpacity="0.1" />

              {/* Data curve */}
              {/* Points mapping:
                  -48h: x=100, y=240 (5200)
                  -36h: x=180, y=210 (5850)
                  -24h: x=260, y=180 (6700)
                  -12h: x=340, y=130 (7600)
                  Now:  x=420, y=80  (8420)
                  +12h: x=500, y=70  (8750)
                  +24h: x=580, y=65  (8850)
                  +48h: x=660, y=55  (9120)
                  +72h: x=740, y=95  (7940)
              */}
              {/* Historical segment */}
              <path
                d="M 100 240 L 180 210 L 260 180 L 340 130 L 420 80"
                fill="none"
                stroke="#1890ff"
                strokeWidth="3.5"
              />

              {/* ML Forecast segment (Dashed) */}
              <path
                d="M 420 80 L 500 70 L 580 65 L 660 55 L 740 95"
                fill="none"
                stroke="#ff4d4f"
                strokeWidth="3.5"
                strokeDasharray="6 4"
              />

              {/* Current time marker */}
              <line x1="420" y1="30" x2="420" y2="270" stroke="#ffffff" strokeWidth="1.5" strokeDasharray="3 3" />
              <text x="425" y="40" fill="#ffffff" fontSize="11" fontWeight="bold">CURRENT TIME</text>

              {/* Data points */}
              {HYDROGRAPH_SERIES.map((pt, idx) => {
                const x = 100 + idx * 80;
                // Calculate y: 10000 m³ -> y=40, 0 m³ -> y=300
                const y = 300 - (pt.discharge / 10000) * 260;
                return (
                  <g key={pt.time}>
                    <circle
                      cx={x}
                      cy={y}
                      r={pt.isNow ? 6 : 4.5}
                      fill={pt.isForecast ? "#ff4d4f" : pt.isNow ? "#ffffff" : "#1890ff"}
                      stroke="#10252c"
                      strokeWidth="2"
                    />
                    <text x={x} y={y - 12} textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">
                      {pt.discharge}
                    </text>
                    <text x={x} y="285" textAnchor="middle" fill="#88adb9" fontSize="10">
                      {pt.time}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="hydro-analysis-cards">
            <div className="analysis-card">
              <h3>24-Hour Horizon Prediction</h3>
              <div className="analysis-val text-danger">8,850 m³/s</div>
              <p>Forecasts flow increasing by <strong>+5.1%</strong> over next 24 hours. Peak discharge expected near Kursela within 36-44 hours.</p>
            </div>
            <div className="analysis-card">
              <h3>Hydrological Risk Assessment</h3>
              <div className="analysis-val text-warning">HIGH CREST RISK</div>
              <p>Birpur Barrage discharge remains above the verified <strong>8,000 m³/s danger mark</strong>. Immediate alert required for Supaul embankments.</p>
            </div>
            <div className="analysis-card">
              <h3>Feature Importance (SHAP Explainability)</h3>
              <ul className="shap-list">
                <li><span>Birpur 48-hour lag discharge:</span> <strong>42% impact</strong></li>
                <li><span>Upstream catchment rainfall (IMD):</span> <strong>34% impact</strong></li>
                <li><span>Rate of water level rise:</span> <strong>24% impact</strong></li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT 4: SHELTER LOGISTICS MATRIX */}
      {activeTab === "shelters" && (
        <div className="eoc-shelters-view">
          <div className="shelters-header">
            <div>
              <h2>Designated Emergency Shelters (Lower Kosi Basin)</h2>
              <p>Government schools, flood shelters, and community health centers designated for evacuation.</p>
            </div>
            <div className="shelter-summary-tag">
              Total Shelters: <strong>{sheltersList.length}</strong> · Capacity: <strong>{stats.totalCapacity}</strong> · Available: <strong>{stats.totalCapacity - stats.totalOccupied}</strong>
            </div>
          </div>

          <div className="shelters-grid">
            {filteredShelters.map((s) => {
              const occPct = Math.round((s.occupied / s.capacity) * 100);
              const isHigh = occPct >= 85;
              const isMed = occPct >= 65;

              return (
                <div key={s.id} className={`shelter-card ${isHigh ? "shelter-card-high" : isMed ? "shelter-card-med" : ""}`}>
                  <div className="shelter-card-top">
                    <div>
                      <span className="shelter-district-badge">{s.district}</span>
                      <h4>{s.name}</h4>
                    </div>
                    <span className={`shelter-status-badge ${isHigh ? "status-high" : "status-ok"}`}>
                      {occPct}% Full
                    </span>
                  </div>

                  <div className="shelter-progress-bar">
                    <div
                      className="shelter-progress-fill"
                      style={{
                        width: `${occPct}%`,
                        backgroundColor: isHigh ? "#ff4d4f" : isMed ? "#faad14" : "#52c41a",
                      }}
                    />
                  </div>

                  <div className="shelter-metrics">
                    <div>Capacity: <strong>{s.occupied} / {s.capacity}</strong></div>
                    <div>Food Buffer: <strong>{s.foodDays} Days</strong></div>
                    <div>Medical Officers: <strong>{s.medicalStaff}</strong></div>
                    <div>Helpline: <code>{s.contact}</code></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT 5: MULTILINGUAL CAP ALERT BROADCASTER */}
      {activeTab === "broadcast" && (
        <div className="eoc-broadcast-view">
          <div className="broadcast-header">
            <div>
              <h2>Multilingual alert bulletin</h2>
              <p>Review emergency warning text in English, Hindi, and Maithili before using an authorized distribution channel.</p>
            </div>
          </div>

          <div className="broadcast-layout">
            <div className="broadcast-composer">
              <h3>Bulletin settings</h3>
              <div className="form-group">
                <label>Target area</label>
                <select
                  value={broadcastTarget}
                  onChange={(e) => {
                    setBroadcastTarget(e.target.value);
                    setBroadcastPrepared(false);
                  }}
                  className="eoc-select"
                >
                  <option value="Supaul & Saharsa">Supaul & Saharsa (Kosi Embankment Ring)</option>
                  <option value="All 4 Districts">All 4 Focus Districts (Supaul, Saharsa, Madhepura, Purnia)</option>
                  <option value="Supaul Only">Supaul District Only</option>
                  <option value="Saharsa Only">Saharsa District Only</option>
                </select>
              </div>

              <div className="form-group">
                <label>Alert severity</label>
                <select
                  value={broadcastSeverity}
                  onChange={(e) => {
                    setBroadcastSeverity(e.target.value);
                    setBroadcastPrepared(false);
                  }}
                  className="eoc-select"
                >
                  <option value="extreme">Extreme Warning (Red Alert - Immediate Threat)</option>
                  <option value="warning">Severe Watch (Orange Alert - Water Level Rising)</option>
                </select>
              </div>

              <div className="broadcast-preview-boxes">
                <div className="preview-lang-box">
                  <div className="preview-lang-head">
                    <strong>English alert preview</strong>
                    <button
                      type="button"
                      className="btn-audio"
                      aria-label={speakingLanguage === "en" ? "Stop English speech" : "Listen to English alert"}
                      aria-pressed={speakingLanguage === "en"}
                      onClick={() => handleSpeechButton(CAP_BROADCAST_TEMPLATES[broadcastSeverity].en, "en")}
                    >
                      {speakingLanguage === "en"
                        ? speechUtteranceRef.current ? "Stop" : "Loading voice…"
                        : "🔊 Listen"}
                    </button>
                  </div>
                  <p>{CAP_BROADCAST_TEMPLATES[broadcastSeverity].en}</p>
                </div>

                <div className="preview-lang-box">
                  <div className="preview-lang-head">
                    <strong>Hindi alert preview</strong>
                    <button
                      type="button"
                      className="btn-audio"
                      aria-label={speakingLanguage === "hi" ? "Stop Hindi speech" : "Listen to Hindi alert"}
                      aria-pressed={speakingLanguage === "hi"}
                      onClick={() => handleSpeechButton(CAP_BROADCAST_TEMPLATES[broadcastSeverity].hi, "hi")}
                    >
                      {speakingLanguage === "hi"
                        ? speechUtteranceRef.current ? "Stop" : "Loading voice…"
                        : "🔊 Listen"}
                    </button>
                  </div>
                  <p>{CAP_BROADCAST_TEMPLATES[broadcastSeverity].hi}</p>
                </div>

                <div className="preview-lang-box">
                  <div className="preview-lang-head">
                    <strong>Maithili alert preview</strong>
                    <button
                      type="button"
                      className="btn-audio"
                      aria-label={speakingLanguage === "mai"
                        ? "Stop Maithili speech using a Hindi voice"
                        : "Listen to Maithili alert using a Hindi voice"}
                      aria-pressed={speakingLanguage === "mai"}
                      onClick={() => handleSpeechButton(CAP_BROADCAST_TEMPLATES[broadcastSeverity].mai, "mai")}
                    >
                      {speakingLanguage === "mai"
                        ? speechUtteranceRef.current ? "Stop" : "Loading voice…"
                        : "🔊 Listen (Hindi voice)"}
                    </button>
                  </div>
                  <p>{CAP_BROADCAST_TEMPLATES[broadcastSeverity].mai}</p>
                </div>
              </div>
              <p className="speech-status" role="status" aria-live="polite">
                {speechNotice}
              </p>

              <button
                className="btn-prepare-bulletin"
                onClick={() => setBroadcastPrepared(true)}
              >
                Prepare multilingual alert bulletin
              </button>

              {broadcastPrepared && (
                <div className="broadcast-success-banner">
                  <strong>Bulletin prepared.</strong> Review the wording and distribute through an authorized alerting channel.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
