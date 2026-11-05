import { useState } from "react";
import { networks, type NetworkId } from "../data/networks";
import { isValidGhanaPhone, maskPhoneNumber } from "../lib/phone";
import { Icon, NetworkMark, NetworkSelector } from "./Ui";

export function OrderComposer({ agentMode = false }: { agentMode?: boolean }) {
  const [network, setNetwork] = useState<NetworkId | null>(null);
  const [phone, setPhone] = useState("");
  const selectedNetwork = networks.find((item) => item.id === network);
  const phoneIsValid = isValidGhanaPhone(phone);

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
        <NetworkSelector value={network} onChange={setNetwork} compact />

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
              onChange={(event) => setPhone(event.target.value)}
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
              disabled
              id={agentMode ? "agent-bundle" : "bundle-choice"}
              value=""
              aria-describedby={agentMode ? "agent-catalogue-note" : "catalogue-note"}
            >
              <option value="">
                {network ? "No verified bundles available yet" : "Select a network first"}
              </option>
            </select>
            <Icon name="chevron-down" size={17} />
          </div>
          <span className="field-hint" id={agentMode ? "agent-catalogue-note" : "catalogue-note"}>
            Bundle options will appear when supplier catalogues are connected.
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
          <strong>GHS —</strong>
        </div>
        <div className="order-summary__line order-summary__line--subtle">
          <span>Sending to</span>
          <span>{phoneIsValid ? maskPhoneNumber(phone) : "—"}</span>
        </div>
      </div>

      <button className="button button--primary button--wide" disabled type="button">
        Continue to payment
        <Icon name="arrow-right" size={17} />
      </button>
      <p className="composer-note">
        <Icon name="lock" size={14} />
        Mobile money PINs are entered only with your payment provider, never here.
      </p>
    </section>
  );
}
