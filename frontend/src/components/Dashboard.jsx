export default function Dashboard({ dashboard, role, error, busy, onRefresh }) {
  const title = role === "ADMIN" ? "All Tickets" : role === "TECHNICIAN" ? "Assigned to Me" : "My Tickets";
  const cards = [
    [title, "total_tickets"], ["Open", "open_tickets"],
    ["In Progress", "in_progress_tickets"], ["Resolved", "resolved_tickets"],
    ["High / Critical", "high_priority_tickets"], ["Unassigned", "unassigned_tickets"],
  ];
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Dashboard</h2>
        <button disabled={busy} onClick={onRefresh}>Refresh Dashboard</button>
      </div>
      {error && <p role="alert" className="message error">{error}</p>}
      {dashboard ? <>
        <p className="subtitle">{dashboard.scope}</p>
        <div className="dashboard-grid">
          {cards.map(([label, key]) => (
            <div className="stat-card" key={key}><span>{label}</span><strong>{dashboard[key]}</strong></div>
          ))}
        </div>
      </> : <p>Dashboard statistics are unavailable. Refresh to try again.</p>}
    </section>
  );
}
