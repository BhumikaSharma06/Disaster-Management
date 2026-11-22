import { useState } from "react";

import { updateCurrentUserProfile } from "../api/auth.js";

export default function ProfileSettings({ currentUser, onProfileUpdated }) {
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function saveProfile(event) {
    event.preventDefault();
    setWorking(true);
    setMessage("");
    setError("");
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    try {
      const updatedUser = await updateCurrentUserProfile({
        contact_phone: values.contact_phone || null,
        home_state: values.home_state || null,
        home_district: values.home_district || null,
        home_locality: values.home_locality || null,
        home_landmark: values.home_landmark || null,
      });
      onProfileUpdated(updatedUser);
      setMessage("Profile details saved. They will be used to prefill help and supply forms.");
    } catch (requestError) {
      setError(requestError.message || "Could not save your profile details.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="panel auth-panel profile-panel">
      <div className="auth-intro">
        <span className="section-kicker">ACCOUNT PROFILE</span>
        <h2>Contact details and saved address</h2>
        <p>Your name comes from your account. Add a phone number and usual address to reduce typing in help forms.</p>
      </div>
      <dl className="profile-identity">
        <div><dt>Name</dt><dd>{currentUser.full_name}</dd></div>
        <div><dt>Email</dt><dd>{currentUser.email}</dd></div>
      </dl>
      <form className="auth-form" onSubmit={saveProfile}>
        <label>
          Contact phone
          <input
            name="contact_phone"
            type="tel"
            maxLength="40"
            autoComplete="tel"
            defaultValue={currentUser.contact_phone || ""}
          />
        </label>
        <div className="auth-field-row">
          <label>
            State
            <input name="home_state" maxLength="120" autoComplete="address-level1" defaultValue={currentUser.home_state || ""} />
          </label>
          <label>
            District
            <input name="home_district" maxLength="120" defaultValue={currentUser.home_district || ""} />
          </label>
        </div>
        <div className="auth-field-row">
          <label>
            Village / ward / locality
            <input name="home_locality" maxLength="200" autoComplete="address-level2" defaultValue={currentUser.home_locality || ""} />
          </label>
          <label>
            Nearby landmark
            <input name="home_landmark" maxLength="200" defaultValue={currentUser.home_landmark || ""} />
          </label>
        </div>
        <p className="profile-privacy-note">
          This saved address is only a form convenience. It does not share or verify your current location. Help requests still require you to select the incident location.
        </p>
        <button className="button button-primary auth-submit" type="submit" disabled={working}>
          {working ? "Saving…" : "Save profile"}
        </button>
      </form>
      {error && <div className="auth-message auth-message-error" role="alert">{error}</div>}
      {message && <div className="auth-message auth-message-success" role="status">{message}</div>}
    </section>
  );
}
