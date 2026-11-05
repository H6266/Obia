import { Link, useLocation } from "react-router-dom";
import { Icon, NoticeBanner, PageIntro } from "../components/Ui";

export function InfoPage() {
  const { pathname } = useLocation();
  const privacy = pathname === "/privacy";
  const title = privacy ? "Privacy at Falaaa" : "Terms of use";

  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="FALAAA POLICIES"
          title={title}
          description="Our full policy documents will be published before the service launches."
          actions={
            <Link className="button button--outline" to="/">
              <Icon name="arrow-right" size={16} />
              Back to home
            </Link>
          }
        />
        <div className="policy-placeholder">
          <span className="policy-placeholder__icon"><Icon name="shield" size={22} /></span>
          <div>
            <h2>{privacy ? "Your data matters." : "Clear terms are part of a fair service."}</h2>
            <p>
              {privacy
                ? "Falaaa does not request mobile money PINs. Account, order, and contact data practices will be described here before any customer information is collected."
                : "This page is a placeholder. Service terms, payment conditions, delivery expectations, cancellations, and refund rules will be documented here before launch."}
            </p>
          </div>
        </div>
        <NoticeBanner title="Policy content is not final">
          This demonstration frontend does not collect or transmit customer information to a backend.
        </NoticeBanner>
      </div>
    </main>
  );
}
