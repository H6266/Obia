import type { CSSProperties, ReactNode } from "react";
import { networks, type NetworkId } from "../data/networks";

type IconName =
  | "arrow-down"
  | "arrow-right"
  | "arrow-up-right"
  | "chart"
  | "check"
  | "chevron-down"
  | "clock"
  | "close"
  | "lock"
  | "menu"
  | "phone"
  | "plus"
  | "refresh"
  | "receipt"
  | "search"
  | "shield"
  | "spark"
  | "support"
  | "wallet";

const iconShapes: Record<IconName, ReactNode> = {
  "arrow-down": <path d="M12 5v14m7-7-7 7-7-7" />,
  "arrow-right": <path d="M5 12h14m-7-7 7 7-7 7" />,
  "arrow-up-right": <path d="M7 17 17 7M7 7h10v10" />,
  chart: (
    <>
      <path d="M4 20V4m0 16h16" />
      <path d="m7 15 3-4 3 2 5-7" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  "chevron-down": <path d="m6 9 6 6 6-6" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
  lock: (
    <>
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 1 1 8 0v3m-4 5v2" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  phone: (
    <>
      <rect x="6" y="2" width="12" height="20" rx="2" />
      <path d="M11 18h2" />
    </>
  ),
  plus: <path d="M12 5v14m-7-7h14" />,
  refresh: (
    <>
      <path d="M20 7v5h-5M4 17v-5h5" />
      <path d="M5.6 9a7 7 0 0 1 11.6-2L20 12M4 12l2.8 5a7 7 0 0 0 11.6-2" />
    </>
  ),
  receipt: (
    <>
      <path d="M5 3h14v18l-3-2-4 2-4-2-3 2V3Z" />
      <path d="M9 8h6m-6 4h6m-6 4h3" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  shield: (
    <>
      <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />
      <path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z" />
    </>
  ),
  support: (
    <>
      <path d="M4 13v-2a8 8 0 0 1 16 0v2" />
      <path d="M4 13h3v6H6a2 2 0 0 1-2-2v-4Zm16 0h-3v6h1a2 2 0 0 0 2-2v-4ZM12 21h2" />
    </>
  ),
  wallet: (
    <>
      <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H20v16H6a2 2 0 0 1-2-2V6.5Z" />
      <path d="M4 7h16m-4 6h4m-3 0h.01" />
    </>
  ),
};

export function Icon({
  name,
  size = 20,
  className,
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {iconShapes[name]}
    </svg>
  );
}

export function NetworkMark({ networkId }: { networkId: NetworkId }) {
  const network = networks.find((item) => item.id === networkId)!;
  const style = {
    "--network-color": network.color,
    "--network-surface": network.surface,
  } as CSSProperties;

  return (
    <span className={`network-mark network-mark--${network.id}`} style={style}>
      {network.initial}
    </span>
  );
}

export function NetworkSelector({
  value,
  onChange,
  legend = "Choose a network",
  compact = false,
}: {
  value: NetworkId | null;
  onChange: (network: NetworkId) => void;
  legend?: string;
  compact?: boolean;
}) {
  return (
    <fieldset className={`network-fieldset${compact ? " network-fieldset--compact" : ""}`}>
      <legend>{legend}</legend>
      <div className="network-options">
        {networks.map((network) => (
          <button
            aria-pressed={value === network.id}
            className={`network-option${value === network.id ? " is-selected" : ""}`}
            key={network.id}
            onClick={() => onChange(network.id)}
            type="button"
          >
            <NetworkMark networkId={network.id} />
            <span>{network.name}</span>
            <span className="network-option__radio" aria-hidden="true">
              {value === network.id && <Icon name="check" size={12} />}
            </span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function PageIntro({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-intro__actions">{actions}</div>}
    </div>
  );
}

export function NoticeBanner({
  title,
  children,
  tone = "info",
}: {
  title: string;
  children: ReactNode;
  tone?: "info" | "warning";
}) {
  return (
    <div className={`notice-banner notice-banner--${tone}`} role="status">
      <span className="notice-banner__icon">
        <Icon name={tone === "warning" ? "clock" : "shield"} size={19} />
      </span>
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </div>
  );
}

export function DataState({
  icon = "spark",
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="data-state">
      <span className="data-state__icon">
        <Icon name={icon} size={22} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}

export function StatusPill({
  children,
  tone = "pending",
}: {
  children: ReactNode;
  tone?: "pending" | "success" | "neutral";
}) {
  return (
    <span className={`status-pill status-pill--${tone}`}>
      <span className="status-pill__dot" />
      {children}
    </span>
  );
}
