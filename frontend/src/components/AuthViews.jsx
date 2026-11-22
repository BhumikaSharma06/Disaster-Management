import { useEffect, useState } from "react";

import {
  decideResponderRequest,
  deleteAdminUser,
  getAdminUsers,
  getResponderRequests,
  restoreAdminUser,
  updateAdminRole,
  loginAccount,
  registerAccount,
  resendVerification,
  verifyEmail,
} from "../api/auth.js";
import { archiveSafetyTip, createSafetyTip, getAdminSafetyTips, updateSafetyTip } from "../api/safety.js";
import { getIncidents, getIncidentOperations } from "../api/eoc.js";
import {
  getAdminAuditLogs,
  getSuperAdminSimulations,
  startSuperAdminSimulation,
  stopSuperAdminSimulation,
} from "../api/superAdmin.js";
import { HAZARDS } from "../data/hazards.js";

export function AuthView({ onAuthenticated, verificationToken, initialMode = "login" }) {
  const [mode, setMode] = useState(initialMode);
  const [responder, setResponder] = useState(false);
  const [email, setEmail] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [canResend, setCanResend] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (!verificationToken) return;
    setWorking(true);
    verifyEmail(verificationToken)
      .then((result) => {
        setMode("login");
        setMessage(result.message);
        setError("");
      })
      .catch((requestError) => {
        setMode("login");
        setError(requestError.message);
      })
      .finally(() => setWorking(false));
  }, [verificationToken]);

  async function handleSubmit(event) {
    event.preventDefault();
    setWorking(true);
    setError("");
    setMessage("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (mode === "register") {
        const result = await registerAccount({
          full_name: values.full_name,
          email: values.email,
          password: values.password,
          is_responder: responder,
          responder_unit: responder ? values.responder_unit || null : null,
          responder_phone: responder ? values.responder_phone || null : null,
        });
        setEmail(values.email.trim().toLowerCase());
        setCanResend(true);
        setMessage("Account created. Check your inbox and use the confirmation link to verify your email before signing in.");
      } else {
        const user = await loginAccount({ identifier: values.identifier, password: values.password });
        onAuthenticated(user);
      }
    } catch (requestError) {
      setError(requestError.message);
      if (requestError.code === "email_not_verified") {
        const enteredIdentifier = values.identifier.trim().toLowerCase();
        if (enteredIdentifier.includes("@")) {
          setEmail(enteredIdentifier);
          setCanResend(true);
        }
      }
    } finally {
      setWorking(false);
    }
  }

  async function handleResend() {
    setWorking(true);
    setError("");
    try {
      await resendVerification(email);
      setMessage("Verification email requested. Check your inbox for the confirmation link.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="auth-layout">
      <div className="panel auth-panel">
        <div className="auth-tabs" role="tablist" aria-label="Account action">
          <button
            type="button"
            className={mode === "login" ? "auth-tab auth-tab-active" : "auth-tab"}
            onClick={() => { setMode("login"); setError(""); setMessage(""); setShowPassword(false); }}
          >
            Sign in
          </button>
          <button
            type="button"
            className={mode === "register" ? "auth-tab auth-tab-active" : "auth-tab"}
            onClick={() => { setMode("register"); setError(""); setMessage(""); setShowPassword(false); }}
          >
            Create account
          </button>
        </div>
        <div className="auth-intro">
          <span className="section-kicker">AAPDASETU ACCOUNT</span>
          <h2>{mode === "register" ? "Join the community" : "Welcome back"}</h2>
          <p>
            {mode === "register"
              ? "Create an account to participate in readiness and coordination features. Verify your email before signing in."
              : "Sign in to access your account and available role-based features."}
          </p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "register" && (
            <label>
              Full name
              <input name="full_name" required minLength="1" maxLength="160" autoComplete="name" />
            </label>
          )}
          <label>
            {mode === "register" ? "Email address" : "Email address or username"}
            <input
              name={mode === "register" ? "email" : "identifier"}
              type={mode === "register" ? "email" : "text"}
              required
              maxLength="254"
              autoComplete={mode === "register" ? "email" : "username"}
              value={mode === "register" ? email : identifier}
              onChange={(event) => mode === "register"
                ? setEmail(event.target.value)
                : setIdentifier(event.target.value)}
              placeholder={mode === "login" ? "Enter your email address or username" : undefined}
            />
          </label>
          <label>
            Password
            <div className="auth-password-field">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                required
                minLength={mode === "register" ? 8 : 1}
                maxLength="128"
                autoComplete={mode === "register" ? "new-password" : "current-password"}
              />
              <button
                className="auth-password-toggle"
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            {mode === "register" && <small>Use at least 8 characters.</small>}
          </label>
          {mode === "register" && (
            <>
              <label className="auth-check">
                <input
                  type="checkbox"
                  checked={responder}
                  onChange={(event) => setResponder(event.target.checked)}
                />
                <span>Request responder access <span className="optional-label">Approval required</span></span>
              </label>
              {responder && (
                <div className="auth-field-row">
                  <label>
                    Responder unit <span className="optional-label">Optional</span>
                    <input name="responder_unit" maxLength="160" placeholder="Team or organization" />
                  </label>
                  <label>
                    Responder phone <span className="optional-label">Optional</span>
                    <input name="responder_phone" type="tel" maxLength="40" autoComplete="tel" />
                  </label>
                </div>
              )}
            </>
          )}
          <button className="button button-primary auth-submit" type="submit" disabled={working}>
            {working ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>
        {error && <div className="auth-message auth-message-error" role="alert">{error}</div>}
        {message && <div className="auth-message auth-message-success" role="status">{message}</div>}
        {mode === "register" && responder && (
          <p className="auth-role-note">
            Your community account remains active while the responder request is reviewed. Responder access begins after approval and email verification.
          </p>
        )}
      </div>
      <aside className="panel auth-side-note">
        <span className="auth-side-icon">✉</span>
        <span className="section-kicker">EMAIL VERIFICATION</span>
        <h2>Verify before signing in</h2>
        <p>New accounts must verify their email address using the confirmation link sent to their inbox before signing in.</p>
        {canResend && email ? (
          <>
            <button className="text-button auth-resend" type="button" onClick={handleResend} disabled={working}>
              Resend verification email
            </button>
            <p><small>After verification, return to Sign in and try again. The sign-in status will confirm when access is ready.</small></p>
          </>
        ) : (
          <p><small>Didn’t receive the email? Use the resend action after creating or attempting to sign in to an unverified account.</small></p>
        )}
      </aside>
    </section>
  );
}

export function AdminUsers({ currentUser }) {
  const emptyTip = { title: "", content: "", hazard_type: "flood", phase: "before", language: "en", region: "", status: "draft", source: "" };
  const [activeTab, setActiveTab] = useState("overview");
  const [users, setUsers] = useState([]);
  const [responderRequests, setResponderRequests] = useState([]);
  const [tips, setTips] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [operations, setOperations] = useState(null);
  const [simulations, setSimulations] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState("");
  const [tipForm, setTipForm] = useState(emptyTip);
  const [simulationForm, setSimulationForm] = useState({
    name: "",
    hazard_type: "flood",
    area_name: "",
    severity: "moderate",
    scenario_notes: "",
  });
  const [editingTipId, setEditingTipId] = useState(null);
  const [accountQuery, setAccountQuery] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const superAdminRequests = currentUser?.is_super_admin
      ? [getSuperAdminSimulations(controller.signal), getAdminAuditLogs(controller.signal)]
      : [Promise.resolve([]), Promise.resolve([])];
    Promise.all([
      getAdminUsers(controller.signal),
      getResponderRequests(controller.signal),
      getAdminSafetyTips(controller.signal),
      getIncidents(controller.signal),
      ...superAdminRequests,
    ])
      .then(([allUsers, pendingRequests, adminTips, incidentRecords, simulationRecords, auditRecords]) => {
        setUsers(allUsers);
        setResponderRequests(pendingRequests);
        setTips(adminTips);
        setIncidents(incidentRecords);
        setSimulations(simulationRecords);
        setAuditLogs(auditRecords);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [currentUser?.is_super_admin]);

  async function refreshAuditLogs() {
    if (!currentUser?.is_super_admin) return;
    try {
      setAuditLogs(await getAdminAuditLogs());
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function decideRequest(userId, decision) {
    setUpdatingId(userId);
    setError("");
    try {
      const updatedUser = await decideResponderRequest(userId, decision);
      setResponderRequests((pending) => pending.filter((user) => user.id !== userId));
      setUsers((all) => all.map((user) => user.id === userId ? updatedUser : user));
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function removeAccount(user) {
    if (!window.confirm(`Soft-delete ${user.full_name}? This prevents future sign-in while retaining evidence.`)) return;
    setUpdatingId(user.id);
    setError("");
    try {
      const updated = await deleteAdminUser(user.id);
      setUsers((all) => all.map((item) => item.id === user.id ? updated : item));
      setSuccess(`${user.full_name} was soft-deleted. All active sessions were invalidated.`);
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function changeRole(user, decision) {
    const action = decision === "promote" ? "Promote" : "Demote";
    if (!window.confirm(`${action} ${user.full_name} ${decision === "promote" ? "to Administrator" : "from Administrator"}?`)) return;
    setUpdatingId(user.id);
    setError("");
    try {
      const updated = await updateAdminRole(user.id, decision);
      setUsers((all) => all.map((item) => item.id === user.id ? updated : item));
      setSuccess(`${user.full_name} ${decision === "promote" ? "promoted to Administrator" : "demoted to Community user"}.`);
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function restoreAccount(user) {
    setUpdatingId(user.id);
    setError("");
    try {
      const updated = await restoreAdminUser(user.id);
      setUsers((all) => all.map((item) => item.id === user.id ? updated : item));
      setSuccess(`${user.full_name} was restored.`);
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function saveTip(event) {
    event.preventDefault();
    setUpdatingId(editingTipId || "tip");
    setError("");
    try {
      const payload = { ...tipForm, region: tipForm.region || null, source: tipForm.source || null };
      const saved = editingTipId ? await updateSafetyTip(editingTipId, payload) : await createSafetyTip(payload);
      setTips((all) => editingTipId ? all.map((tip) => tip.id === saved.id ? saved : tip) : [saved, ...all]);
      setTipForm(emptyTip);
      setEditingTipId(null);
      setSuccess(editingTipId ? "Safety tip updated." : "Safety tip created.");
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  function editTip(tip) {
    setEditingTipId(tip.id);
    const matchingHazard = HAZARDS.find((hazard) =>
      hazard.id === tip.hazard_type || hazard.title.toLowerCase() === tip.hazard_type.toLowerCase()
    );
    setTipForm({ title: tip.title, content: tip.content, hazard_type: matchingHazard?.id || tip.hazard_type, phase: tip.phase, language: tip.language, region: tip.region || "", status: tip.status, source: tip.source || "" });
  }

  async function archiveTip(tip) {
    if (!window.confirm(`Archive “${tip.title}”?`)) return;
    setUpdatingId(String(tip.id));
    setError("");
    try {
      await archiveSafetyTip(tip.id);
      setTips((all) => all.map((item) => item.id === tip.id ? { ...item, status: "archived" } : item));
      setSuccess(`${tip.title} was archived.`);
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function loadOperations(incidentId) {
    setSelectedIncident(incidentId);
    setOperations(null);
    if (!incidentId) return;
    setError("");
    try {
      setOperations(await getIncidentOperations(incidentId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function startSimulation(event) {
    event.preventDefault();
    setUpdatingId("simulation");
    setError("");
    try {
      const simulation = await startSuperAdminSimulation({
        ...simulationForm,
        scenario_notes: simulationForm.scenario_notes || null,
      });
      setSimulations((all) => [simulation, ...all]);
      setSimulationForm({
        name: "",
        hazard_type: "flood",
        area_name: "",
        severity: "moderate",
        scenario_notes: "",
      });
      setSuccess("Simulation started. It is isolated from live incidents and public alerts.");
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function stopSimulation(simulation) {
    if (!window.confirm(`Stop the simulation “${simulation.name}”?`)) return;
    setUpdatingId(`simulation-${simulation.id}`);
    setError("");
    try {
      const stopped = await stopSuperAdminSimulation(simulation.id);
      setSimulations((all) => all.map((item) => item.id === stopped.id ? stopped : item));
      setSuccess(`Simulation “${simulation.name}” stopped.`);
      await refreshAuditLogs();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUpdatingId("");
    }
  }

  const filteredUsers = users.filter((user) => {
    const query = accountQuery.trim().toLowerCase();
    return !query || [user.full_name, user.username, user.email].some((value) => (value || "").toLowerCase().includes(query));
  });

  const tabs = [
    ["overview", "Overview"],
    ["accounts", "Accounts"],
    ["tips", "Safety tips"],
    ["moderation", "Incidents & SOS"],
    ...(currentUser?.is_super_admin ? [["super-admin", "Super Admin"]] : []),
  ];

  return (
    <div className="admin-dashboard">
      <div className="admin-summary-grid">
        <article className="admin-summary-card"><span>Accounts</span><strong>{users.filter((user) => !user.deleted_at).length}</strong></article>
        <article className="admin-summary-card"><span>Responder requests</span><strong>{responderRequests.length}</strong></article>
        <article className="admin-summary-card"><span>Safety tips</span><strong>{tips.filter((tip) => tip.status === "published").length}</strong></article>
        <article className="admin-summary-card"><span>Active incidents</span><strong>{incidents.length}</strong></article>
      </div>

      <nav className="admin-tabs" aria-label="Administrator sections">
        {tabs.map(([id, label]) => (
          <button key={id} type="button" className={activeTab === id ? "admin-tab-active" : ""} onClick={() => setActiveTab(id)}>{label}</button>
        ))}
      </nav>

      {activeTab === "overview" && (
        <div className="admin-overview-grid">
          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">ACTION QUEUE</span><h2>Responder approval requests</h2></div><span>{responderRequests.length} awaiting</span></div>
            {loading ? <p className="admin-state">Loading…</p> : responderRequests.length === 0 ? <p className="admin-state">No pending responder requests.</p> : (
              responderRequests.slice(0, 5).map((user) => (
                <div className="admin-action-row" key={user.id}>
                  <div><strong>{user.full_name}</strong><small>{user.responder_unit || user.email}</small></div>
                  <div className="admin-decision-actions">
                    <button type="button" className="admin-approve" disabled={updatingId === user.id || !user.is_email_verified} onClick={() => decideRequest(user.id, "approve")}>Approve</button>
                    <button type="button" className="admin-reject" disabled={updatingId === user.id} onClick={() => decideRequest(user.id, "reject")}>Reject</button>
                  </div>
                </div>
              ))
            )}
          </section>
          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">CONTENT STATUS</span><h2>Safety tips</h2></div><span>{tips.length} total</span></div>
            {tips.slice(0, 5).map((tip) => <div className="admin-action-row" key={tip.id}><div><strong>{tip.title}</strong><small>{tip.hazard_type} · {tip.phase}</small></div><span className={`status-pill status-${tip.status}`}>{tip.status}</span></div>)}
            {tips.length === 0 && <p className="admin-state">No safety tips have been created.</p>}
          </section>
        </div>
      )}

      {activeTab === "accounts" && (
        <section className="panel admin-users-panel">
          <div className="admin-users-heading"><div><span className="section-kicker">ADMIN ONLY</span><h2>Account directory</h2></div><span>{users.length} accounts</span></div>
          <input className="admin-search" value={accountQuery} onChange={(event) => setAccountQuery(event.target.value)} placeholder="Search name, username or email" aria-label="Search accounts" />
          <div className="admin-table-wrap">
            <table className="admin-users-table">
              <thead><tr><th>Name</th><th>Username</th><th>Email</th><th>Role</th><th>Verification</th><th>State</th><th>Action</th></tr></thead>
              <tbody>{filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>{user.full_name}</td><td>{user.username || "—"}</td><td>{user.email}</td>
                  <td>{user.is_super_admin ? "Super Admin" : user.is_admin ? "Admin" : user.is_responder ? "Responder" : "Community"}</td>
                  <td>{user.is_email_verified ? "Verified" : "Pending"}</td>
                  <td>{user.deleted_at ? "Deleted" : "Active"}</td>
                  <td>
                    <div className="admin-account-actions">
                      {user.deleted_at ? (
                        <button type="button" className="admin-approve" disabled={updatingId === user.id} onClick={() => restoreAccount(user)}>Restore</button>
                      ) : (
                        !user.is_admin && <button type="button" className="admin-reject" disabled={updatingId === user.id} onClick={() => removeAccount(user)}>Delete</button>
                      )}
                      {currentUser?.is_super_admin && !user.deleted_at && user.id !== currentUser.id && (
                        user.is_admin ? (
                          !user.is_super_admin && <button type="button" className="admin-role-demote" disabled={updatingId === user.id} onClick={() => changeRole(user, "demote")}>Demote</button>
                        ) : (
                          <button type="button" className="admin-role-promote" disabled={updatingId === user.id} onClick={() => changeRole(user, "promote")}>Promote Admin</button>
                        )
                      )}
                    </div>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "tips" && (
        <div className="admin-overview-grid">
          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">{editingTipId ? "EDIT TIP" : "NEW TIP"}</span><h2>{editingTipId ? "Update safety tip" : "Create safety tip"}</h2></div></div>
            <form className="admin-tip-form" onSubmit={saveTip}>
              <input value={tipForm.title} onChange={(event) => setTipForm({ ...tipForm, title: event.target.value })} minLength="3" maxLength="160" required placeholder="Title" />
              <textarea value={tipForm.content} onChange={(event) => setTipForm({ ...tipForm, content: event.target.value })} minLength="10" maxLength="5000" required placeholder="Safety instruction" />
              <div className="admin-field-row">
                <select value={tipForm.hazard_type} onChange={(event) => setTipForm({ ...tipForm, hazard_type: event.target.value })}>
                  {HAZARDS.map((hazard) => <option value={hazard.id} key={hazard.id}>{hazard.title}</option>)}
                  <option value="all-hazards">All hazards</option>
                </select>
                <select value={tipForm.phase} onChange={(event) => setTipForm({ ...tipForm, phase: event.target.value })}><option value="before">Before</option><option value="during">During</option><option value="after">After</option></select>
                <select value={tipForm.status} onChange={(event) => setTipForm({ ...tipForm, status: event.target.value })}><option value="draft">Draft</option><option value="published">Published</option><option value="archived">Archived</option></select>
              </div>
              <div className="admin-field-row"><input value={tipForm.region} onChange={(event) => setTipForm({ ...tipForm, region: event.target.value })} placeholder="Region (optional)" /><input value={tipForm.source} onChange={(event) => setTipForm({ ...tipForm, source: event.target.value })} placeholder="Source (optional)" /></div>
              <div className="form-actions"><button type="submit" className="button button-primary" disabled={updatingId === "tip" || updatingId === String(editingTipId)}>{editingTipId ? "Save changes" : "Create tip"}</button>{editingTipId && <button type="button" className="button button-outline" onClick={() => { setEditingTipId(null); setTipForm(emptyTip); }}>Cancel</button>}</div>
            </form>
          </section>
          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">LIBRARY</span><h2>Safety-tip records</h2></div><span>{tips.length} records</span></div>
            <div className="admin-tip-list">{tips.map((tip) => <article key={tip.id} className="admin-tip-card"><div><strong>{tip.title}</strong><small>{tip.hazard_type} · {tip.phase} · {tip.language}</small><p>{tip.content}</p></div><div className="admin-tip-actions"><span className={`status-pill status-${tip.status}`}>{tip.status}</span><button type="button" className="admin-approve" onClick={() => editTip(tip)}>Edit</button>{tip.status !== "archived" && <button type="button" className="admin-reject" disabled={updatingId === String(tip.id)} onClick={() => archiveTip(tip)}>Archive</button>}</div></article>)}</div>
          </section>
        </div>
      )}

      {activeTab === "moderation" && (
        <div className="admin-overview-grid">
          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">ACTIVE REGISTER</span><h2>Incident records</h2></div><span>{incidents.length} incidents</span></div>
            <div className="admin-incident-list">{incidents.map((incident) => <button type="button" key={incident.id} className={selectedIncident === String(incident.id) ? "admin-incident-active" : ""} onClick={() => loadOperations(String(incident.id))}><strong>{incident.title}</strong><small>{incident.hazard_type} · {incident.area_name} · {incident.status}</small></button>)}</div>
            {incidents.length === 0 && <p className="admin-state">No active incidents.</p>}
          </section>
          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">SOS / SHELTERS</span><h2>Incident operations</h2></div></div>
            {!operations ? <p className="admin-state">Select an incident to review linked SOS records.</p> : (
              <div className="admin-operation-list">
                {(operations.sos_records || []).map((record) => <article key={record.id}><strong>{record.need_type} · {record.urgency}</strong><p>{record.description || "No description supplied."}</p><small>Status: {record.status}</small></article>)}
                {(operations.sos_records || []).length === 0 && <p className="admin-state">No SOS records are linked to this incident.</p>}
              </div>
            )}
          </section>
        </div>
      )}

      {activeTab === "super-admin" && currentUser?.is_super_admin && (
        <div className="admin-dashboard">
          <section className="panel admin-users-panel">
            <div className="simulation-warning" role="note">
              <strong>SIMULATION ONLY</strong>
              <span>Scenarios are isolated metadata for testing. They do not create live incidents, public alerts, SOS requests, or emergency-service dispatches.</span>
            </div>
            <div className="admin-users-heading">
              <div><span className="section-kicker">SUPER ADMIN ONLY</span><h2>Disaster simulation control</h2></div>
              <span>{simulations.filter((simulation) => simulation.status === "running").length ? "One simulation active" : "No active simulation"}</span>
            </div>
            <form className="admin-tip-form" onSubmit={startSimulation}>
              <div className="admin-field-row">
                <input
                  aria-label="Simulation name"
                  value={simulationForm.name}
                  onChange={(event) => setSimulationForm({ ...simulationForm, name: event.target.value })}
                  minLength="3"
                  maxLength="160"
                  required
                  placeholder="Scenario name"
                />
                <input
                  aria-label="Simulation area"
                  value={simulationForm.area_name}
                  onChange={(event) => setSimulationForm({ ...simulationForm, area_name: event.target.value })}
                  minLength="2"
                  maxLength="200"
                  required
                  placeholder="Area label"
                />
              </div>
              <div className="admin-field-row simulation-config-row">
                <select
                  aria-label="Simulation hazard"
                  value={simulationForm.hazard_type}
                  onChange={(event) => setSimulationForm({ ...simulationForm, hazard_type: event.target.value })}
                >
                  {HAZARDS.map((hazard) => <option value={hazard.id} key={hazard.id}>{hazard.title}</option>)}
                </select>
                <select
                  aria-label="Simulation severity"
                  value={simulationForm.severity}
                  onChange={(event) => setSimulationForm({ ...simulationForm, severity: event.target.value })}
                >
                  <option value="low">Low</option>
                  <option value="moderate">Moderate</option>
                  <option value="high">High</option>
                  <option value="extreme">Extreme</option>
                </select>
              </div>
              <textarea
                aria-label="Simulation notes"
                value={simulationForm.scenario_notes}
                onChange={(event) => setSimulationForm({ ...simulationForm, scenario_notes: event.target.value })}
                maxLength="4000"
                placeholder="Scenario notes (optional)"
              />
              <div className="form-actions">
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={updatingId === "simulation" || simulations.some((simulation) => simulation.status === "running")}
                >
                  {updatingId === "simulation" ? "Starting…" : "Start simulation"}
                </button>
                {simulations.some((simulation) => simulation.status === "running") && <small>Stop the active simulation before starting another.</small>}
              </div>
            </form>
          </section>

          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">ISOLATED SCENARIOS</span><h2>Simulation history</h2></div><span>{simulations.length} records</span></div>
            {simulations.length === 0 ? <p className="admin-state">No simulations have been started.</p> : (
              <div className="admin-table-wrap">
                <table className="admin-users-table">
                  <thead><tr><th>Scenario</th><th>Hazard / severity</th><th>Area</th><th>Status</th><th>Started</th><th>Action</th></tr></thead>
                  <tbody>{simulations.map((simulation) => (
                    <tr key={simulation.id}>
                      <td>{simulation.name}{simulation.scenario_notes && <small className="simulation-notes">{simulation.scenario_notes}</small>}</td>
                      <td>{simulation.hazard_type} · {simulation.severity}</td>
                      <td>{simulation.area_name}</td>
                      <td><span className={`status-pill status-${simulation.status}`}>{simulation.status}</span></td>
                      <td>{new Date(simulation.started_at).toLocaleString()}</td>
                      <td>{simulation.status === "running" && (
                        <button
                          type="button"
                          className="admin-reject"
                          disabled={updatingId === `simulation-${simulation.id}`}
                          onClick={() => stopSimulation(simulation)}
                        >
                          {updatingId === `simulation-${simulation.id}` ? "Stopping…" : "Stop"}
                        </button>
                      )}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel admin-users-panel">
            <div className="admin-users-heading"><div><span className="section-kicker">PRIVILEGED ACTIONS</span><h2>Recent audit log</h2></div><span>{auditLogs.length} recent records</span></div>
            {auditLogs.length === 0 ? <p className="admin-state">No audited administrative actions yet.</p> : (
              <div className="admin-table-wrap">
                <table className="admin-users-table">
                  <thead><tr><th>Time</th><th>Administrator</th><th>Action</th><th>Target</th></tr></thead>
                  <tbody>{auditLogs.map((entry) => (
                    <tr key={entry.id}>
                      <td>{new Date(entry.created_at).toLocaleString()}</td>
                      <td>{entry.actor_name}</td>
                      <td>{entry.action.replaceAll("_", " ")}</td>
                      <td>{entry.target_label || `${entry.target_type}${entry.target_id ? ` #${entry.target_id}` : ""}`}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {success && <p className="auth-message auth-message-success" role="status">{success}</p>}
      {error && <p className="auth-message auth-message-error" role="alert">{error}</p>}
    </div>
  );
}
