import { useState } from "react";
import ITHelpdesk from "./components/ITHelpdesk";
import HRDashboard from "./components/HRDashboard";
import FinanceDashboard from "./components/FinanceDashboard";
import EngineeringDashboard from "./components/EngineeringDashboard";
import CustomerSupport from "./components/CustomerSupport";
import ComplianceDashboard from "./components/ComplianceDashboard";

type View = "it" | "hr" | "finance" | "engineering" | "customers" | "compliance";

const NAV: { id: View; label: string; icon: string }[] = [
  { id: "it", label: "IT Helpdesk", icon: "ticket" },
  { id: "hr", label: "HR & People", icon: "people" },
  { id: "finance", label: "Finance", icon: "finance" },
  { id: "engineering", label: "Engineering", icon: "engineering" },
  { id: "customers", label: "Customer Support", icon: "customers" },
  { id: "compliance", label: "Compliance", icon: "compliance" },
];

function NavIcon({ icon }: { icon: string }) {
  switch (icon) {
    case "ticket":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="2" y="3" width="12" height="10" rx="2" />
          <path d="M2 7h12" />
          <path d="M5 10h6" />
        </svg>
      );
    case "people":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="8" cy="5" r="2.5" />
          <path d="M3 14c0-2.8 2.2-5 5-5s5 2.2 5 5" />
        </svg>
      );
    case "finance":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 2v12M5 4.5C5 3.7 6.3 3 8 3s3 .7 3 1.5S9.7 6 8 6 5 6.7 5 7.5 6.3 9 8 9s3 .7 3 1.5S9.7 12 8 12s-3-.7-3-1.5" />
        </svg>
      );
    case "engineering":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M5.5 2L3 8l2.5 6M10.5 2L13 8l-2.5 6M9 2L7 14" />
        </svg>
      );
    case "customers":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M14 12.5c0-1.4-1.8-2.5-4-2.5-1 0-1.9.2-2.6.6M6 12.5c0-1.4-1.8-2.5-4-2.5" />
          <circle cx="10" cy="6" r="2" />
          <circle cx="4.5" cy="7.5" r="1.5" />
        </svg>
      );
    case "compliance":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="3" y="2" width="10" height="12" rx="1" />
          <path d="M6 6h4M6 8.5h4M6 11h2" />
        </svg>
      );
    default:
      return null;
  }
}

export default function App() {
  const [view, setView] = useState<View>("it");

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          NorthHill Corp <span>portal</span>
        </div>
        <div className="sidebar-section">Departments</div>
        {NAV.map((item) => (
          <div
            key={item.id}
            className={`sidebar-item ${view === item.id ? "active" : ""}`}
            onClick={() => setView(item.id)}
          >
            <NavIcon icon={item.icon} />
            {item.label}
          </div>
        ))}
        <div className="sidebar-footer">
          <div className="connection-status">
            <div className="connection-dot connected" />
            NorthHill Enterprise
          </div>
        </div>
      </nav>
      <main className="main-content">
        {view === "it" && <ITHelpdesk />}
        {view === "hr" && <HRDashboard />}
        {view === "finance" && <FinanceDashboard />}
        {view === "engineering" && <EngineeringDashboard />}
        {view === "customers" && <CustomerSupport />}
        {view === "compliance" && <ComplianceDashboard />}
      </main>
    </div>
  );
}
