import { useState } from "react";
import { OrderComposer } from "../components/OrderComposer";
import {
  Icon,
  NetworkMark,
  NoticeBanner,
  StatusPill,
} from "../components/Ui";
import { networks, type NetworkId } from "../data/networks";

const benefits = [
  {
    icon: "spark" as const,
    title: "Less searching",
    body: "A clear place to explore Ghana's mobile networks and find the right way to stay connected.",
  },
  {
    icon: "shield" as const,
    title: "Clarity at every step",
    body: "Know what is confirmed, what is still processing, and what needs attention.",
  },
  {
    icon: "wallet" as const,
    title: "No surprises",
    body: "See the full order summary before any payment flow begins.",
  },
  {
    icon: "support" as const,
    title: "Help when you need it",
    body: "A simple path to support for order questions and account assistance.",
  },
];

export function HomePage() {
  const [filter, setFilter] = useState<NetworkId | "all">("all");
  const visibleNetworks = filter === "all" ? networks : networks.filter((item) => item.id === filter);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <main id="main-content" tabIndex={-1}>
      <section className="hero-section">
        <div className="hero-copy">
          <div className="hero-kicker">
            <span className="hero-kicker__dot" />
            MADE FOR GHANA, MADE FOR EVERY DAY
          </div>
          <h1>Data that keeps Ghana <span>moving.</span></h1>
          <p>
            Find the right mobile data bundle, send it to any number, and follow every
            step with confidence.
          </p>
          <div className="hero-actions">
            <button className="button button--primary" onClick={() => scrollTo("purchase")} type="button">
              Buy data
              <Icon name="arrow-right" size={17} />
            </button>
            <button className="button button--text" onClick={() => scrollTo("catalogue")} type="button">
              Explore networks
              <Icon name="arrow-down" size={17} />
            </button>
          </div>
          <div className="hero-proof">
            <span className="hero-proof__avatars" aria-hidden="true">
              {networks.map((network) => <NetworkMark key={network.id} networkId={network.id} />)}
            </span>
            <span>One place for the networks you know</span>
          </div>
        </div>

        <div className="hero-art" aria-label="Falaaa data marketplace preview">
          <div className="hero-art__orbit hero-art__orbit--outer" />
          <div className="hero-art__orbit hero-art__orbit--inner" />
          <div className="hero-art__signal">
            <span className="hero-art__signal-line hero-art__signal-line--one" />
            <span className="hero-art__signal-line hero-art__signal-line--two" />
            <span className="hero-art__signal-line hero-art__signal-line--three" />
          </div>
          <div className="hero-phone">
            <div className="hero-phone__notch" />
            <div className="hero-phone__topline">
              <span className="brand-symbol brand-symbol--small">f</span>
              <span>falaaa</span>
              <span className="hero-phone__dots">•••</span>
            </div>
            <div className="hero-phone__greeting">Good morning</div>
            <strong className="hero-phone__headline">Stay connected</strong>
            <div className="hero-phone__balance">
              <div className="hero-phone__balance-icon"><Icon name="spark" size={18} /></div>
              <div><small>Choose a network</small><strong>Your next bundle starts here</strong></div>
              <Icon name="arrow-up-right" size={17} />
            </div>
            <div className="hero-phone__list-label">NETWORKS</div>
            {networks.map((network) => (
              <div className="hero-phone__network" key={network.id}>
                <NetworkMark networkId={network.id} />
                <span>{network.name}</span>
                <Icon name="arrow-right" size={15} />
              </div>
            ))}
            <div className="hero-phone__bottom">
              <span className="hero-phone__home-indicator" />
            </div>
          </div>
          <div className="hero-float hero-float--status">
            <span className="hero-float__status-icon"><Icon name="shield" size={17} /></span>
            <span><strong>Every step, clear.</strong><small>Know what is confirmed</small></span>
          </div>
          <div className="hero-float hero-float--ghana">
            <span className="ghana-dot" />
            <span>Built for Ghana</span>
          </div>
          <div className="hero-art__caption">SIMPLE. CLEAR. CONNECTED.</div>
        </div>
      </section>

      <section className="market-strip" aria-label="Available mobile networks">
        <span className="market-strip__label">CHOOSE YOUR NETWORK</span>
        <div className="market-strip__networks">
          {networks.map((network) => (
            <span className="market-strip__network" key={network.id}>
              <NetworkMark networkId={network.id} />
              {network.name}
            </span>
          ))}
        </div>
        <span className="market-strip__country"><span className="ghana-dot" /> Ghana</span>
      </section>

      <section className="purchase-section section-wrap">
        <div className="purchase-copy">
          <span className="eyebrow">A BETTER WAY TO TOP UP</span>
          <h2>Make your next bundle feel effortless.</h2>
          <p>
            Pick a network, enter the number, and see your order before you pay.
            It is as simple as that.
          </p>
          <ul className="check-list">
            <li><span><Icon name="check" size={14} /></span>Send data to yourself or someone else</li>
            <li><span><Icon name="check" size={14} /></span>Keep the recipient number in view</li>
            <li><span><Icon name="check" size={14} /></span>Track progress without the guesswork</li>
          </ul>
          <div className="purchase-copy__trust">
            <Icon name="lock" size={16} />
            Your mobile money PIN is never entered on Falaaa.
          </div>
        </div>
        <OrderComposer />
      </section>

      <section className="catalogue-section" id="catalogue">
        <div className="section-wrap">
          <div className="section-heading">
            <div>
              <span className="eyebrow">THE BUNDLE CATALOGUE</span>
              <h2>Pick your network. We’ll take it from there.</h2>
              <p>Offers will show here as soon as the supplier catalogues are verified.</p>
            </div>
            <span className="catalogue-count"><span className="catalogue-count__dot" /> Live offers coming soon</span>
          </div>

          <div className="catalogue-toolbar">
            <div className="filter-tabs" role="group" aria-label="Filter by network">
              <button
                aria-pressed={filter === "all"}
                className={filter === "all" ? "is-active" : ""}
                onClick={() => setFilter("all")}
                type="button"
              >
                All networks
              </button>
              {networks.map((network) => (
                <button
                  aria-pressed={filter === network.id}
                  className={filter === network.id ? "is-active" : ""}
                  key={network.id}
                  onClick={() => setFilter(network.id)}
                  type="button"
                >
                  {network.shortName}
                </button>
              ))}
            </div>
            <span className="catalogue-toolbar__hint">Prices and availability are not connected</span>
          </div>

          <div className="bundle-grid">
            {visibleNetworks.map((network) => (
              <article className="bundle-card" key={network.id}>
                <div className="bundle-card__top">
                  <NetworkMark networkId={network.id} />
                  <StatusPill>Catalogue pending</StatusPill>
                </div>
                <h3>{network.name}</h3>
                <p className="bundle-card__description">Verified data bundles will be listed here.</p>
                <div className="bundle-card__details">
                  <div><span>Bundle size</span><strong>—</strong></div>
                  <div><span>Price</span><strong>GHS —</strong></div>
                </div>
                <div className="bundle-card__bottom">
                  <span><Icon name="clock" size={14} /> Availability pending</span>
                  <button disabled type="button">Unavailable</button>
                </div>
              </article>
            ))}
          </div>
          <NoticeBanner title="Offers are not live yet">
            The catalogue will display verified bundle sizes, prices, and availability only after a supplier integration is configured.
          </NoticeBanner>
        </div>
      </section>

      <section className="how-section section-wrap">
        <div className="section-heading section-heading--center">
          <span className="eyebrow">SIMPLE FROM START TO FINISH</span>
          <h2>Stay connected in three clear steps.</h2>
          <p>No confusing menus. Just the information you need, when you need it.</p>
        </div>
        <div className="how-grid">
          {[
            ["01", "Choose a network", "Pick MTN, Telecel or AirtelTigo for the number you have in mind."],
            ["02", "Review your order", "Check the recipient and bundle details before moving to payment."],
            ["03", "Follow your status", "See when payment and delivery are confirmed, not before."],
          ].map(([number, title, body]) => (
            <article className="how-card" key={number}>
              <span className="how-card__number">{number}</span>
              <div className="how-card__rule" />
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="benefits-section">
        <div className="section-wrap">
          <div className="section-heading">
            <div>
              <span className="eyebrow">BUILT AROUND YOU</span>
              <h2>Good data. Clear decisions.</h2>
            </div>
            <p className="section-heading__aside">A more considered way to buy mobile data, with the details never hidden.</p>
          </div>
          <div className="benefit-grid">
            {benefits.map((benefit, index) => (
              <article className="benefit-card" key={benefit.title}>
                <span className={`benefit-card__icon benefit-card__icon--${index + 1}`}>
                  <Icon name={benefit.icon} size={20} />
                </span>
                <h3>{benefit.title}</h3>
                <p>{benefit.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="support-cta section-wrap">
        <div className="support-cta__icon"><Icon name="support" size={23} /></div>
        <div>
          <h2>Need a hand?</h2>
          <p>Our customer support team will be here to help with your orders and questions.</p>
        </div>
        <a className="button button--outline" href="mailto:support@falaaa.example">
          Contact support
          <Icon name="arrow-up-right" size={16} />
        </a>
        <span className="support-cta__note">Contact details are placeholders until launch.</span>
      </section>
    </main>
  );
}
