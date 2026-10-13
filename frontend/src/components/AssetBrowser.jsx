export default function AssetBrowser({ assets, selectedAsset, busy, onOpen, onClose, onTicket }) {
  return (
    <section className="panel">
      <h2>Campus Assets</h2>
      <p className="subtitle">Shared campus inventory. Linked tickets follow your account permissions.</p>
      {assets.length === 0 ? <p>No assets are available.</p> : (
        <div className="asset-grid">
          {assets.map((asset) => (
            <button className="ticket-card" disabled={busy} key={asset.asset_id} onClick={() => onOpen(asset.asset_id)}>
              <strong>{asset.asset_name}</strong><span className="badge">{asset.status}</span>
              <p>{asset.asset_tag} · {asset.asset_type}</p><small>{asset.department_name || "No department"}</small>
            </button>
          ))}
        </div>
      )}
      {selectedAsset && (
        <article className="asset-detail">
          <div className="section-heading">
            <h3>{selectedAsset.asset.asset_name}</h3>
            <button className="secondary-button" onClick={onClose}>Close asset</button>
          </div>
          <dl className="detail-grid">
            {[["Asset tag","asset_tag"],["Type","asset_type"],["Status","status"],["Department","department_name"]].map(([label,key]) => (
              <div key={key}><dt>{label}</dt><dd>{selectedAsset.asset[key] || "None"}</dd></div>
            ))}
          </dl>
          <h4>Linked tickets visible to you</h4>
          {selectedAsset.tickets.length === 0 ? <p>No linked tickets are visible to your account.</p> : (
            <div className="ticket-list">
              {selectedAsset.tickets.map((ticket) => (
                <button disabled={busy} className="ticket-card" key={ticket.ticket_id} onClick={() => onTicket(ticket.ticket_id)}>
                  #{ticket.ticket_id} · {ticket.title} · {ticket.status.replaceAll("_", " ")}
                </button>
              ))}
            </div>
          )}
        </article>
      )}
    </section>
  );
}
