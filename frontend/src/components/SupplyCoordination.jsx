import { useCallback, useEffect, useState } from "react";

import {
  claimSupplyOffer,
  cancelSupplyOffer,
  cancelHelpRequest,
  createHelpRequest,
  createSupplyOffer,
  getHelpRequests,
  getMyHelpRequests,
  getMySupplyOffers,
  getOpenRequestItems,
  getSupplyOffers,
  updateSupplyOfferStatus,
} from "../api/coordination.js";
import { reverseGeocode } from "../api/geography.js";
import {
  removeQueuedCoordinationSubmission,
  getQueuedCoordinationSubmissions,
  queueCoordinationSubmission,
  updateQueuedCoordinationSubmission,
} from "../offline/coordinationQueue.js";
import {
  geocodeHelpRequestPayload,
  syncCoordinationQueue,
} from "../offline/syncCoordinationQueue.js";

const COPY = {
  en: {
    inbox: "Responder inbox",
    responseNoticeTitle: "Coordinated relief dispatch",
    responseNotice: "Submissions are saved and routed to verified responders. For immediate life-threatening emergencies, call 112.",
    inboxNoticeTitle: "Active responder queue",
    inboxNotice: "Review each request and its donor offer in one place. Update offer stages through delivery.",
    openInbox: "Open responder inbox",
    needTab: "I need help",
    offerTab: "I can help",
    requestTitle: "Tell us what you need",
    requestIntro: "Share a clear description and location so responders can coordinate support.",
    offerTitle: "Offer supplies",
    offerIntro: "Choose an open request, then tell us what you can provide.",
    item: "Need category or item",
    selectItem: "Select an item",
    otherItem: "Describe the item or need",
    urgency: "Urgency",
    urgent: "Urgent — immediate safety concern",
    high: "High — needed today",
    general: "General — when possible",
    quantity: "Quantity required",
    unit: "Unit",
    units: "units",
    people: "people",
    packets: "packets",
    litres: "litres",
    state: "State",
    district: "District",
    locality: "Village / ward",
    landmark: "Nearby landmark (optional)",
    searching: "Searching…",
    resolvingLocation: "Finding your location…",
    useDevice: "Use current location",
    locationChosen: "Location selected",
    locationRequired: "Choose the incident location before submitting. Your saved address is prefilled but does not confirm your current location.",
    locationAddressUnavailable: "The location is selected. Address details could not be retrieved and will be left blank.",
    contactName: "Contact name",
    contactPhone: "Contact phone",
    notes: "Additional notes (optional)",
    notesPlaceholder: "Share only the information needed to coordinate this request.",
    submitRequest: "Submit help request",
    selectRequest: "Open request item",
    noOpenItems: "No open request items are available right now.",
    loadingItems: "Loading open requests…",
    unitsOffered: "Quantity offered",
    donorName: "Your name",
    donorPhone: "Your phone",
    pickup: "Pickup location",
    pickupPlaceholder: "Enter the location where supplies can be collected",
    submitOffer: "Submit supply offer",
    queued: "Saved on this device and will sync when a connection is available.",
    submitted: "Request recorded and routed to the responder queue.",
    activeQueue: "ACTIVE COORDINATION QUEUE",
    queuedCount: "Pending offline submissions",
    needsAttention: "Submission needs your attention",
    saveAndRetry: "Update quantity and retry",
    dismiss: "Dismiss",
    queuedOffer: "Saved supply offer",
    queuedRequest: "Saved help request",
    formError: "Submission could not be completed.",
    pending: "Sync is pending. Your submission remains saved on this device.",
    inboxLoad: "Could not load responder offers.",
    titleInbox: "Coordination queue",
    refresh: "Refresh",
    statusFilter: "Filter by status",
    allStatuses: "All statuses",
    itemFilter: "Filter by item",
    locationFilter: "Filter by location",
    noOffers: "No active help requests or supply offers match these filters.",
    noRequestsInQueue: "No active help requests need responder review.",
    required: "required",
    remaining: "remaining",
    requester: "Requester",
    donor: "Donor",
    need: "Need",
    pickupLabel: "Pickup",
    dropoffLabel: "Delivery location",
    noDonorYet: "No donor offer yet",
    noPickupYet: "Waiting for a donor offer",
    queueTableLabel: "Responder coordination queue",
    queueItem: "Item",
    queueStatus: "Status",
    queueActions: "Actions",
    claim: "Claim offer",
    contacted: "Mark contacted",
    picked_up: "Mark picked up",
    delivered: "Mark delivered",
    pickedUpQuantity: "Actual quantity picked up",
    cancelOffer: "Cancel offer",
    donorCancelled: "Donor cancelled",
    donorUnreachable: "Donor unreachable",
    notesLabel: "Notes",
    assigned: "Assigned responder",
    requestHistory: "My help requests",
    offerHistory: "My supply offers",
    signInForHistory: "Sign in to see and manage requests or offers linked to your account. Guest submissions cannot be managed from account history.",
    noRequestHistory: "You have not submitted any help requests from this account.",
    noOfferHistory: "You have not submitted any supply offers from this account.",
    cancelRequest: "Cancel request",
    cancelDonation: "Cancel offer",
    historyLoad: "Could not load your coordination history.",
    historyActionError: "The cancellation could not be completed.",
    matched: "matched",
    requestStatuses: {
      open: "Open",
      partially_fulfilled: "Partially matched",
      fulfilled: "Supplies matched",
      closed: "Closed by response team",
      cancelled: "Cancelled",
    },
    statuses: {
      pending_responder: "Awaiting responder",
      responder_assigned: "Responder assigned",
      contacted: "Contacted",
      picked_up: "Picked up",
      delivered: "Delivered",
      cancelled: "Cancelled",
    },
  },
  hi: {
    inbox: "रिस्पॉन्डर इनबॉक्स",
    responseNoticeTitle: "राहत वितरण समन्वय",
    responseNotice: "अनुरोध सहेजकर सत्यापित रिस्पॉन्डर तक पहुँचाए जाते हैं। जीवन को तत्काल खतरे में 112 पर कॉल करें।",
    inboxNoticeTitle: "सक्रिय रिस्पॉन्डर कतार",
    inboxNotice: "हर अनुरोध और उसके सहायता प्रस्ताव को एक जगह देखें। प्रस्ताव की स्थिति डिलीवरी तक अपडेट करें।",
    openInbox: "रिस्पॉन्डर इनबॉक्स खोलें",
    needTab: "मुझे मदद चाहिए",
    offerTab: "मैं मदद कर सकता/सकती हूँ",
    requestTitle: "बताएँ कि आपको क्या चाहिए",
    requestIntro: "सहायता के समन्वय के लिए ज़रूरत और स्थान की जानकारी दें।",
    offerTitle: "सामग्री देने का प्रस्ताव",
    offerIntro: "खुली ज़रूरत चुनें और उपलब्ध सहायता बताएँ।",
    item: "ज़रूरत या सामग्री",
    selectItem: "सामग्री चुनें",
    otherItem: "ज़रूरत का वर्णन करें",
    urgency: "प्राथमिकता",
    urgent: "तत्काल — सुरक्षा को अभी खतरा",
    high: "उच्च — आज चाहिए",
    general: "सामान्य — सुविधा अनुसार",
    quantity: "आवश्यक मात्रा",
    unit: "इकाई",
    units: "इकाई",
    people: "लोग",
    packets: "पैकेट",
    litres: "लीटर",
    state: "राज्य",
    district: "ज़िला",
    locality: "गाँव / वार्ड",
    landmark: "नज़दीकी पहचान (वैकल्पिक)",
    searching: "खोज रहे हैं…",
    resolvingLocation: "आपका स्थान खोज रहे हैं…",
    useDevice: "वर्तमान स्थान उपयोग करें",
    locationChosen: "स्थान चुना गया",
    locationRequired: "भेजने से पहले आपदा का स्थान चुनें। पहले से भरा पता आपके वर्तमान स्थान की पुष्टि नहीं करता।",
    locationAddressUnavailable: "स्थान चुन लिया गया है। पते की जानकारी नहीं मिली और इसे खाली छोड़ा जाएगा।",
    contactName: "संपर्क नाम",
    contactPhone: "संपर्क फ़ोन",
    notes: "अतिरिक्त जानकारी (वैकल्पिक)",
    notesPlaceholder: "समन्वय के लिए आवश्यक जानकारी ही साझा करें।",
    submitRequest: "मदद का अनुरोध भेजें",
    selectRequest: "खुली ज़रूरत चुनें",
    noOpenItems: "अभी कोई खुली ज़रूरत उपलब्ध नहीं है।",
    loadingItems: "खुले अनुरोध लोड हो रहे हैं…",
    unitsOffered: "प्रस्तावित मात्रा",
    donorName: "आपका नाम",
    donorPhone: "आपका फ़ोन",
    pickup: "सामग्री लेने का स्थान",
    pickupPlaceholder: "सामग्री लेने का स्थान लिखें",
    submitOffer: "सामग्री प्रस्ताव भेजें",
    queued: "इस डिवाइस पर सुरक्षित है; कनेक्शन मिलने पर सिंक होगा।",
    submitted: "अनुरोध दर्ज करके रिस्पॉन्डर कतार में भेज दिया गया है।",
    activeQueue: "सक्रिय समन्वय कतार",
    queuedCount: "ऑफ़लाइन भेजे जाने वाले अनुरोध",
    needsAttention: "अनुरोध में सुधार आवश्यक है",
    saveAndRetry: "मात्रा बदलकर फिर भेजें",
    dismiss: "हटाएँ",
    queuedOffer: "सहेजा गया सहायता प्रस्ताव",
    queuedRequest: "सहेजा गया मदद अनुरोध",
    formError: "अनुरोध पूरा नहीं हो सका।",
    pending: "सिंक बाकी है। आपका अनुरोध इस डिवाइस पर सुरक्षित है।",
    inboxLoad: "रिस्पॉन्डर प्रस्ताव लोड नहीं हो सके।",
    titleInbox: "समन्वय कतार",
    refresh: "रीफ़्रेश करें",
    statusFilter: "स्थिति से छाँटें",
    allStatuses: "सभी स्थितियाँ",
    itemFilter: "सामग्री से छाँटें",
    locationFilter: "स्थान से छाँटें",
    noOffers: "इन फ़िल्टर से कोई सक्रिय अनुरोध या सहायता प्रस्ताव नहीं मिला।",
    noRequestsInQueue: "समीक्षा के लिए कोई सक्रिय मदद अनुरोध नहीं है।",
    required: "आवश्यक",
    remaining: "बाकी",
    requester: "अनुरोधकर्ता",
    donor: "दाता",
    need: "ज़रूरत",
    pickupLabel: "सामग्री लेने का स्थान",
    dropoffLabel: "पहुँचाने का स्थान",
    noDonorYet: "अभी कोई दाता प्रस्ताव नहीं",
    noPickupYet: "दाता प्रस्ताव की प्रतीक्षा",
    queueTableLabel: "रिस्पॉन्डर समन्वय कतार",
    queueItem: "सामग्री",
    queueStatus: "स्थिति",
    queueActions: "कार्रवाई",
    claim: "प्रस्ताव लें",
    contacted: "संपर्क दर्ज करें",
    picked_up: "सामग्री ली गई",
    delivered: "पहुँचा दिया",
    pickedUpQuantity: "वास्तव में ली गई मात्रा",
    cancelOffer: "प्रस्ताव रद्द करें",
    donorCancelled: "दाता ने रद्द किया",
    donorUnreachable: "दाता से संपर्क नहीं हुआ",
    notesLabel: "जानकारी",
    assigned: "नियुक्त रिस्पॉन्डर",
    requestHistory: "मेरे मदद अनुरोध",
    offerHistory: "मेरे सहायता प्रस्ताव",
    signInForHistory: "अपने खाते से जुड़े अनुरोध और प्रस्ताव देखने या प्रबंधित करने के लिए साइन इन करें। अतिथि अनुरोध खाते की इतिहास सूची से प्रबंधित नहीं किए जा सकते।",
    noRequestHistory: "इस खाते से अभी कोई मदद अनुरोध नहीं भेजा गया है।",
    noOfferHistory: "इस खाते से अभी कोई सहायता प्रस्ताव नहीं भेजा गया है।",
    cancelRequest: "अनुरोध रद्द करें",
    cancelDonation: "प्रस्ताव रद्द करें",
    historyLoad: "आपका समन्वय इतिहास लोड नहीं हो सका।",
    historyActionError: "रद्द करने की कार्रवाई पूरी नहीं हो सकी।",
    matched: "मिलान",
    requestStatuses: {
      open: "खुला",
      partially_fulfilled: "आंशिक रूप से प्रस्ताव मिले",
      fulfilled: "सामग्री के प्रस्ताव मिल गए",
      closed: "रिस्पॉन्स टीम ने बंद किया",
      cancelled: "रद्द",
    },
    statuses: {
      pending_responder: "रिस्पॉन्डर की प्रतीक्षा",
      responder_assigned: "रिस्पॉन्डर नियुक्त",
      contacted: "संपर्क हुआ",
      picked_up: "सामग्री ली गई",
      delivered: "पहुँचा दिया",
      cancelled: "रद्द",
    },
  },
};

const STATUS_OPTIONS = [
  "pending_responder",
  "responder_assigned",
  "contacted",
  "picked_up",
  "delivered",
  "cancelled",
];
const ITEM_OPTIONS = ["Food Packet", "Drinking Water", "Blanket", "Medical Supplies", "General Assistance", "Other"];

function newSubmissionId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    return (character === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
}

export function Response({
  language = "en",
  onOpenInbox,
  submissionCount = 0,
  onCountChanged,
  canOpenInbox = false,
  currentUser,
}) {
  const text = COPY[language] || COPY.en;
  const [responseType, setResponseType] = useState("request");
  const [formMessage, setFormMessage] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [openItems, setOpenItems] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState("");
  const [itemSelection, setItemSelection] = useState("");
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemError, setItemError] = useState("");
  const [selectedCoordinates, setSelectedCoordinates] = useState(null);
  const [placeLoading, setPlaceLoading] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);
  const [attentionSubmissions, setAttentionSubmissions] = useState([]);
  const [queuedEditMessage, setQueuedEditMessage] = useState("");
  const [myRequests, setMyRequests] = useState([]);
  const [myOffers, setMyOffers] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [historyActionId, setHistoryActionId] = useState(null);

  const refreshQueueCount = useCallback(async () => {
    const submissions = await getQueuedCoordinationSubmissions();
    setQueuedCount(submissions.filter((submission) => submission.status !== "needs_attention").length);
    setAttentionSubmissions(submissions.filter((submission) => submission.status === "needs_attention"));
  }, []);

  const loadOpenItems = useCallback(async () => {
    setItemsLoading(true);
    setItemError("");
    try {
      setOpenItems(await getOpenRequestItems({
        latitude: selectedCoordinates?.latitude,
        longitude: selectedCoordinates?.longitude,
      }));
    } catch (error) {
      setItemError(error.message || text.formError);
      setOpenItems([]);
    } finally {
      setItemsLoading(false);
    }
  }, [selectedCoordinates?.latitude, selectedCoordinates?.longitude, text.formError]);

  const loadHistory = useCallback(async () => {
    if (!currentUser) {
      setMyRequests([]);
      setMyOffers([]);
      setHistoryError("");
      return;
    }
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const [requests, offers] = await Promise.all([
        getMyHelpRequests(),
        getMySupplyOffers(),
      ]);
      setMyRequests(requests);
      setMyOffers(offers);
    } catch (error) {
      setHistoryError(error.message || text.historyLoad);
    } finally {
      setHistoryLoading(false);
    }
  }, [currentUser, text.historyLoad]);

  const syncQueued = useCallback(async () => {
    try {
      const result = await syncCoordinationQueue();
      await refreshQueueCount();
      if (result.error) throw result.error;
      await loadOpenItems();
      if (result.synced > 0) onCountChanged?.();
    } catch (error) {
      setFormError(error.message);
    }
  }, [loadOpenItems, onCountChanged, refreshQueueCount]);

  useEffect(() => {
    refreshQueueCount().catch((error) => setFormError(error.message));
    loadOpenItems();
    syncQueued();
    const handleOnline = () => syncQueued();
    window.addEventListener("online", handleOnline);
    const retryInterval = window.setInterval(syncQueued, 30000);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.clearInterval(retryInterval);
    };
  }, [loadOpenItems, refreshQueueCount, syncQueued]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  async function selectLocation(latitude, longitude, label, form) {
    setPlaceLoading(true);
    setFormError("");
    setSelectedCoordinates({ latitude, longitude, label });
    const stateField = form?.elements.namedItem("state");
    const districtField = form?.elements.namedItem("district");
    const localityField = form?.elements.namedItem("locality");
    if (stateField) stateField.value = "";
    if (districtField) districtField.value = "";
    if (localityField) localityField.value = "";
    try {
      const address = await reverseGeocode(latitude, longitude);
      if (!address.available || !address.state || !address.district || !address.locality) {
        throw new Error(address.message || text.locationAddressUnavailable);
      }

      if (!stateField || !districtField || !localityField) {
        throw new Error(text.locationAddressUnavailable);
      }

      stateField.value = address.state;
      districtField.value = address.district;
      localityField.value = address.locality;
    } catch (error) {
      setFormError(error.message || text.locationAddressUnavailable);
    } finally {
      setPlaceLoading(false);
    }
  }

  async function useDeviceLocation(event) {
    if (!navigator.geolocation) {
      setFormError("Location access is not available in this browser.");
      return;
    }
    const form = event.currentTarget.form;
    setFormError("");
    setSelectedCoordinates(null);
    for (const name of ["state", "district", "locality"]) {
      const field = form?.elements.namedItem(name);
      if (field) field.value = "";
    }
    setPlaceLoading(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => selectLocation(
        coords.latitude,
        coords.longitude,
        text.locationChosen,
        form,
      ),
      () => {
        setFormError("Could not get your location. Check permission and try again.");
        setPlaceLoading(false);
      },
      { enableHighAccuracy: false, timeout: 10000 },
    );
  }

  async function submitForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (responseType === "request" && !selectedCoordinates) {
      setFormError(text.locationRequired);
      return;
    }
    const values = Object.fromEntries(new FormData(form));
    const id = newSubmissionId();
    const type = responseType;
    let payload;
    if (responseType === "request") {
      const itemName = values.item_name === "Other" ? values.other_item : values.item_name;
      payload = {
        client_submission_id: id,
        item_name: itemName || "General assistance",
        urgency: values.urgency,
        units_required: Number(values.units_required || 1),
        unit_label: values.unit_label,
        state: values.state || null,
        district: values.district || null,
        locality: values.locality || null,
        landmark: values.landmark || null,
        contact_name: values.contact_name,
        contact_phone: values.contact_phone,
        notes: values.notes || null,
        latitude: selectedCoordinates?.latitude,
        longitude: selectedCoordinates?.longitude,
      };
    } else {
      payload = {
        client_submission_id: id,
        help_request_item_id: Number(values.item_id),
        units_offered: Number(values.units_offered),
        donor_name: values.donor_name,
        donor_phone: values.donor_phone,
        pickup_location: values.pickup_location,
        pickup_latitude: selectedCoordinates?.latitude,
        pickup_longitude: selectedCoordinates?.longitude,
        notes: values.offer_notes || null,
      };
    }

    setFormError("");
    setFormMessage("");
    setSubmitting(true);
    if (!navigator.onLine) {
      try {
        await queueCoordinationSubmission(type, payload);
        setFormMessage(text.queued);
        form.reset();
        setSelectedCoordinates(null);
        setSelectedItemId("");
        setItemSelection("");
        await refreshQueueCount();
      } catch (queueError) {
        setFormError(queueError.message);
      } finally {
        setSubmitting(false);
      }
      return;
    }

    try {
      if (type === "request") payload = await geocodeHelpRequestPayload(payload);
      if (type === "offer") {
        const selected = openItems.find((item) => String(item.id) === values.item_id);
        if (!selected) {
          setFormError(text.noOpenItems);
          setSubmitting(false);
          return;
        }
        if (payload.units_offered > selected.units_remaining) {
          setFormError(`Only ${selected.units_remaining} ${selected.unit_label} remain for this request.`);
          setSubmitting(false);
          return;
        }
      }
    } catch (error) {
      setFormError(error.message || text.formError);
      setSubmitting(false);
      return;
    }

    try {
      if (type === "request") await createHelpRequest(payload);
      else await createSupplyOffer(payload);
      setFormMessage(text.submitted);
      form.reset();
      setSelectedCoordinates(null);
      setSelectedItemId("");
      setItemSelection("");
      await loadOpenItems();
      await loadHistory();
      onCountChanged?.();
    } catch (error) {
      if (!error.status || error.status >= 500) {
        try {
          await queueCoordinationSubmission(type, payload);
          setFormMessage(text.queued);
          form.reset();
          setSelectedCoordinates(null);
          setSelectedItemId("");
          setItemSelection("");
          await refreshQueueCount();
        } catch (queueError) {
          setFormError(queueError.message);
        }
      } else {
        setFormError(error.message || text.formError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function cancelMyRequest(request) {
    setHistoryActionId(`request-${request.id}`);
    setHistoryError("");
    try {
      await cancelHelpRequest(request.id);
      await loadHistory();
      await loadOpenItems();
      onCountChanged?.();
    } catch (error) {
      setHistoryError(error.message || text.historyActionError);
    } finally {
      setHistoryActionId(null);
    }
  }

  async function cancelMyOffer(offer) {
    setHistoryActionId(`offer-${offer.id}`);
    setHistoryError("");
    try {
      await cancelSupplyOffer(offer.id, "donor_cancelled");
      await loadHistory();
      await loadOpenItems();
      onCountChanged?.();
    } catch (error) {
      setHistoryError(error.message || text.historyActionError);
    } finally {
      setHistoryActionId(null);
    }
  }

  async function updateAttentionQuantity(event, submission) {
    event.preventDefault();
    const quantity = Number(new FormData(event.currentTarget).get("quantity"));
    if (!Number.isInteger(quantity) || quantity < 1) {
      setQueuedEditMessage("Enter a quantity greater than zero.");
      return;
    }
    const payload = {
      ...submission.payload,
      [submission.type === "request" ? "units_required" : "units_offered"]: quantity,
    };
    try {
      await updateQueuedCoordinationSubmission(submission.client_submission_id, payload);
      setQueuedEditMessage("");
      await syncQueued();
    } catch (error) {
      setQueuedEditMessage(error.message || text.formError);
    }
  }

  async function dismissAttentionSubmission(submission) {
    try {
      await removeQueuedCoordinationSubmission(submission.client_submission_id);
      await refreshQueueCount();
      setQueuedEditMessage("");
    } catch (error) {
      setQueuedEditMessage(error.message || text.formError);
    }
  }

  const selectedOfferItem = openItems.find((item) => String(item.id) === selectedItemId);

  return (
    <>
      <div className="notice-banner notice-amber coordination-notice">
        <span className="notice-symbol" aria-hidden="true">i</span>
        <div><strong>{text.responseNoticeTitle}</strong><p>{text.responseNotice}</p></div>
        {canOpenInbox ? (
          <button className="button button-outline" type="button" onClick={onOpenInbox}>
            {text.inbox} ({submissionCount})
          </button>
        ) : (
          <span className="button button-outline" aria-label={`${text.inbox} (${submissionCount})`}>
            {text.inbox} ({submissionCount})
          </span>
        )}
      </div>
      <div className="response-layout">
        <section className="panel response-form-panel">
          <div className="response-tabs" role="tablist" aria-label="Choose a response form">
            <button type="button" role="tab" aria-selected={responseType === "request"} className={responseType === "request" ? "response-tab active" : "response-tab"} onClick={() => { setResponseType("request"); setFormError(""); setFormMessage(""); setSelectedCoordinates(null); }}>
              {text.needTab}
            </button>
            <button type="button" role="tab" aria-selected={responseType === "offer"} className={responseType === "offer" ? "response-tab active" : "response-tab"} onClick={() => { setResponseType("offer"); setFormError(""); setFormMessage(""); setSelectedCoordinates(null); loadOpenItems(); }}>
              {text.offerTab}
            </button>
          </div>
          <div className="form-intro">
            <span className="section-kicker">{responseType === "request" ? text.needTab : text.offerTab}</span>
            <h2>{responseType === "request" ? text.requestTitle : text.offerTitle}</h2>
            <p>{responseType === "request" ? text.requestIntro : text.offerIntro}</p>
          </div>
          <form className="response-form" onSubmit={submitForm}>
            {responseType === "request" ? (
              <>
                <div className="form-row">
                  <label>{text.item}
                      <select name="item_name" required value={itemSelection} onChange={(event) => setItemSelection(event.target.value)}>
                      <option value="" disabled>{text.selectItem}</option>
                      {ITEM_OPTIONS.map((item) => <option value={item} key={item}>{item}</option>)}
                    </select>
                  </label>
                  <label>{text.urgency}
                    <select name="urgency" required defaultValue="general">
                      <option value="urgent">{text.urgent}</option><option value="high">{text.high}</option><option value="general">{text.general}</option>
                    </select>
                  </label>
                </div>
                <div className="form-row">
                  <label>{text.quantity}<input name="units_required" type="number" min="1" defaultValue="1" required /></label>
                  <label>{text.unit}
                    <select name="unit_label" defaultValue="units">
                      <option value="units">{text.units}</option><option value="people">{text.people}</option><option value="packets">{text.packets}</option><option value="litres">{text.litres}</option>
                    </select>
                  </label>
                </div>
                {itemSelection === "Other" && <label>{text.otherItem}<input name="other_item" required maxLength="120" placeholder={text.otherItem} /></label>}
                <div className="form-row">
                  <label>
                    {text.state} {selectedCoordinates && <span className="coordination-muted">(optional)</span>}
                    <input aria-label={text.state} name="state" maxLength="120" defaultValue={currentUser?.home_state || ""} />
                  </label>
                  <label>
                    {text.district} {selectedCoordinates && <span className="coordination-muted">(optional)</span>}
                    <input aria-label={text.district} name="district" maxLength="120" defaultValue={currentUser?.home_district || ""} />
                  </label>
                </div>
                <div className="form-row">
                  <label>
                    {text.locality} {selectedCoordinates && <span className="coordination-muted">(optional)</span>}
                    <input aria-label={text.locality} name="locality" maxLength="200" defaultValue={currentUser?.home_locality || ""} />
                  </label>
                  <label>{text.landmark}<input name="landmark" maxLength="200" defaultValue={currentUser?.home_landmark || ""} /></label>
                </div>
                <div className="coordination-location-actions">
                  <button type="button" className="button button-outline" onClick={useDeviceLocation} disabled={placeLoading}>
                    {placeLoading ? text.resolvingLocation : text.useDevice}
                  </button>
                  {selectedCoordinates && <span role="status">{selectedCoordinates.label}</span>}
                </div>
                {!selectedCoordinates && <p className="coordination-muted">{text.locationRequired}</p>}
                <div className="form-row">
                  <label>{text.contactName}<input name="contact_name" required maxLength="160" autoComplete="name" defaultValue={currentUser?.full_name || ""} /></label>
                  <label>{text.contactPhone}<input name="contact_phone" required type="tel" maxLength="40" autoComplete="tel" defaultValue={currentUser?.contact_phone || ""} /></label>
                </div>
                <label>{text.notes}<textarea name="notes" rows="3" maxLength="4000" placeholder={text.notesPlaceholder} /></label>
              </>
            ) : (
              <>
                <label>{text.selectRequest}
                  <select name="item_id" required value={selectedItemId} onChange={(event) => setSelectedItemId(event.target.value)}>
                    <option value="" disabled>{itemsLoading ? text.loadingItems : text.selectItem}</option>
                    {openItems.map((item) => (
                      <option value={item.id} key={item.id}>
                        {item.item_name} — {item.units_required} {text.required} ({item.units_remaining} {text.remaining}) · {[item.locality, item.district, item.state].filter(Boolean).join(", ")}
                      </option>
                    ))}
                  </select>
                </label>
                {itemError && <p className="coordination-error" role="alert">{itemError}</p>}
                {openItems.length === 0 && !itemsLoading && !itemError && <p className="coordination-muted">{text.noOpenItems}</p>}
                <div className="form-row">
                  <label>{text.unitsOffered}<input name="units_offered" type="number" min="1" max={selectedOfferItem?.units_remaining || undefined} required /></label>
                  <label>{text.donorName}<input name="donor_name" required maxLength="160" autoComplete="name" defaultValue={currentUser?.full_name || ""} /></label>
                </div>
                <div className="form-row">
                  <label>{text.donorPhone}<input name="donor_phone" required type="tel" maxLength="40" autoComplete="tel" defaultValue={currentUser?.contact_phone || ""} /></label>
                  <label>{text.pickup}<input name="pickup_location" required maxLength="300" placeholder={text.pickupPlaceholder} /></label>
                </div>
                <div className="coordination-location-actions">
                  <button type="button" className="button button-outline" onClick={useDeviceLocation}>{text.useDevice}</button>
                  {selectedCoordinates && <span role="status">{selectedCoordinates.label}</span>}
                </div>
                <label>{text.notes}<textarea name="offer_notes" rows="3" maxLength="4000" placeholder={text.notesPlaceholder} /></label>
              </>
            )}
            {formError && <p className="coordination-error" role="alert">{formError}</p>}
            {formMessage && (
              <div className="coordination-success" role="status">
                <span>{formMessage}</span>
                {formMessage === text.submitted && canOpenInbox && (
                  <a
                    className="text-link"
                    href="#responders"
                    onClick={(event) => {
                      event.preventDefault();
                      onOpenInbox?.();
                    }}
                  >
                    {text.openInbox}
                  </a>
                )}
              </div>
            )}
            <div className="form-actions">
              <button className="button button-primary" type="submit" disabled={submitting || (responseType === "offer" && openItems.length === 0)}>
                {submitting ? text.searching : responseType === "request" ? text.submitRequest : text.submitOffer}
              </button>
              {queuedCount > 0 && <span>{text.queuedCount}: {queuedCount}</span>}
            </div>
          </form>
          <section className="coordination-history" aria-labelledby="coordination-history-title">
            <div className="coordination-history-heading">
              <h3 id="coordination-history-title">
                {responseType === "request" ? text.requestHistory : text.offerHistory}
              </h3>
              {currentUser && (
                <button
                  type="button"
                  className="button button-outline"
                  onClick={loadHistory}
                  disabled={historyLoading}
                >
                  {text.refresh}
                </button>
              )}
            </div>
            {!currentUser ? (
              <p className="coordination-muted">{text.signInForHistory}</p>
            ) : historyError ? (
              <p className="coordination-error" role="alert">{historyError}</p>
            ) : historyLoading ? (
              <p className="coordination-muted">{text.searching}</p>
            ) : responseType === "request" ? (
              myRequests.length === 0 ? (
                <p className="coordination-muted">{text.noRequestHistory}</p>
              ) : (
                <div className="coordination-history-list">
                  {myRequests.map((request) => (
                    <article className="coordination-history-card" key={request.id}>
                      <div className="coordination-history-card-heading">
                        <strong>{request.items.map((item) => `${item.item_name} · ${item.units_fulfilled}/${item.units_required} ${item.unit_label} ${text.matched}`).join(", ")}</strong>
                        <span className="submission-status">{text.requestStatuses[request.status] || request.status}</span>
                      </div>
                      <p>{[request.locality, request.district, request.state].filter(Boolean).join(", ") || request.landmark || "Location shared with responders"}</p>
                      <small>#{request.id} · {new Date(request.created_at).toLocaleString()}</small>
                      {["open", "partially_fulfilled"].includes(request.status) && (
                        <button
                          type="button"
                          className="button button-outline"
                          disabled={historyActionId === `request-${request.id}`}
                          onClick={() => cancelMyRequest(request)}
                        >
                          {text.cancelRequest}
                        </button>
                      )}
                    </article>
                  ))}
                </div>
              )
            ) : myOffers.length === 0 ? (
              <p className="coordination-muted">{text.noOfferHistory}</p>
            ) : (
              <div className="coordination-history-list">
                {myOffers.map((offer) => (
                  <article className="coordination-history-card" key={offer.id}>
                    <div className="coordination-history-card-heading">
                      <strong>{offer.item_name} · {offer.actual_units_picked_up ?? offer.units_offered} {offer.unit_label}</strong>
                      <span className="submission-status">{text.statuses[offer.status] || offer.status}</span>
                    </div>
                    <p>{offer.drop_location || offer.pickup_location}</p>
                    <small>#{offer.id} · {new Date(offer.created_at).toLocaleString()}</small>
                    {!["cancelled", "delivered"].includes(offer.status) && (
                      <button
                        type="button"
                        className="button button-outline"
                        disabled={historyActionId === `offer-${offer.id}`}
                        onClick={() => cancelMyOffer(offer)}
                      >
                        {text.cancelDonation}
                      </button>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </section>
        <aside className="response-aside">
          <div className="panel matching-panel">
            <span className="section-kicker">COORDINATION WORKFLOW</span>
            <h2>Needs meet local capacity</h2>
            <p>Offers are matched to an open item, then tracked by authorized responders through delivery.</p>
            <div className="match-steps">
              <div><span>1</span><p><strong>Submit a request or offer</strong><small>Include a clear quantity and location</small></p></div>
              <div><span>2</span><p><strong>Responder claims an offer</strong><small>Contacts are available to authorized responders</small></p></div>
              <div><span>3</span><p><strong>Track delivery progress</strong><small>Contacted · picked up · delivered</small></p></div>
            </div>
          </div>
        </aside>
      </div>
      {attentionSubmissions.length > 0 && (
        <section className="panel coordination-attention" aria-label={text.needsAttention}>
          <h2>{text.needsAttention}</h2>
          <p>These saved submissions were rejected and will not be retried automatically.</p>
          {queuedEditMessage && <p className="coordination-error" role="alert">{queuedEditMessage}</p>}
          {attentionSubmissions.map((submission) => (
            <article key={submission.client_submission_id}>
              <strong>{submission.type === "request" ? text.queuedRequest : text.queuedOffer}</strong>
              <p>{submission.error_reason}</p>
              <form onSubmit={(event) => updateAttentionQuantity(event, submission)}>
                <label>Quantity
                  <input
                    name="quantity"
                    type="number"
                    min="1"
                    defaultValue={submission.payload.units_offered ?? submission.payload.units_required}
                    required
                  />
                </label>
                <button className="button button-primary" type="submit">{text.saveAndRetry}</button>
                <button
                  className="button button-outline"
                  type="button"
                  onClick={() => dismissAttentionSubmission(submission)}
                >
                  {text.dismiss}
                </button>
              </form>
            </article>
          ))}
        </section>
      )}
    </>
  );
}

export function ResponderInbox({ language = "en", onCountChanged, currentUser, submissionCount = 0, onAccessDenied }) {
  const text = COPY[language] || COPY.en;
  const [offers, setOffers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [responderCoordinates, setResponderCoordinates] = useState(null);
  const [pickupQuantities, setPickupQuantities] = useState({});
  const [statusFilter, setStatusFilter] = useState("");
  const [itemFilter, setItemFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionId, setActionId] = useState(null);

  const queueRows = [];
  const includedOfferIds = new Set();
  for (const request of requests) {
    for (const item of request.items) {
      const itemOffers = offers.filter((offer) => offer.help_request_item_id === item.id);
      if (itemOffers.length === 0) {
        queueRows.push({
          key: `request-${request.id}-${item.id}`,
          request,
          item,
          offer: null,
        });
      } else {
        for (const offer of itemOffers) {
          includedOfferIds.add(offer.id);
          queueRows.push({
            key: `offer-${offer.id}`,
            request,
            item,
            offer,
          });
        }
      }
    }
  }
  for (const offer of offers) {
    if (!includedOfferIds.has(offer.id)) {
      queueRows.push({
        key: `offer-${offer.id}`,
        request: null,
        item: {
          item_name: offer.item_name,
          units_required: offer.units_offered,
          units_remaining: offer.units_offered,
          unit_label: offer.unit_label,
        },
        offer,
      });
    }
  }

  const loadQueue = useCallback(async (signal) => {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (itemFilter.trim()) params.item = itemFilter.trim();
      if (locationFilter.trim()) params.location = locationFilter.trim();
      if (responderCoordinates) {
        params.latitude = responderCoordinates.latitude;
        params.longitude = responderCoordinates.longitude;
      }
      const requestParams = {
        active_only: true,
        item: params.item,
        location: params.location,
        latitude: params.latitude,
        longitude: params.longitude,
      };
      const [offerRows, requestRows] = await Promise.all([
        getSupplyOffers(params, signal),
        getHelpRequests(requestParams, signal),
      ]);
      setOffers(offerRows);
      setRequests(requestRows);
    } catch (loadError) {
      if (loadError.name !== "AbortError") {
        if (loadError.status === 401 || loadError.status === 403) {
          await onAccessDenied?.();
        } else {
          setError(loadError.message || text.inboxLoad);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [itemFilter, locationFilter, responderCoordinates, statusFilter, text.inboxLoad, onAccessDenied]);

  useEffect(() => {
    const controller = new AbortController();
    loadQueue(controller.signal);
    return () => controller.abort();
  }, [loadQueue]);

  async function runOfferAction(offer, action, actualUnitsPickedUp) {
    setActionId(offer.id);
    setError("");
    try {
      if (action === "assign") await claimSupplyOffer(offer.id);
      else if (action === "cancel") await cancelSupplyOffer(offer.id, actualUnitsPickedUp);
      else if (action === "picked_up") {
        await updateSupplyOfferStatus(offer.id, action, actualUnitsPickedUp);
      } else await updateSupplyOfferStatus(offer.id, action);
      await loadQueue();
      onCountChanged?.();
    } catch (actionError) {
      setError(actionError.message || text.formError);
    } finally {
      setActionId(null);
    }
  }

  function useResponderLocation() {
    if (!navigator.geolocation) {
      setError("Location access is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setResponderCoordinates({ latitude: coords.latitude, longitude: coords.longitude });
        setError("");
      },
      () => setError("Could not get your location. Check permission and try again."),
      { enableHighAccuracy: false, timeout: 10000 },
    );
  }

  return (
    <section className="responder-desk">
      <div className="notice-banner notice-blue responder-notice">
        <span className="notice-symbol" aria-hidden="true">i</span>
        <div><strong>{text.inboxNoticeTitle}</strong><p>{text.inboxNotice}</p></div>
        <span className="button button-outline" aria-label={`${text.inbox} (${submissionCount})`}>
          {text.inbox} ({submissionCount})
        </span>
      </div>
      {error && <p className="coordination-error" role="alert">{error}</p>}
      <div className="panel responder-list-panel">
        <div className="responder-list-heading">
          <div><span className="section-kicker">{text.activeQueue}</span><h2>{text.titleInbox}</h2></div>
          <button type="button" className="button button-outline" onClick={() => loadQueue()} disabled={loading}>{text.refresh}</button>
        </div>
        <div className="coordination-filters">
          <button type="button" className="button button-outline" onClick={useResponderLocation}>
            {responderCoordinates ? "Sorting near your location" : "Sort by my location"}
          </button>
          <label>{text.statusFilter}
            <select aria-label={text.statusFilter} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">{text.allStatuses}</option>
              {STATUS_OPTIONS.map((status) => <option value={status} key={status}>{text.statuses[status]}</option>)}
            </select>
          </label>
          <label>{text.itemFilter}<input aria-label={text.itemFilter} value={itemFilter} onChange={(event) => setItemFilter(event.target.value)} /></label>
          <label>{text.locationFilter}<input aria-label={text.locationFilter} value={locationFilter} onChange={(event) => setLocationFilter(event.target.value)} /></label>
        </div>
        {loading && queueRows.length === 0 ? <p className="coordination-muted">Loading coordination queue…</p> : null}
        {queueRows.length === 0 && !loading ? (
          <div className="responder-empty"><h3>{text.noOffers}</h3></div>
        ) : queueRows.length > 0 ? (
          <div className="responder-table-wrap">
            <table className="responder-queue-table" aria-label={text.queueTableLabel}>
              <thead>
                <tr>
                  <th scope="col">{text.requester}</th>
                  <th scope="col">{text.need}</th>
                  <th scope="col">{text.donor}</th>
                  <th scope="col">{text.pickupLabel}</th>
                  <th scope="col">{text.dropoffLabel}</th>
                  <th scope="col">{text.queueStatus}</th>
                  <th scope="col">{text.queueActions}</th>
                </tr>
              </thead>
              <tbody>
                {queueRows.map(({ key, request, item, offer }) => {
                  const requesterName = request?.contact_name || offer?.requester_name;
                  const requesterPhone = request?.contact_phone || offer?.requester_phone;
                  const deliveryLocation = offer?.drop_location || [
                    request?.landmark,
                    request?.locality,
                    request?.district,
                    request?.state,
                  ].filter(Boolean).join(", ") || (
                    request ? `${request.latitude}, ${request.longitude}` : ""
                  );
                  const status = offer
                    ? text.statuses[offer.status] || offer.status
                    : text.requestStatuses[request.status] || request.status;

                  return (
                    <tr key={key}>
                      <td>
                        <strong>{requesterName}</strong>
                        {requesterPhone && <a href={`tel:${requesterPhone}`}>{requesterPhone}</a>}
                      </td>
                      <td>
                        <strong>{item.item_name}</strong>
                        <span>{item.units_remaining} {item.unit_label} {text.remaining}</span>
                        {offer && <span>{text.unitsOffered}: {offer.units_offered} {offer.unit_label}</span>}
                        {offer?.actual_units_picked_up !== null &&
                          offer?.actual_units_picked_up !== undefined && (
                            <span>{text.pickedUpQuantity}: {offer.actual_units_picked_up} {offer.unit_label}</span>
                          )}
                        {request && (
                          <small>
                            {item.units_fulfilled}/{item.units_required} {item.unit_label} {text.matched}
                          </small>
                        )}
                        {request?.urgency && <small>{text.urgency}: {request.urgency}</small>}
                        {request?.notes && <small>{request.notes}</small>}
                        {offer?.notes && <small>{offer.notes}</small>}
                      </td>
                      <td>
                        {offer ? (
                          <>
                            <strong>{offer.donor_name}</strong>
                            {offer.donor_phone && <a href={`tel:${offer.donor_phone}`}>{offer.donor_phone}</a>}
                          </>
                        ) : <span className="responder-placeholder">{text.noDonorYet}</span>}
                      </td>
                      <td>{offer?.pickup_location || <span className="responder-placeholder">{text.noPickupYet}</span>}</td>
                      <td>{deliveryLocation || "—"}</td>
                      <td>
                        <span className="submission-status">{status}</span>
                        <small>#{offer?.id ?? request.id} · {new Date(offer?.created_at || request.created_at).toLocaleString()}</small>
                        {offer?.assignment_responder_id && (
                          <small>{text.assigned}: {offer.assignment_responder_id}</small>
                        )}
                      </td>
                      <td>
                        {offer && (
                          <div className="coordination-offer-actions">
                            {offer.status === "pending_responder" && <button className="button button-primary" disabled={actionId === offer.id} onClick={() => runOfferAction(offer, "assign")}>{text.claim}</button>}
                            {offer.status === "responder_assigned" && <button className="button button-primary" disabled={actionId === offer.id} onClick={() => runOfferAction(offer, "contacted")}>{text.contacted}</button>}
                            {offer.status === "contacted" && (
                              <>
                                <label>{text.pickedUpQuantity}
                                  <input
                                    aria-label={`${text.pickedUpQuantity} ${offer.id}`}
                                    type="number"
                                    min="0"
                                    max={offer.units_offered}
                                    value={pickupQuantities[offer.id] ?? offer.units_offered}
                                    onChange={(event) => setPickupQuantities({
                                      ...pickupQuantities,
                                      [offer.id]: Number(event.target.value),
                                    })}
                                  />
                                </label>
                                <button
                                  className="button button-primary"
                                  disabled={actionId === offer.id}
                                  onClick={() => runOfferAction(
                                    offer,
                                    "picked_up",
                                    pickupQuantities[offer.id] ?? offer.units_offered,
                                  )}
                                >
                                  {text.picked_up}
                                </button>
                              </>
                            )}
                            {offer.status === "picked_up" && <button className="button button-primary" disabled={actionId === offer.id} onClick={() => runOfferAction(offer, "delivered")}>{text.delivered}</button>}
                            {(currentUser?.is_admin || offer.assignment_responder_id === currentUser?.id) &&
                              !["cancelled", "delivered"].includes(offer.status) && (
                                <>
                                  <button
                                    className="button button-outline"
                                    disabled={actionId === offer.id}
                                    onClick={() => runOfferAction(offer, "cancel", "donor_cancelled")}
                                  >
                                    {text.donorCancelled}
                                  </button>
                                  <button
                                    className="button button-outline"
                                    disabled={actionId === offer.id}
                                    onClick={() => runOfferAction(offer, "cancel", "donor_unreachable")}
                                  >
                                    {text.donorUnreachable}
                                  </button>
                                </>
                              )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}
