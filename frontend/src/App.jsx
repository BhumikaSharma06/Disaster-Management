import { useCallback, useEffect, useRef, useState } from "react";

import EOCDashboard from "./components/EOCDashboard.jsx";
import { AdminUsers, AuthView } from "./components/AuthViews.jsx";
import ProfileSettings from "./components/ProfileSettings.jsx";
import { ResponderInbox, Response } from "./components/SupplyCoordination.jsx";
import SosReportForm from "./components/SosReportForm.jsx";
import {
  clearAccessToken,
  getAccessToken,
  getCurrentUser,
  logoutAccount,
  requestResponderRole,
} from "./api/auth.js";
import { getInboxCount } from "./api/coordination.js";
import { getPublishedSafetyTips } from "./api/safety.js";
import { syncCoordinationQueue } from "./offline/syncCoordinationQueue.js";
import { HAZARDS, getEmergencyContacts } from "./data/hazards.js";
import {
  getTranslationFallbackNotice,
  translateWithFallback,
} from "./bhasini/translation.js";
import {
  detectDeviceRegion,
  getLanguageLabel,
} from "./i18n/deviceLanguage.js";
import {
  getCoreStatus,
  getLiveForecasts,
  getLocalReadiness,
  getNearestShelters,
  searchPlaces,
} from "./api/geography.js";

const translations = {
  en: {
    overview: "Overview",
    prepare: "Be prepared",
    during: "During a disaster",
    response: "Get or offer help",
    responders: "Responder inbox",
    admin: "Admin accounts",
    auth: "Account access",
    profile: "My profile",
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
    responderBadge: "Responder inbox",
  },
  hi: {
    overview: "अवलोकन",
    prepare: "तैयार रहें",
    during: "आपदा के दौरान",
    response: "मदद लें या दें",
    responders: "रिस्पॉन्डर इनबॉक्स",
    admin: "व्यवस्थापक खाते",
    auth: "खाता प्रवेश",
    profile: "मेरी प्रोफ़ाइल",
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
    responderBadge: "रिस्पॉन्डर इनबॉक्स",
  },
};

const navigation = [
  { id: "overview", icon: "grid" },
  { id: "prepare", icon: "shield" },
  { id: "during", icon: "life" },
  { id: "response", icon: "people" },
  { id: "responders", icon: "health" },
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
  const [activeView, setActiveView] = useState(() =>
    new URLSearchParams(window.location.search).has("verify_token") ? "auth" : "overview"
  );
  const [selectedHazard, setSelectedHazard] = useState("all");
  const [language, setLanguage] = useState("en");
  const [languageOptions, setLanguageOptions] = useState(["en", "hi"]);
  const [deviceRegion, setDeviceRegion] = useState("Checking device region");
  const [online, setOnline] = useState(navigator.onLine);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [inboxCount, setInboxCount] = useState(0);
  const [coordinationCountError, setCoordinationCountError] = useState("");
  const [coordinationSyncError, setCoordinationSyncError] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authStatusMessage, setAuthStatusMessage] = useState("");
  const [roleRequestMessage, setRoleRequestMessage] = useState("");
  const [logoutError, setLogoutError] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [authViewKey, setAuthViewKey] = useState(0);
  const [verificationToken, setVerificationToken] = useState(() =>
    new URLSearchParams(window.location.search).get("verify_token")
  );
  const languageWasSelected = useRef(false);
  const canAccessResponderInbox = Boolean(currentUser?.is_responder || currentUser?.is_admin);
  const refreshCurrentUser = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      setAuthStatusMessage("");
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        clearAccessToken();
        setCurrentUser(null);
        setAuthStatusMessage("Your sign-in session or account access is no longer valid. Sign in again.");
      } else {
        setAuthStatusMessage(`Could not verify your account access: ${error.message}`);
      }
    }
  }, []);

  const refreshInboxCount = useCallback(async () => {
    if (!canAccessResponderInbox) {
      setInboxCount(0);
      setCoordinationCountError("");
      return;
    }
    try {
      const result = await getInboxCount();
      setInboxCount(result.count);
      setCoordinationCountError("");
    } catch (error) {
      setInboxCount(0);
      if (error.status === 401 || error.status === 403) {
        await refreshCurrentUser();
        setCoordinationCountError("");
      } else {
        setCoordinationCountError(error.message);
      }
    }
  }, [canAccessResponderInbox, refreshCurrentUser]);

  const text = translations[language];
  const selectedModule = HAZARDS.find((module) => module.id === selectedHazard);
  const visibleNavigation = [
    ...navigation.filter((item) =>
      item.id !== "responders" || canAccessResponderInbox
    ),
    ...(currentUser ? [{ id: "profile", icon: "people" }] : []),
    ...(currentUser?.is_admin ? [{ id: "admin", icon: "health" }] : []),
  ];

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

  useEffect(() => {
    refreshInboxCount();
    const intervalId = window.setInterval(refreshInboxCount, 30000);
    window.addEventListener("online", refreshInboxCount);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("online", refreshInboxCount);
    };
  }, [refreshInboxCount, currentUser?.id, currentUser?.is_admin, currentUser?.is_responder]);

  useEffect(() => {
    let active = true;
    const syncPendingSubmissions = async () => {
      try {
        const result = await syncCoordinationQueue();
        if (!active) return;
        if (result.error) {
          setCoordinationSyncError(result.error.message);
          return;
        }
        setCoordinationSyncError("");
        if (result.synced > 0) refreshInboxCount();
      } catch (error) {
        if (active) setCoordinationSyncError(error.message);
      }
    };
    syncPendingSubmissions();
    const intervalId = window.setInterval(syncPendingSubmissions, 30000);
    window.addEventListener("online", syncPendingSubmissions);
    return () => {
      active = false;
      window.clearInterval(intervalId);
      window.removeEventListener("online", syncPendingSubmissions);
    };
  }, [refreshInboxCount]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setAuthLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    getCurrentUser(controller.signal)
      .then(setCurrentUser)
      .catch((error) => {
        if (error.name !== "AbortError") {
          clearAccessToken();
          setCurrentUser(null);
          setAuthStatusMessage("Your saved sign-in session could not be verified. Please sign in again.");
        }
      })
      .finally(() => setAuthLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (verificationToken) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [verificationToken]);

  function navigate(view) {
    setActiveView(view);
    setMobileMenuOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openAccountAccess(mode = "login") {
    setAuthMode(mode);
    setAuthViewKey((key) => key + 1);
    navigate("auth");
  }

  async function signOut() {
    setLogoutError("");
    const logoutRequest = logoutAccount();
    clearAccessToken();
    setCurrentUser(null);
    setRoleRequestMessage("");
    setAuthStatusMessage("");
    setMobileMenuOpen(false);
    navigate("overview");

    try {
      await logoutRequest;
    } catch (error) {
      setLogoutError(`Signed out on this device, but server logout could not be confirmed: ${error.message}`);
    }
  }

  async function submitResponderRoleRequest() {
    setRoleRequestMessage("");
    try {
      const updatedUser = await requestResponderRole();
      setCurrentUser(updatedUser);
      setRoleRequestMessage("Responder access requested. You can continue using AapdaSetu as a community user while an admin reviews your request.");
    } catch (error) {
      setRoleRequestMessage(error.message);
    }
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
          {visibleNavigation.map((item, index) => (
            <button
              key={item.id}
              className={`nav-item ${activeView === item.id ? "nav-item-active" : ""}`}
              onClick={() => navigate(item.id)}
              aria-current={activeView === item.id ? "page" : undefined}
            >
              <span className="nav-icon"><Icon name={item.icon} /></span>
              <span>{text[item.id]}</span>
              {item.id === "responders" && (
                <span className="nav-count" aria-label={`${text.responderBadge} (${inboxCount})`}>{inboxCount}</span>
              )}
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
            <div className="account-actions">
              {authLoading ? (
                <span className="account-loading">Checking account…</span>
              ) : currentUser ? (
                <>
                  <span className="account-identity">
                    <strong>{currentUser.full_name}</strong>
                    <small>{currentUser.is_super_admin ? "Super Admin" : currentUser.is_admin ? "Admin" : currentUser.is_responder ? "Approved responder" : currentUser.responder_request_status === "pending" ? "Responder approval pending" : "Community user"}</small>
                  </span>
                  {!currentUser.is_admin && !currentUser.is_responder && currentUser.responder_request_status !== "pending" && (
                    <button className="account-button account-responder-request" type="button" onClick={submitResponderRoleRequest}>
                      Request responder access
                    </button>
                  )}
                  <button className="account-button" type="button" onClick={signOut}>Log out</button>
                </>
              ) : (
                <>
                  <button className="account-button" type="button" onClick={() => openAccountAccess("login")}>Sign in</button>
                  <button className="account-button account-button-primary" type="button" onClick={() => openAccountAccess("register")}>Create account</button>
                </>
              )}
            </div>
          </div>
        </header>

        <main className="content">
          {logoutError && <div className="auth-message auth-message-error" role="alert">{logoutError}</div>}
          {authStatusMessage && <div className="auth-message auth-message-error" role="alert">{authStatusMessage}</div>}
          {coordinationCountError && ["response", "responders", "eoc"].includes(activeView) && (
            <div className="auth-message auth-message-error" role="alert">{coordinationCountError}</div>
          )}
          {coordinationSyncError && activeView === "response" && (
            <div className="auth-message auth-message-error" role="alert">
              A saved submission has not synced yet: {coordinationSyncError}
            </div>
          )}
          {roleRequestMessage && <div className="role-request-message" role="status">{roleRequestMessage}</div>}
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
            <>
              <SosReportForm />
              <Response
                language={language}
                currentUser={currentUser}
                onOpenInbox={() => navigate("responders")}
                submissionCount={inboxCount}
                onCountChanged={refreshInboxCount}
                canOpenInbox={canAccessResponderInbox}
              />
            </>
          )}
          {activeView === "responders" && (
            authLoading ? null : !currentUser ? (
              <AccessNotice
                title="Responder access requires an account"
                message="Sign in with a verified account marked as a responder to open responder tools."
                onSignIn={() => openAccountAccess("login")}
              />
            ) : !canAccessResponderInbox ? (
              <AccessNotice
                title="Responder role required"
                message="This account is not marked as a responder. You can still submit a help request or supply offer from Get or offer help."
              />
            ) : (
              <ResponderInbox
                language={language}
                onCountChanged={refreshInboxCount}
                currentUser={currentUser}
                submissionCount={inboxCount}
                onAccessDenied={refreshCurrentUser}
              />
            )
          )}
          {activeView === "admin" && (
            currentUser?.is_admin
              ? <AdminUsers currentUser={currentUser} />
              : <AccessNotice
                  title="Administrator access required"
                  message="This area is restricted to administrator accounts."
                  onSignIn={!currentUser ? () => openAccountAccess("login") : undefined}
                />
          )}
          {activeView === "auth" && (
            <AuthView
              key={authViewKey}
              initialMode={authMode}
              verificationToken={verificationToken}
              onAuthenticated={(user) => {
                setCurrentUser(user);
                setAuthStatusMessage("");
                setLogoutError("");
                setVerificationToken(null);
                navigate(user.is_admin ? "admin" : "overview");
              }}
            />
          )}
          {activeView === "profile" && currentUser && (
            <ProfileSettings
              currentUser={currentUser}
              onProfileUpdated={setCurrentUser}
            />
          )}
          {activeView === "data" && <DataSources />}
          {activeView === "eoc" && (
            <EOCDashboard
              language={language}
              onCoordinationUpdated={refreshInboxCount}
              canModerate={Boolean(currentUser?.is_admin || currentUser?.is_responder)}
              canManageIncidents={Boolean(currentUser?.is_admin)}
            />
          )}

          <footer className="page-footer">
            <span>AapdaSetu · All-hazard disaster readiness</span>
            <span>For preparedness and learning · follow local emergency services for live assistance</span>
          </footer>
        </main>
      </div>

      <nav className="mobile-nav" aria-label="Quick navigation">
        {visibleNavigation.map((item) => (
          <button
            key={item.id}
            className={activeView === item.id ? "mobile-nav-active" : ""}
            onClick={() => navigate(item.id)}
            aria-current={activeView === item.id ? "page" : undefined}
          >
            <Icon name={item.icon} size={19} />
            <span>{text[item.id]}</span>
            {item.id === "responders" && (
              <span className="nav-count" aria-label={`${text.responderBadge} (${inboxCount})`}>{inboxCount}</span>
            )}
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
    responders: text.responders,
    admin: text.admin,
    auth: text.auth,
    profile: text.profile,
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
      response: "Request essential relief supplies or pledge available items for coordinated responder delivery.",
      responders: "Review, claim, and track active help requests and supply offers across your response area.",
      admin: "Manage account visibility and review registered roles.",
      auth: "Sign in or create an account to access role-gated features.",
      profile: "Manage your saved contact details and usual address for quicker form filling.",
      data: "See data availability for services and information across hazard areas.",
      eoc: "Situation overview · live service status, coordination records, readiness information, and response capacity.",
    },
    hi: {
      overview: "उपलब्ध जानकारी, बाकी जानकारी और अगले कदम एक जगह देखें।",
      prepare: "स्थानीय जोखिम बढ़ने से पहले घर की व्यावहारिक तैयारी करें।",
      during: "सरल सुरक्षा सुझाव। आधिकारिक निर्देशों के लिए स्थानीय प्रशासन की बात मानें।",
      response: "रिस्पॉन्डर समन्वय के लिए आवश्यक राहत सामग्री का अनुरोध करें या उपलब्ध वस्तुएँ देने का प्रस्ताव दें।",
      responders: "अपने प्रतिक्रिया क्षेत्र में सक्रिय सहायता अनुरोध और सामग्री प्रस्ताव देखें, स्वीकारें और उनकी प्रगति दर्ज करें।",
      admin: "खातों और पंजीकृत भूमिकाओं की समीक्षा करें।",
      auth: "भूमिका-आधारित सुविधाओं के लिए साइन इन करें या खाता बनाएँ।",
      profile: "फॉर्म जल्दी भरने के लिए अपने संपर्क विवरण और सामान्य पता प्रबंधित करें।",
      data: "आपदा सेवाओं और स्थानीय जानकारी की उपलब्धता देखें।",
      eoc: "स्थिति का अवलोकन · सेवाओं की स्थिति, समन्वय रिकॉर्ड, तैयारी की जानकारी और सहायता क्षमता।",
    },
  };
  return descriptions[language]?.[view] || descriptions.en[view];
}

function AccessNotice({ title, message, onSignIn }) {
  return (
    <section className="panel access-notice">
      <span className="access-notice-icon"><Icon name="health" size={23} /></span>
      <span className="section-kicker">ROLE-RESTRICTED AREA</span>
      <h2>{title}</h2>
      <p>{message}</p>
      {onSignIn && (
        <button className="button button-primary" type="button" onClick={onSignIn}>
          Sign in or register
        </button>
      )}
    </section>
  );
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
  const [safetyTips, setSafetyTips] = useState([]);
  const [safetyTipsLoading, setSafetyTipsLoading] = useState(true);
  const [safetyTipsError, setSafetyTipsError] = useState("");
  const phaseLabels = {
    before: translateWithFallback("Before", language).text,
    during: translateWithFallback("During", language).text,
    after: translateWithFallback("After", language).text,
  };
  const fallbackNotice = getTranslationFallbackNotice(language);

  useEffect(() => {
    const controller = new AbortController();
    getPublishedSafetyTips(controller.signal)
      .then((tips) => {
        if (!Array.isArray(tips)) {
          throw new Error("The safety guidance service returned an unexpected response.");
        }
        setSafetyTips(tips);
        setSafetyTipsError("");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setSafetyTipsError(error.message);
      })
      .finally(() => setSafetyTipsLoading(false));
    return () => controller.abort();
  }, []);

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
                  {safetyTipsLoading ? (
                    <p className="safety-language-note" role="status">Loading published safety guidance…</p>
                  ) : safetyTipsError ? (
                    <p className="auth-message auth-message-error" role="alert">{safetyTipsError}</p>
                  ) : safetyTips.filter((tip) => tip.hazard_type === hazard.id || tip.hazard_type === "all-hazards").length === 0 ? (
                    <p className="safety-language-note">No published safety guidance is currently available for this hazard.</p>
                  ) : (
                    <table className="safety-guide-table">
                    <thead>
                      <tr><th scope="col">Phase</th><th scope="col">What to do</th></tr>
                    </thead>
                    <tbody>
                      {["before", "during", "after"].map((phase) => {
                        const instructions = safetyTips
                          .filter((tip) => (tip.hazard_type === hazard.id || tip.hazard_type === "all-hazards") && tip.phase === phase)
                          .map((tip) => tip.content);
                        return instructions.length === 0 ? null : (
                        <tr key={phase}>
                          <th scope="row">{phaseLabels[phase]}</th>
                          <td>
                            <ul>
                              {instructions.map((instruction) => <li key={instruction}>{instruction}</li>)}
                            </ul>
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                    </table>
                  )}
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

function DataSources() {
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [forecasts, setForecasts] = useState(null);
  const [localReadiness, setLocalReadiness] = useState(null);
  const [nearestShelters, setNearestShelters] = useState(null);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [placeQuery, setPlaceQuery] = useState("");
  const [placeResults, setPlaceResults] = useState([]);
  const [placeProvider, setPlaceProvider] = useState("");
  const [placeMessage, setPlaceMessage] = useState("");
  const [hasLocalSuggestions, setHasLocalSuggestions] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [activePlaceIndex, setActivePlaceIndex] = useState(-1);
  const [searchingPlaces, setSearchingPlaces] = useState(false);
  const [localMessage, setLocalMessage] = useState("");

  const loadStatus = async (signal) => {
    setStatusError("");
    try {
      setStatus(await getCoreStatus(signal));
    } catch (error) {
      if (error.name !== "AbortError") {
        setStatusError("Could not reach the AapdaSetu backend status endpoint.");
        setStatus(null);
      }
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    loadStatus(controller.signal);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const query = placeQuery.trim();
    if (selectedPlace && (placeQuery === (selectedPlace.display_name || selectedPlace.name))) {
      setPlaceResults([]);
      setActivePlaceIndex(-1);
      return undefined;
    }
    if (query.length < 2) {
      setPlaceResults([]);
      setPlaceProvider("");
      setActivePlaceIndex(-1);
      return undefined;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(async () => {
      setSearchingPlaces(true);
      try {
        const data = await searchPlaces(query, 6, controller.signal);
        setPlaceResults(data.results || []);
        setPlaceProvider(data.provider || "");
        setHasLocalSuggestions(Boolean(data.has_local_suggestions));
        setPlaceMessage(data.message || "");
        setActivePlaceIndex(-1);
      } catch (error) {
        if (error.name !== "AbortError") {
          setPlaceResults([]);
          setPlaceProvider("");
        }
      } finally {
        if (!controller.signal.aborted) setSearchingPlaces(false);
      }
    }, 350);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [placeQuery, selectedPlace]);

  async function refreshForecasts() {
    const controller = new AbortController();
    setRefreshing(true);
    setLocalMessage("");
    try {
      const [statusData, forecastData] = await Promise.all([
        getCoreStatus(controller.signal),
        getLiveForecasts(true, controller.signal),
      ]);
      setStatus(statusData);
      setForecasts(forecastData);
    } catch (error) {
      setLocalMessage(error.message || "The live provider refresh failed.");
    } finally {
      setRefreshing(false);
    }
  }

  function handlePlaceInputKeyDown(event) {
    if (event.key === "Escape") {
      setPlaceResults([]);
      setActivePlaceIndex(-1);
      return;
    }
    if (placeResults.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActivePlaceIndex((current) =>
        current >= placeResults.length - 1 ? 0 : current + 1,
      );
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActivePlaceIndex((current) =>
        current <= 0 ? placeResults.length - 1 : current - 1,
      );
    } else if (event.key === "Enter" && activePlaceIndex >= 0) {
      event.preventDefault();
      selectPlace(placeResults[activePlaceIndex]);
    }
  }

  async function submitPlaceSearch(event) {
    event.preventDefault();
    const query = placeQuery.trim();
    if (query.length < 2) {
      setLocalMessage("Enter at least two characters, such as a district or city name.");
      return;
    }

    const controller = new AbortController();
    setSearchingPlaces(true);
    setPlaceResults([]);
    setPlaceProvider("");
    setLocalMessage("Searching India place names…");
    try {
      const data = await searchPlaces(query, 5, controller.signal);
      setPlaceResults(data.results || []);
      setSelectedPlace(null);
      setPlaceProvider(data.provider || "");
      setHasLocalSuggestions(Boolean(data.has_local_suggestions));
      setPlaceMessage(data.message || "");
      setLocalMessage(
        data.results?.length
          ? `${data.results.length} location${data.results.length === 1 ? "" : "s"} found. Select a result to check readiness.`
          : "No matching place was found. Try the district name and state.",
      );
    } catch (error) {
      setLocalMessage(error.message || "Place search failed.");
    } finally {
      setSearchingPlaces(false);
    }
  }

  async function selectPlace(place) {
    setPlaceQuery(place.display_name || place.name);
    setPlaceResults([]);
    setActivePlaceIndex(-1);
    setSelectedPlace(place);
    setLocalReadiness(null);
    setNearestShelters(null);
    setLocalMessage(`Loading nearest hazard zone for ${place.name || place.display_name}…`);
    await checkCoordinates(place.latitude, place.longitude);
  }

  async function checkCoordinates(lat, lon) {
    const controller = new AbortController();
    setLocalMessage("Checking backend readiness for this coordinate…");
    try {
      const [localData, shelterData] = await Promise.all([
        getLocalReadiness(lat, lon, controller.signal),
        getNearestShelters(lat, lon, 5, controller.signal),
      ]);
      setLatitude(String(lat));
      setLongitude(String(lon));
      setLocalReadiness(localData);
      setNearestShelters(shelterData);
      setLocalMessage("Coordinate check complete from the backend.");
    } catch (error) {
      setLocalReadiness(null);
      setNearestShelters(null);
      setLocalMessage(error.message || "Could not check local readiness.");
    }
  }

  function useDeviceCoordinates() {
    if (!navigator.geolocation) {
      setLocalMessage("This browser does not provide geolocation.");
      return;
    }
    setLocalMessage("Requesting device coordinates…");
    navigator.geolocation.getCurrentPosition(
      (position) => checkCoordinates(position.coords.latitude, position.coords.longitude),
      () => setLocalMessage("Could not get your coordinates. Check browser permission and try again."),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );
  }

  function submitCoordinates(event) {
    event.preventDefault();
    const lat = Number(latitude);
    const lon = Number(longitude);
    if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lon) || lon < -180 || lon > 180) {
      setLocalMessage("Enter a latitude from -90 to 90 and longitude from -180 to 180.");
      return;
    }
    checkCoordinates(lat, lon);
  }

  const telemetryAvailable = Boolean(status?.telemetry?.available);
  const sheltersAvailable = Boolean(status?.shelters?.available);
  const alertsAvailable = Boolean(status?.alerts?.available);
  const translationAvailable = Boolean(status?.translation?.available);
  const routingAvailable = Boolean(status?.routing?.available);
  const allReady = telemetryAvailable && sheltersAvailable && alertsAvailable && routingAvailable;

  return (
    <>
      <section className="data-summary">
        <div className="data-summary-copy">
          <span className="section-kicker">ALL-HAZARD DATA READINESS</span>
          <h2>Regional services and verified information</h2>
          <p>Backend status and coordinate checks determine whether live or verified local information is available.</p>
        </div>
        <div className={`readiness-badge ${allReady ? "ready" : ""}`}>
          <span /> {statusError ? "BACKEND UNAVAILABLE" : status ? (allReady ? "CORE SERVICES READY" : "PARTIALLY AVAILABLE") : "CHECKING SERVICES"}
        </div>
      </section>

      <div className="data-stat-grid">
        <div className="data-stat">
          <span className="stat-label">LIVE HAZARD FEEDS</span>
          <strong className={telemetryAvailable ? "" : "stat-pending"}>{telemetryAvailable ? "Available" : status ? "Unavailable" : "Checking"}</strong>
          <small>{status?.telemetry?.last_error || (telemetryAvailable ? `${status.telemetry.sentinel_count} sentinels responding` : "Open-provider feed not initialized")}</small>
        </div>
        <div className="data-stat">
          <span className="stat-label">VERIFIED SHELTERS</span>
          <strong className={sheltersAvailable ? "" : "stat-pending"}>{sheltersAvailable ? `${status.shelters.verified_count} verified` : "Unavailable"}</strong>
          <small>{sheltersAvailable ? "Published PostGIS shelter records" : "No verified shelter records are available"}</small>
        </div>
        <div className="data-stat"><span className="stat-label">EMERGENCY CONTACT</span><strong>112</strong><small>India emergency response number</small></div>
      </div>

      <section className="panel data-table-panel">
        <div className="panel-heading">
          <div><span className="section-kicker">SERVICE AVAILABILITY</span><h2>Information shown on this dashboard</h2></div>
          <button className="button button-secondary" type="button" onClick={refreshForecasts} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh live feeds"}</button>
        </div>
        {statusError && <p className="location-status">{statusError}</p>}
        <div className="source-list">
          <SourceRow status={telemetryAvailable ? "available" : "pending"} title="Live forecasts and official alerts" detail={telemetryAvailable ? `${status.telemetry.sentinel_count} configured sentinels have returned provider data.` : "Open providers have not returned an initialized live snapshot."} />
          <SourceRow status={sheltersAvailable && routingAvailable ? "available" : "pending"} title="Local shelter locations and safe routes" detail={sheltersAvailable ? `${status.shelters.verified_count} verified shelter records plus routing are connected.` : "Local shelter routing is connected; no verified shelter feed is published."} />
          <SourceRow status={alertsAvailable && translationAvailable ? "available" : "pending"} title="Regional-language alert delivery" detail={status?.translation?.bhashini ? "Bhashini configuration is active; mock delivery is available." : "Mock delivery is active with Google/local fallback; uncached text may remain in English."} />
          <SourceRow status="available" title="Safety guidance" detail="General hazard-specific information is available in the safety guides." />
          <SourceRow status="available" title="Emergency contact" detail="India emergency response number: 112." />
        </div>
      </section>

      <section className="panel location-readiness-panel">
        <div className="panel-heading"><div><span className="section-kicker">PER-AREA CHECK</span><h2>Check a local area</h2></div></div>
        <p className="data-area-copy">Search by district or place name, enter coordinates, or explicitly share your device location. The backend will return the nearest hazard zone and shelter readiness.</p>
        <form className="place-search-form" onSubmit={submitPlaceSearch}>
          <label htmlFor="place-search">Search district or place in India</label>
          <div className="place-search-row">
            <input
              id="place-search"
              type="search"
              value={placeQuery}
              onChange={(event) => {
                setPlaceQuery(event.target.value);
                setSelectedPlace(null);
                setPlaceResults([]);
                setActivePlaceIndex(-1);
              }}
              onKeyDown={handlePlaceInputKeyDown}
              placeholder="Search by district, city, or landmark…"
              autoComplete="off"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded={placeResults.length > 0}
              aria-controls="place-search-results"
              aria-activedescendant={activePlaceIndex >= 0 ? `place-result-${activePlaceIndex}` : undefined}
            />
            <button className="button button-primary" type="submit" disabled={searchingPlaces}>
              {searchingPlaces ? "Searching…" : "Search map"}
            </button>

            {placeResults.length > 0 && (
              <div
                id="place-search-results"
                className="place-search-results"
                role="listbox"
                aria-label="Place search suggestions"
              >
                {placeResults.map((place, index) => (
                  <button
                    type="button"
                    role="option"
                    id={`place-result-${index}`}
                    aria-selected={activePlaceIndex === index}
                    key={`${place.place_id || place.display_name}-${place.latitude}-${place.longitude}`}
                    className={`${activePlaceIndex === index ? "active " : ""}${selectedPlace?.latitude === place.latitude && selectedPlace?.longitude === place.longitude ? "selected" : ""}`}
                    onMouseEnter={() => setActivePlaceIndex(index)}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectPlace(place)}
                  >
                    <span><strong>{place.name}</strong><small>{place.display_name}</small></span>
                    <span className="place-result-coordinates">{place.latitude.toFixed(4)}, {place.longitude.toFixed(4)}</span>
                  </button>
                ))}
                {placeMessage && <small className="place-provider place-suggestion-message">{placeMessage}</small>}
                {placeProvider && <small className="place-provider">Provider: {placeProvider === "google-maps-geocoding" ? "Google Maps Geocoding" : placeProvider === "aapdasetu-sentinel-fallback" ? "AapdaSetu similar-area fallback" : "OpenStreetMap fallback"}{hasLocalSuggestions ? " + AapdaSetu similar areas" : ""}</small>}
              </div>
            )}
          </div>
        </form>

        <form className="coordinate-form" onSubmit={submitCoordinates}>
          <label>Latitude<input type="number" step="0.000001" min="-90" max="90" value={latitude} onChange={(event) => setLatitude(event.target.value)} placeholder="28.6139" /></label>
          <label>Longitude<input type="number" step="0.000001" min="-180" max="180" value={longitude} onChange={(event) => setLongitude(event.target.value)} placeholder="77.2090" /></label>
          <button className="button button-primary" type="submit">Check area</button>
          <button className="button button-secondary" type="button" onClick={useDeviceCoordinates}>Use device location</button>
        </form>
        {localMessage && <p className="location-status">{localMessage}</p>}

        {selectedPlace && localReadiness && (
          <div className="selected-location-card" role="status">
            <span className="selected-location-icon">⌖</span>
            <div>
              <strong>{selectedPlace.name || selectedPlace.display_name}</strong>
              <small>{selectedPlace.display_name}</small>
            </div>
            <span className="selected-location-coordinates">{selectedPlace.latitude.toFixed(5)}, {selectedPlace.longitude.toFixed(5)}</span>
          </div>
        )}

        {localReadiness && (
          <div className="local-readiness-grid">
            <div><strong>Nearest hazard zone</strong>{localReadiness.nearest_hazard_zone ? <small>{localReadiness.nearest_hazard_zone.region} · {localReadiness.nearest_hazard_zone.level?.toUpperCase()} · score {localReadiness.nearest_hazard_zone.score}{typeof localReadiness.nearest_hazard_zone.distance_km === "number" ? ` · ${localReadiness.nearest_hazard_zone.distance_km} km away` : ""}</small> : <small>No live sentinel result is initialized for this area.</small>}</div>
            <div><strong>Verified shelters</strong><small>{localReadiness.verified_shelters.length ? `${localReadiness.verified_shelters.length} verified nearby` : "No verified shelter records for this coordinate check"}</small></div>
            <div><strong>Local routing</strong><small>{localReadiness.route_available ? "Local route endpoint available" : "Routing unavailable"}</small></div>
          </div>
        )}

        {nearestShelters && nearestShelters.shelters?.length > 0 && (
          <div className="nearby-shelters">
            <strong>{nearestShelters.verified ? "Nearby verified shelters" : "Nearby unverified shelter entries"}</strong>
            <ul>{nearestShelters.shelters.map((shelter) => <li key={shelter.id || shelter.name}>{shelter.name} · {shelter.distance_km} km · {shelter.verification_status || "unverified"}</li>)}</ul>
          </div>
        )}
      </section>

      {forecasts && <section className="panel forecast-summary"><strong>Latest provider refresh</strong><small>{forecasts.available ? `${forecasts.forecasts.length} provider risk indicators returned` : forecasts.reason}</small></section>}
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
