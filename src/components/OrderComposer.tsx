import { useEffect, useState } from "react";
import { networks, type NetworkId } from "../data/networks";
import { createOrder, getBundles, type Bundle, type PurchaseOrder } from "../lib/api";
import { isValidGhanaPhone, maskPhoneNumber } from "../lib/phone";
import { Icon, NetworkMark, NetworkSelector } from "./Ui";

export function OrderComposer({ agentMode = false }: { agentMode?: boolean }) {
  const [network, setNetwork] = useState<NetworkId | null>(null);
  const [phone, setPhone] = useState("");
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [bundleId, setBundleId] = useState("");
  const [loadingBundles, setLoadingBundles] = useState(false);
  const [catalogueError, setCatalogueError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [createdOrder, setCreatedOrder] = useState<PurchaseOrder | null>(null);
  const selectedNetwork = networks.find((item) => item.id === network);
  const selectedBundle = bundles.find((item) => item.id === bundleId);
  const phoneIsValid = isValidGhanaPhone(phone);

  useEffect(() => {
    if (!network) {
      setBundles([]);
      setBundleId("");
      setCatalogueError("");
      setLoadingBundles(false);
      return;
    }

    let active = true;
    setBundles([]);
    setBundleId("");
    setCatalogueError("");
    setLoadingBundles(true);
    getBundles(network)
      .then((availableBundles) => {
        if (active) setBundles(availableBundles);
      })
      .catch((error: unknown) => {
        if (active) {
          setCatalogueError(
            error instanceof Error ? error.message : "Could not load bundle options.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingBundles(false);
      });

    return () => {
      active = false;
    };
  }, [network]);

  async function submitPurchaseRequest() {
    if (!network || !phoneIsValid || !selectedBundle || submitting) return;
    setSubmitting(true);
    setSubmitError("");
    setCreatedOrder(null);
    try {
      const order = await createOrder({
        phone,
        network_id: network,
        bundle_id: selectedBundle.id,
      });
      setCreatedOrder(order);
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Could not create the purchase request.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      aria-labelledby="composer-title"
      className={`composer-card${agentMode ? " composer-card--agent" : ""}`}
      id={agentMode ? "sale-workbench" : "purchase"}
    >
      <div className="composer-card__heading">
        <div>
          <span className="step-label">{agentMode ? "AGENT WORKFLOW" : "QUICK PURCHASE"}</span>
          <h2 id="composer-title">{agentMode ? "Start a customer sale" : "Buy data in a few taps"}</h2>
        </div>
        <span className="composer-secure">
          <Icon name="lock" size={15} />
          Secure by design
        </span>
      </div>

      <div className="composer-steps" aria-label="Purchase steps">
        <span className="composer-step composer-step--active"><b>1</b> Choose</span>
        <span className="composer-step"><b>2</b> Review</span>
        <span className="composer-step"><b>3</b> Pay</span>
      </div>

      <div className="composer-form">
        <NetworkSelector
          value={network}
          onChange={(value) => {
            setNetwork(value);
            setCreatedOrder(null);
            setSubmitError("");
          }}
          compact
        />

        <div className="field-group">
          <label htmlFor={agentMode ? "agent-phone" : "recipient-phone"}>
            Recipient phone number
          </label>
          <div className="phone-input">
            <span className="phone-input__country" aria-label="Ghana country code">
              <span aria-hidden="true">GH</span>
              <Icon name="chevron-down" size={14} />
            </span>
            <input
              autoComplete="tel"
              id={agentMode ? "agent-phone" : "recipient-phone"}
              inputMode="tel"
              maxLength={18}
              onChange={(event) => {
                setPhone(event.target.value);
                setCreatedOrder(null);
                setSubmitError("");
              }}
              placeholder="024 000 0000"
              type="tel"
              value={phone}
            />
            <Icon className="phone-input__icon" name="phone" size={17} />
          </div>
          {phone.length > 0 && !phoneIsValid && (
            <span className="field-hint field-hint--error" role="status">
              Enter a valid Ghanaian mobile number.
            </span>
          )}
        </div>

        <div className="field-group">
          <label htmlFor={agentMode ? "agent-bundle" : "bundle-choice"}>Choose a data bundle</label>
          <div className="select-wrap">
            <select
              disabled={!network || loadingBundles || bundles.length === 0}
              id={agentMode ? "agent-bundle" : "bundle-choice"}
              onChange={(event) => {
                setBundleId(event.target.value);
                setCreatedOrder(null);
                setSubmitError("");
              }}
              value={bundleId}
              aria-describedby={agentMode ? "agent-catalogue-note" : "catalogue-note"}
            >
              <option value="">
                {!network
                  ? "Select a network first"
                  : loadingBundles
                    ? "Loading available bundles…"
                    : bundles.length
                      ? "Choose a bundle"
                      : "No bundles are available"}
              </option>
              {bundles.map((bundle) => (
                <option key={bundle.id} value={bundle.id}>
                  {bundle.name} — GHS {Number(bundle.amount).toFixed(2)}
                  {bundle.is_sample ? " (sample)" : ""}
                </option>
              ))}
            </select>
            <Icon name="chevron-down" size={17} />
          </div>
          <span
            className={`field-hint${catalogueError ? " field-hint--error" : ""}`}
            id={agentMode ? "agent-catalogue-note" : "catalogue-note"}
            role={catalogueError ? "alert" : undefined}
          >
            {catalogueError ||
              (selectedBundle?.is_sample
                ? "Sample offer for development only; no live service or payment is attached."
                : "Only offers returned by the backend can be selected.")}
          </span>
        </div>
      </div>

      <div className="order-summary">
        <div className="order-summary__label">
          <span>Order summary</span>
          <span className="summary-muted">No charge yet</span>
        </div>
        <div className="order-summary__line">
          <span className="summary-network">
            {selectedNetwork ? (
              <>
                <NetworkMark networkId={selectedNetwork.id} />
                {selectedNetwork.shortName} data
              </>
            ) : (
              "Choose a network"
            )}
          </span>
          <strong>
            {selectedBundle
              ? `GHS ${Number(selectedBundle.amount).toFixed(2)}`
              : "GHS —"}
          </strong>
        </div>
        <div className="order-summary__line order-summary__line--subtle">
          <span>Sending to</span>
          <span>{phoneIsValid ? maskPhoneNumber(phone) : "—"}</span>
        </div>
      </div>

      <button
        className="button button--primary button--wide"
        disabled={!network || !phoneIsValid || !selectedBundle || submitting}
        onClick={submitPurchaseRequest}
        type="button"
      >
        {submitting ? "Creating request…" : "Create purchase request"}
        <Icon name="arrow-right" size={17} />
      </button>
      {submitError && <p className="field-hint field-hint--error" role="alert">{submitError}</p>}
      {createdOrder && (
        <div className="order-result" role="status">
          <strong>Purchase request created</strong>
          <span>Reference: {createdOrder.reference}</span>
          <span>Status: {createdOrder.status.replaceAll("_", " ")}</span>
          {createdOrder.is_sample && (
            <span>Sample order only. No payment or delivery has been initiated.</span>
          )}
        </div>
      )}
      <p className="composer-note">
        <Icon name="lock" size={14} />
        No payment is taken here. Mobile money PINs are never requested or stored.
      </p>
    </section>
  );
}
