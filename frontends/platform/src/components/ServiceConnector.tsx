interface Props {
  selected: Set<string>;
  onToggle: (service: string) => void;
}

const SERVICES = [
  { id: "it", name: "IT Services", desc: "Helpdesk tickets, provisioning, access requests" },
  { id: "hr", name: "HR & People", desc: "Employee directory, onboarding, PTO" },
  { id: "finance", name: "Finance", desc: "Expenses, purchase orders, budgets" },
  { id: "engineering", name: "Engineering", desc: "Incidents, deployments, monitoring" },
  { id: "support", name: "Customer Support", desc: "Support tickets, account health" },
  { id: "compliance", name: "Compliance", desc: "Contracts, audits, policies" },
];

export default function ServiceConnector({ selected, onToggle }: Props) {
  return (
    <div>
      <div className="sidebar-section" style={{ padding: "0 0 8px" }}>
        Connect Services
      </div>
      <div className="service-grid">
        {SERVICES.map((svc) => {
          const active = selected.has(svc.id);
          return (
            <button
              key={svc.id}
              className={`service-toggle ${active ? "active" : ""}`}
              onClick={() => onToggle(svc.id)}
            >
              <div className="service-dot" />
              <div>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{svc.name}</div>
                <div style={{ fontSize: 10, opacity: 0.7, lineHeight: 1.3 }}>{svc.desc}</div>
              </div>
            </button>
          );
        })}
      </div>
      <div
        style={{
          marginTop: 12,
          fontSize: 11,
          color: "var(--text-tertiary)",
          textAlign: "center",
        }}
      >
        {selected.size} of {SERVICES.length} connected
      </div>
    </div>
  );
}
