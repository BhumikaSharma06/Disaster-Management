import { useEffect, useRef, useState } from "react";

import EOCDashboard from "./components/EOCDashboard.jsx";
import { HAZARDS, getEmergencyContacts } from "./data/hazards.js";
import {
  getTranslationFallbackNotice,
  translateWithFallback,
} from "./bhasini/translation.js";
import {
  detectDeviceRegion,
  getLanguageLabel,
} from "./i18n/deviceLanguage.js";

const translations = {
  en: {
    overview: "Overview",
    prepare: "Be prepared",
    during: "During a disaster",
    response: "Get or offer help",
    data: "Data & sources",
    eoc: "EOC Dashboard",
    offline: "You’re offline",
    online: "Online · no live hazard feed",
    subtitle: "All-hazard disaster readiness",
    safetyGuide: "Safety guides",
    requestHelp: "Request help",
    noForecast: "Hazard information",
    noForecastBody: "No live hazard forecasts or official alert feed are available on this dashboard.",
    locationShare: "Share my location",
    locationPrivacy: "Your location is requested only after you tap the button. Nothing is sent automatically.",
    requestLocation: "Get device location",
    copyLocation: "Copy location",
    shareLocation: "Share location",
    locationPending: "Requesting device location…",
    locationUnavailable: "Could not get your location. Check permission and try again.",
    locationCopied: "Location copied. Share it only with people you trust.",
    locationShareCancelled: "Share cancelled. Nothing was sent.",
    before: "Before",
    duringPhase: "During",
    after: "After",
    allHazards: "All hazards",
    emergencyContacts: "Emergency contacts",
    contactCoverage: "Availability may vary by area. If a number does not connect, call 112.",
  },
  hi: {
    overview: "अवलोकन",
    prepare: "तैयार रहें",
    during: "आपदा के दौरान",
    response: "मदद लें या दें",
    data: "डेटा और स्रोत",
    eoc: "ईओसी डैशबोर्ड",
    offline: "आप ऑफ़लाइन हैं",
    online: "ऑनलाइन · लाइव आपदा फ़ीड उपलब्ध नहीं",
    subtitle: "सभी आपदाओं के लिए तैयारी",
    safetyGuide: "आपदा सुरक्षा मार्गदर्शिकाएँ",
    requestHelp: "मदद माँगें",
    noForecast: "आपदा संबंधी जानकारी",
    noForecastBody: "आपदा की जानकारी और तैयारी के सुझाव एक जगह देखें।",
    locationShare: "अपना स्थान साझा करें",
    locationPrivacy: "स्थान केवल बटन दबाने के बाद माँगा जाएगा। कुछ भी अपने-आप नहीं भेजा जाएगा।",
    requestLocation: "डिवाइस का स्थान लें",
    copyLocation: "स्थान कॉपी करें",
    shareLocation: "स्थान साझा करें",
    locationPending: "डिवाइस का स्थान प्राप्त हो रहा है…",
    locationUnavailable: "स्थान नहीं मिला। अनुमति जाँचें और फिर प्रयास करें।",
    locationCopied: "स्थान कॉपी हुआ। इसे केवल भरोसेमंद लोगों के साथ साझा करें।",
    locationShareCancelled: "साझाकरण रद्द हुआ। कुछ नहीं भेजा गया।",
    before: "पहले",
    duringPhase: "दौरान",
    after: "बाद",
    allHazards: "सभी आपदाएँ",
    emergencyContacts: "आपातकालीन संपर्क",
    contactCoverage: "सेवा की उपलब्धता क्षेत्र के अनुसार बदल सकती है। संपर्क न होने पर 112 पर कॉल करें।",
  },
};

const navigation = [
  { id: "overview", icon: "grid" },
  { id: "prepare", icon: "shield" },
  { id: "during", icon: "life" },
  { id: "response", icon: "people" },
  { id: "data", icon: "database" },
  { id: "eoc", icon: "alert" },
];

function Icon({ name, size = 20 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    life: <><circle cx="12" cy="12" r="10" /><path d="m4.9 4.9 4.3 4.3M14.8 14.8l4.3 4.3M14.8 9.2l4.3-4.3M4.9 19.1l4.3-4.3M12 8v4l3 2" /></>,
    people: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
    database: <><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0" /></>,
    arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
    chevron: <path d="m9 18 6-6-6-6" />,
    pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    clock: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    drop: <><path d="M12 22a8 8 0 0 0 8-8c0-4-8-12-8-12S4 10 4 14a8 8 0 0 0 8 8Z" /></>,
    language: <><circle cx="12" cy="12" r="10" /><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" /></>,
    wind: <><path d="M3 8h12a3 3 0 1 0-3-3M2 12h17a3 3 0 1 1-3 3M4 16h8a3 3 0 1 1-3 3" /></>,
    mountain: <><path d="m3 20 7-13 4 7 2-3 5 9H3Z" /><path d="m8 11 2 2 2-2" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></>,
    wave: <><path d="M2 8c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 14c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 20c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2" /></>,
    flame: <><path d="M8.5 14.5A3.5 3.5 0 0 0 12 18a3.5 3.5 0 0 0 3.5-3.5c0-2-1.5-3-1.5-5.5-2 1-3 2-3 4-1.5-.5-2.5-2-2-5-3 2-4 5-4 7a7 7 0 0 0 14 0c0-3-1-5-3-7" /></>,
    bolt: <path d="m13 2-3 8H5l6 12 3-9h5L13 2Z" />,
    alert: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4m0 4h.01" /></>,
    health: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="M9 12h6m-3-3v6" /></>,
    snow: <><path d="M12 2v20M4 6l16 12M20 6 4 18M8 3l4 3 4-3M8 21l4-3 4 3M2 10l4-1 1-4m15 9-4 1-1 4M22 10l-4-1-1-4M2 14l4 1 1 4" /></>,
    phone: <><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.4 19.4 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.2-1.3a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.8 2.1Z" /></>,
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name] || paths.grid}
    </svg>
  );
}

function App() {
  const [activeView, setActiveView] = useState("overview");
  const [selectedHazard, setSelectedHazard] = useState("all");
  const [language, setLanguage] = useState("en");
  const [languageOptions, setLanguageOptions] = useState(["en", "hi"]);
  const [deviceRegion, setDeviceRegion] = useState("Checking device region");
  const [online, setOnline] = useState(navigator.onLine);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [responseType, setResponseType] = useState("request");
  const [formMessage, setFormMessage] = useState("");
  const languageWasSelected = useRef(false);

  const text = translations[language];
  const selectedModule = HAZARDS.find((module) => module.id === selectedHazard);

  useEffect(() => {
    detectDeviceRegion(
      (region) => {
        setDeviceRegion(region.regionLabel);
        setLanguageOptions(
          languageWasSelected.current && !region.languageCodes.includes(language)
            ? [...region.languageCodes, language]
            : region.languageCodes,
        );
        if (!languageWasSelected.current && !region.languageCodes.includes(language)) {
          setLanguage("en");
        }
      },
      (message) => {
        setDeviceRegion(message);
        setLanguageOptions(["en", "hi"]);
      }
    );

    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  function navigate(view) {
    setActiveView(view);
    setMobileMenuOpen(false);
    setFormMessage("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function submitLocalForm(event) {
    event.preventDefault();
    setFormMessage(
      language === "en"
        ? "Draft recorded on this page only. It has not been sent to an emergency service."
        : "यह केवल इस पृष्ठ पर ड्राफ़्ट है। यह किसी आपातकालीन सेवा को नहीं भेजा गया है।",
    );
    event.currentTarget.reset();
  }

  return (
    <div className="app-shell">
      {mobileMenuOpen && (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation menu"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      <aside className={`sidebar ${mobileMenuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <Icon name="people" size={23} />
          </div>
          <div>
            <strong>AapdaSetu</strong>
            <span>COMMUNITY RESILIENCE</span>
          </div>
          <button
            className="icon-button sidebar-close"
            aria-label="Close menu"
            onClick={() => setMobileMenuOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="pilot-label">ALL-HAZARD RESILIENCE</div>
        <div className="nav-caption">DISASTER LIFECYCLE</div>
        <nav className="primary-nav" aria-label="Main navigation">
          {navigation.map((item, index) => (
            <button
              key={item.id}
              className={`nav-item ${activeView === item.id ? "nav-item-active" : ""}`}
              onClick={() => navigate(item.id)}
              aria-current={activeView === item.id ? "page" : undefined}
            >
              <span className="nav-icon"><Icon name={item.icon} /></span>
              <span>{text[item.id]}</span>
              {index === 0 && <span className="nav-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="data-status-card">
            <span className="status-icon"><Icon name="database" size={18} /></span>
            <div>
              <strong>AapdaSetu services</strong>
              <span>No live warnings or dispatch</span>
            </div>
            <span className="status-indicator" />
          </div>
          <div className="sidebar-credit">
            <span>Designed for communities across India</span>
            <span>Swadeshi for Aatmanirbhar Bharat</span>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button menu-button"
              aria-label="Open navigation menu"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <div className="breadcrumb">
              <span>India · Disaster readiness</span>
              <Icon name="chevron" size={15} />
              <strong>{text[activeView]}</strong>
            </div>
          </div>
          <div className="topbar-actions">
            <span className={`connection-pill ${online ? "" : "connection-offline"}`}>
              <span className="connection-dot" />
              {online ? text.online : text.offline}
            </span>
            <label className="language-control">
              <Icon name="language" size={17} />
              <span className="sr-only">Display language</span>
              <select
                aria-label="Display language"
                title={`Language options: ${deviceRegion}`}
                value={language}
                onChange={(event) => {
                  languageWasSelected.current = true;
                  setLanguage(event.target.value);
                }}
              >
                {languageOptions.map((languageCode) => (
                  <option value={languageCode} key={languageCode}>
                    {getLanguageLabel(languageCode)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>

        <main className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">{text.subtitle}</p>
              <h1>{pageTitle(activeView, text)}</h1>
              <p className="page-description">{pageDescription(activeView, language)}</p>
            </div>
            {selectedModule && (
              <span className="focus-badge">
                <Icon name={selectedModule.icon} size={16} />
                {selectedModule.title}
              </span>
            )}
          </div>

          {activeView === "overview" && (
            <Overview
              text={text}
              selectedHazard={selectedHazard}
              onSelectHazard={setSelectedHazard}
              onNavigate={navigate}
            />
          )}
          {activeView === "prepare" && (
            <Prepare text={text} language={language} onNavigate={navigate} />
          )}
          {activeView === "during" && (
            <During
              language={language}
              selectedHazard={selectedHazard}
              onSelectHazard={setSelectedHazard}
            />
          )}
          {activeView === "response" && (
            <Response
              responseType={responseType}
              setResponseType={setResponseType}
              onSubmit={submitLocalForm}
              formMessage={formMessage}
            />
          )}
          {activeView === "data" && <DataSources />}
          {activeView === "eoc" && <EOCDashboard language={language} />}

          <footer className="page-footer">
            <span>AapdaSetu · All-hazard disaster readiness</span>
            <span>For preparedness and learning · follow local emergency services for live assistance</span>
          </footer>
        </main>
      </div>

      <nav className="mobile-nav" aria-label="Quick navigation">
        {navigation.map((item) => (
          <button
            key={item.id}
            className={activeView === item.id ? "mobile-nav-active" : ""}
            onClick={() => navigate(item.id)}
            aria-current={activeView === item.id ? "page" : undefined}
          >
            <Icon name={item.icon} size={19} />
            <span>{text[item.id]}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

function pageTitle(view, text) {
  const titles = {
    overview: text.overview,
    prepare: text.prepare,
    during: text.during,
    response: text.response,
    data: text.data,
    eoc: "District Emergency Operations Center (DEOC)",
  };
  return titles[view] || text.overview;
}

function pageDescription(view, language) {
  const descriptions = {
    en: {
      overview: "One platform for communities preparing for different kinds of disasters across India.",
      prepare: "Build practical household readiness before local risks increase.",
      during: "Simple, practical safety guidance. Follow local authorities for official instructions.",
      response: "Share a need or offer support. Requests entered here are not sent to responders.",
      data: "See data availability for services and information across hazard areas.",
      eoc: "Situation overview · Lower Kosi Basin · River telemetry, GIS map, SOS triage, shelter capacity, and multilingual alert bulletins.",
    },
    hi: {
      overview: "उपलब्ध जानकारी, बाकी जानकारी और अगले कदम एक जगह देखें।",
      prepare: "स्थानीय जोखिम बढ़ने से पहले घर की व्यावहारिक तैयारी करें।",
      during: "सरल सुरक्षा सुझाव। आधिकारिक निर्देशों के लिए स्थानीय प्रशासन की बात मानें।",
      response: "ज़रूरत बताएँ या सहायता दें।",
      data: "आपदा सेवाओं और स्थानीय जानकारी की उपलब्धता देखें।",
      eoc: "स्थिति का अवलोकन · निचला कोसी बेसिन · नदी टेलीमेट्री, जीआईएस मानचित्र, एसओएस ट्राइएज, आश्रय क्षमता और बहुभाषी चेतावनी बुलेटिन।",
    },
  };
  return descriptions[language]?.[view] || descriptions.en[view];
}

function Overview({ text, selectedHazard, onSelectHazard, onNavigate }) {
  return (
    <>
      <section className="welcome-banner">
        <div className="welcome-copy">
          <span className="banner-kicker"><span className="pulse-dot" /> ALL-HAZARD RESILIENCE</span>
          <h2>Small steps today<br />can make a safer tomorrow.</h2>
          <p>
            AapdaSetu supports communities before, during, and after a wide range
            of natural and human-made disasters.
          </p>
          <div className="banner-actions">
            <button
              className="button button-light"
              onClick={() => {
                onNavigate("during");
              }}
            >
              <Icon name="shield" size={18} /> {text.safetyGuide}
            </button>
            <button className="button button-ghost-light" onClick={() => onNavigate("response")}>
              {text.requestHelp} <Icon name="arrow" size={17} />
            </button>
            <button
              className="button button-primary"
              onClick={() => onNavigate("eoc")}
            >
              <Icon name="alert" size={18} /> Operations center <Icon name="arrow" size={16} />
            </button>
          </div>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="sun-disc" />
          <div className="hill hill-back" />
          <div className="hill hill-front" />
          <div className="ground-shape" />
          <div className="art-home home-one"><i /><b /></div>
          <div className="art-home home-two"><i /><b /></div>
          <div className="art-home home-three"><i /><b /></div>
          <div className="art-person person-one"><i /><b /></div>
          <div className="art-person person-two"><i /><b /></div>
          <span className="art-label">PREPARE · RESPOND · RECOVER</span>
        </div>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="section-kicker">SITUATION BOARD</span>
            <h2>What we know right now</h2>
          </div>
          <span className="data-mode"><span className="status-indicator" /> Current data status</span>
        </div>
        <div className="status-grid">
          <article className="status-card forecast-card">
            <div className="card-icon icon-coral"><Icon name="drop" /></div>
            <div className="card-label">LIVE HAZARD INFORMATION</div>
            <h3>{text.noForecast}</h3>
            <p>{text.noForecastBody}</p>
            <button className="text-link" onClick={() => onNavigate("data")}>
              Why is this unavailable? <Icon name="chevron" size={16} />
            </button>
          </article>
          <article className="status-card">
            <div className="card-icon icon-teal"><Icon name="shield" /></div>
            <div className="card-label">HAZARD COVERAGE</div>
            <h3>{HAZARDS.length} disaster categories</h3>
            <p>Explore focused preparedness and response guidance for natural and human-made hazards.</p>
            <div className="card-meta"><Icon name="check" size={15} /> Select a category to learn more</div>
          </article>
          <article className="status-card">
            <div className="card-icon icon-violet"><Icon name="people" /></div>
            <div className="card-label">SHELTER & RESPONSE</div>
            <h3>Shelter information unavailable</h3>
            <p>Verified shelter locations and local response contacts are not connected for any region.</p>
            <button className="text-link" onClick={() => onNavigate("during")}>
              See safety guidance <Icon name="chevron" size={16} />
            </button>
          </article>
        </div>
      </section>

      <section className="module-section">
        <div className="section-heading">
          <div>
            <span className="section-kicker">ONE CORE · HAZARD-SPECIFIC MODULES</span>
            <h2>Designed for the risks communities face</h2>
          </div>
          <span className="data-mode">Select a hazard for guidance</span>
        </div>
        {selectedHazard !== "all" && (
          <div className="module-focus" role="status">
            <span>{HAZARDS.find((module) => module.id === selectedHazard)?.title} selected</span>
            <span>Open its safety guide for response steps and emergency contacts.</span>
            <button onClick={() => onSelectHazard("all")}>Clear selection</button>
          </div>
        )}
        <div className="hazard-module-grid">
          {HAZARDS.map((module) => (
            <button
              className={`hazard-module-card ${selectedHazard === module.id ? "hazard-module-selected" : ""}`}
              key={module.id}
              onClick={() => {
                onSelectHazard(module.id);
                onNavigate("during");
              }}
              aria-label={`Open ${module.title} safety guide`}
            >
              <span className={`module-icon module-icon-${module.id}`}><Icon name={module.icon} size={19} /></span>
              <span className="module-status">Safety guide</span>
              <strong>{module.title}</strong>
              <small>{module.focus}</small>
            </button>
          ))}
        </div>
      </section>

      <div className="overview-lower">
        <section className="panel next-steps-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">START HERE</span>
              <h2>Preparedness checklist</h2>
            </div>
            <span className="checklist-count">3 steps</span>
          </div>
          <div className="checklist">
            <button onClick={() => onNavigate("during")}>
              <span className="check-circle"><Icon name="check" size={15} /></span>
              <span><strong>Know where to get updates</strong><small>Follow district and local authority guidance.</small></span>
              <Icon name="chevron" size={17} />
            </button>
            <button onClick={() => onNavigate("during")}>
              <span className="check-circle"><Icon name="check" size={15} /></span>
              <span><strong>Plan how to reconnect</strong><small>Agree on a meeting point and how to contact one another.</small></span>
              <Icon name="chevron" size={17} />
            </button>
            <button onClick={() => onNavigate("response")}>
              <span className="check-circle"><Icon name="check" size={15} /></span>
              <span><strong>Keep essential contacts handy</strong><small>Save local emergency numbers on your phone.</small></span>
              <Icon name="chevron" size={17} />
            </button>
          </div>
          <div className="help-note"><span>i</span> This checklist is general guidance, not an official alert.</div>
        </section>
      </div>

      <div className="lifecycle-strip">
        <div className="lifecycle-intro"><span className="section-kicker">THROUGH EVERY PHASE</span><h2>Prepared together</h2></div>
        {[
          ["01", "Before", "Prepare with trusted information", "prepare"],
          ["02", "During", "Keep people and families safer", "during"],
          ["03", "After", "Connect needs with local support", "response"],
        ].map(([number, title, caption, view]) => (
          <button className="lifecycle-card" key={number} onClick={() => onNavigate(view)}>
            <span>{number}</span><strong>{title}</strong><small>{caption}</small>
            <Icon name="arrow" size={16} />
          </button>
        ))}
      </div>
    </>
  );
}

function Prepare({ text, language, onNavigate }) {
  return (
    <>
      <div className="notice-banner notice-amber">
        <span className="notice-symbol">!</span>
      <div><strong>No live hazard forecasts</strong><p>This dashboard does not currently publish a risk category or warning.</p></div>
        <button className="text-link" onClick={() => onNavigate("data")}>View data status <Icon name="chevron" size={16} /></button>
      </div>
      <div className="prepare-grid">
        <section className="panel prepare-main">
          <div className="section-heading">
            <div><span className="section-kicker">BEFORE A DISASTER</span><h2>Be ready before local risks increase</h2></div>
            <span className="tag-neutral">General guidance</span>
          </div>
          <div className="prepare-list">
            <GuideCard number="01" title="Stay informed" text="Follow official updates from district administration, local authorities, and trusted radio or news channels." />
            <GuideCard number="02" title="Make a household plan" text="Agree on a meeting point, how to contact one another, and who may need extra help." />
            <GuideCard number="03" title="Prepare essentials" text="Keep essential medicines, a torch, charged power bank, important documents, and locally relevant supplies together." />
            <GuideCard number="04" title="Know how to respond" text="Learn what local authorities recommend for the hazards in your area. Follow their instructions during an emergency." />
          </div>
          <div className="guidance-source"><Icon name="shield" size={17} /> General preparedness information · Follow official local instructions.</div>
        </section>
        <aside className="panel alert-preview">
          <span className="section-kicker">ALERT PREVIEW</span>
          <div className="preview-icon"><Icon name="language" size={21} /></div>
          <h2>Regional-language alerts</h2>
          <p>Alert delivery is not connected. Bhashini credentials are not configured, so local translations are used where available and other text stays in English.</p>
          <label className="field-label" htmlFor="preview-language">Preview language</label>
          <select id="preview-language" value={language} disabled>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
          </select>
          <div className="empty-preview">{getTranslationFallbackNotice(language) || "English is the source language. No alert is sent from this page."}</div>
          <span className="preview-status"><span /> Local fallback active · no alert sent</span>
        </aside>
      </div>
    </>
  );
}

function GuideCard({ number, title, text }) {
  return (
    <article className="guide-card">
      <span className="guide-number">{number}</span>
      <div><h3>{title}</h3><p>{text}</p></div>
      <Icon name="check" size={18} />
    </article>
  );
}

function During({ language, selectedHazard, onSelectHazard }) {
  const [openHazardId, setOpenHazardId] = useState(
    selectedHazard === "all" ? "" : selectedHazard,
  );
  const phaseLabels = {
    before: translateWithFallback("Before", language).text,
    during: translateWithFallback("During", language).text,
    after: translateWithFallback("After", language).text,
  };
  const fallbackNotice = getTranslationFallbackNotice(language);

  return (
    <>
      <div className="notice-banner notice-blue">
        <span className="notice-symbol"><Icon name="shield" size={19} /></span>
        <div>
          <strong>Choose a hazard to open its safety guide</strong>
          <p>Guidance is general. Follow current instructions from local authorities and emergency services.</p>
        </div>
      </div>
      <LocationSharing language={language} />
      <section className="safety-directory" aria-label="Disaster safety guides">
        {HAZARDS.map((hazard) => {
          const isOpen = openHazardId === hazard.id;
          const detailsId = `safety-guide-${hazard.id}`;
          return (
            <article className={`panel safety-directory-card ${isOpen ? "safety-directory-card-open" : ""}`} key={hazard.id}>
              <span className={`module-icon module-icon-${hazard.id}`}><Icon name={hazard.icon} size={20} /></span>
              <h2>{hazard.title}</h2>
              <p>{hazard.focus}</p>
              <button
                aria-controls={detailsId}
                aria-expanded={isOpen}
                className="button button-outline safety-guide-toggle"
                onClick={() => {
                  const nextOpenId = isOpen ? "" : hazard.id;
                  setOpenHazardId(nextOpenId);
                  onSelectHazard(nextOpenId || "all");
                }}
              >
                {isOpen ? "Close safety guide" : "View safety guide"}
                <Icon name={isOpen ? "close" : "chevron"} size={16} />
              </button>
              {isOpen && (
                <div className="safety-guide-card-content" id={detailsId}>
                  <h3>{hazard.title} safety guide</h3>
                  <table className="safety-guide-table">
                    <thead>
                      <tr><th scope="col">Phase</th><th scope="col">What to do</th></tr>
                    </thead>
                    <tbody>
                      {Object.entries(hazard.guidance).map(([phase, instructions]) => (
                        <tr key={phase}>
                          <th scope="row">{phaseLabels[phase]}</th>
                          <td>
                            <ul>
                              {instructions.map((instruction) => <li key={instruction}>{instruction}</li>)}
                            </ul>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {fallbackNotice && <p className="safety-language-note" role="status">{fallbackNotice}</p>}
                  <EmergencyContactList hazardId={hazard.id} language={language} compact />
                </div>
              )}
            </article>
          );
        })}
      </section>
    </>
  );
}

function EmergencyContactList({ hazardId, language, compact = false }) {
  const contacts = getEmergencyContacts(hazardId);
  const text = translations[language];

  return (
    <section className={`emergency-contacts ${compact ? "emergency-contacts-compact" : ""}`}>
      {!compact && <h3>{text.emergencyContacts}</h3>}
      <div className="emergency-contact-list">
        {contacts.map((contact) => {
          const translatedLabel = translateWithFallback(contact.label, language).text;
          return (
            <a className="emergency-contact-link" href={`tel:${contact.number}`} key={contact.number}>
              <span className="contact-link-icon"><Icon name="phone" size={15} /></span>
              <span className="contact-link-copy">
                <strong>{translatedLabel}</strong>
                <small>{contact.note}</small>
              </span>
              <strong className="contact-number">{contact.number}</strong>
            </a>
          );
        })}
      </div>
      {!compact && <p className="contact-coverage-note">{text.contactCoverage}</p>}
    </section>
  );
}

function LocationSharing({ language }) {
  const text = translations[language];
  const [coordinates, setCoordinates] = useState(null);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function requestLocation() {
    if (!navigator.geolocation) {
      setMessage(text.locationUnavailable);
      return;
    }

    setIsLoading(true);
    setMessage("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setCoordinates({
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy: coords.accuracy,
        });
        setIsLoading(false);
      },
      () => {
        setIsLoading(false);
        setMessage(text.locationUnavailable);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15_000 },
    );
  }

  function getShareText() {
    if (!coordinates) {
      return "";
    }
    return `My current location: ${coordinates.latitude.toFixed(5)}, ${coordinates.longitude.toFixed(5)} (accuracy about ${Math.round(coordinates.accuracy)} m)`;
  }

  async function shareLocation() {
    if (!coordinates) {
      return;
    }
    if (!navigator.share) {
      setMessage("Device sharing is unavailable. Copy the location and share it yourself.");
      return;
    }

    try {
      await navigator.share({ title: "My current location", text: getShareText() });
      setMessage("Location shared using your device's share sheet.");
    } catch (error) {
      if (error.name === "AbortError") {
        setMessage(text.locationShareCancelled);
        return;
      }
      setMessage("Could not open device sharing. Copy the location and share it yourself.");
    }
  }

  async function copyLocation() {
    try {
      await navigator.clipboard.writeText(getShareText());
      setMessage(text.locationCopied);
    } catch {
      setMessage("Clipboard access is unavailable. Select and copy the location text.");
    }
  }

  return (
    <section className="panel location-sharing-panel">
      <div className="location-sharing-copy">
        <span className="location-sharing-icon"><Icon name="pin" size={20} /></span>
        <div>
          <h2>{text.locationShare}</h2>
          <p>{text.locationPrivacy}</p>
        </div>
      </div>
      {!coordinates ? (
        <button className="button button-outline" disabled={isLoading} onClick={requestLocation}>
          <Icon name="pin" size={16} />
          {isLoading ? text.locationPending : text.requestLocation}
        </button>
      ) : (
        <>
          <p className="location-coordinates" aria-live="polite">
            {coordinates.latitude.toFixed(5)}, {coordinates.longitude.toFixed(5)}
            <small>Approx. accuracy: {Math.round(coordinates.accuracy)} m</small>
          </p>
          <div className="location-actions">
            <button className="button button-primary" onClick={shareLocation}>
              <Icon name="arrow" size={16} /> {text.shareLocation}
            </button>
            <button className="button button-outline" onClick={copyLocation}>
              {text.copyLocation}
            </button>
          </div>
        </>
      )}
      {message && <p className="location-status" role="status">{message}</p>}
    </section>
  );
}

function Response({ responseType, setResponseType, onSubmit, formMessage }) {
  return (
    <>
      <div className="notice-banner notice-amber">
        <span className="notice-symbol">!</span>
        <div><strong>Request form · not monitored</strong><p>Information entered here is not sent to responders.</p></div>
      </div>
      <div className="response-layout">
        <section className="panel response-form-panel">
          <div className="response-tabs" role="tablist" aria-label="Choose a response form">
            <button className={responseType === "request" ? "response-tab active" : "response-tab"} onClick={() => { setResponseType("request"); }}>
              <Icon name="life" size={18} /> I need help
            </button>
            <button className={responseType === "offer" ? "response-tab active" : "response-tab"} onClick={() => { setResponseType("offer"); }}>
              <Icon name="people" size={18} /> I can help
            </button>
          </div>
          <div className="form-intro">
            <span className="section-kicker">{responseType === "request" ? "REQUEST SUPPORT" : "OFFER SUPPORT"}</span>
            <h2>{responseType === "request" ? "Tell us what you need" : "Share how you can help"}</h2>
            <p>{responseType === "request" ? "Provide the basic details needed to describe a request for support." : "Provide the basic details of support you can offer."}</p>
          </div>
          <form className="response-form" onSubmit={onSubmit}>
            <div className="form-row">
              <label>
                {responseType === "request" ? "Type of need" : "Type of support"}
                <select required defaultValue="">
                  <option value="" disabled>Select an option</option>
                  {(responseType === "request"
                    ? ["Food and drinking water", "Medical assistance", "Rescue / evacuation", "Temporary shelter", "Other"]
                    : ["Food and drinking water", "Medical assistance", "Transport", "Temporary shelter", "Other"]
                  ).map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label>
                {responseType === "request" ? "Urgency" : "Available capacity"}
                <select required defaultValue="">
                  <option value="" disabled>Select an option</option>
                  {(responseType === "request"
                    ? ["Urgent — immediate safety concern", "High — needed today", "General — when possible"]
                    : ["1–5 people", "6–20 people", "More than 20 people"]
                  ).map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
            </div>
            <div className="form-row">
              <label>
                State / district
                <input required placeholder="Enter state and district" />
              </label>
              <label>
                Village / ward / nearby landmark
                <input required placeholder="Enter a local area or landmark" />
              </label>
            </div>
            <label>
              {responseType === "request" ? "What should responders know?" : "Any details about your offer?"}
              <textarea rows="4" placeholder="Share only the details needed to understand the situation." />
            </label>
            <label className="consent-row">
              <input type="checkbox" required />
              <span>I understand this form will not contact emergency services or send information to responders.</span>
            </label>
            <div className="form-actions">
              <button className="button button-primary" type="submit">
                {responseType === "request" ? "Preview request" : "Preview offer"} <Icon name="arrow" size={17} />
              </button>
              <span><Icon name="database" size={15} /> This form does not transmit or store submissions</span>
            </div>
            {formMessage && <div className="form-confirmation" role="status">{formMessage}</div>}
          </form>
        </section>
        <aside className="response-aside">
          <div className="panel matching-panel">
            <span className="section-kicker">HOW MATCHING WILL WORK</span>
            <h2>Needs meet local capacity</h2>
            <p>Requests and offers can be organized around location, need type, and urgency.</p>
            <div className="match-steps">
              <div><span>1</span><p><strong>Share a need or offer</strong><small>Specific, useful information</small></p></div>
              <div><span>2</span><p><strong>Review nearby options</strong><small>Distance and availability</small></p></div>
              <div><span>3</span><p><strong>Confirm a match</strong><small>Only after human confirmation</small></p></div>
            </div>
            <div className="privacy-note"><Icon name="shield" size={17} /> Do not enter sensitive personal or medical details in this prototype.</div>
          </div>
        </aside>
      </div>
    </>
  );
}

function DataSources() {
  return (
    <>
      <section className="data-summary">
        <div className="data-summary-copy">
          <span className="section-kicker">ALL-HAZARD DATA READINESS</span>
          <h2>Regional services and verified information</h2>
          <p>Data and services must be verified for each local area before they can support live decisions.</p>
        </div>
        <div className="readiness-badge"><span /> LIVE SERVICES NOT CONNECTED</div>
      </section>
      <div className="data-stat-grid">
        <div className="data-stat"><span className="stat-label">LIVE HAZARD FEEDS</span><strong className="stat-pending">Unavailable</strong><small>No live source is connected</small></div>
        <div className="data-stat"><span className="stat-label">VERIFIED SHELTERS</span><strong className="stat-pending">Unavailable</strong><small>Local coordinates are not connected</small></div>
        <div className="data-stat"><span className="stat-label">EMERGENCY CONTACT</span><strong>112</strong><small>India emergency response number</small></div>
      </div>
      <section className="panel data-table-panel">
        <div className="panel-heading">
          <div><span className="section-kicker">SERVICE AVAILABILITY</span><h2>Information shown on this dashboard</h2></div>
        </div>
        <div className="source-list">
          <SourceRow status="pending" title="Live forecasts and official alerts" detail="No live forecast or alert service is connected." />
          <SourceRow status="pending" title="Local shelter locations and safe routes" detail="No verified local shelter or route recommendations are available." />
          <SourceRow status="pending" title="Regional-language alert delivery" detail="Translation and alert delivery services are not connected." />
          <SourceRow status="available" title="Safety guidance" detail="General hazard-specific information is available in the safety guides." />
          <SourceRow status="available" title="Emergency contact" detail="India emergency response number: 112." />
        </div>
      </section>
    </>
  );
}

function SourceRow({ status, title, detail }) {
  return (
    <div className="source-row">
      <span className={`source-status ${status}`}>{status === "available" ? <Icon name="check" size={14} /> : <Icon name="clock" size={14} />}</span>
      <span><strong>{title}</strong><small>{detail}</small></span>
      <span className={`source-status-label ${status}`}>{status === "available" ? "AVAILABLE" : "NOT CONNECTED"}</span>
    </div>
  );
}

export default App;
