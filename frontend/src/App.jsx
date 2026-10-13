import { useEffect, useState } from "react";
import "./App.css";
import { request } from "./api";
import Dashboard from "./components/Dashboard";
import AssetBrowser from "./components/AssetBrowser";
function App() {
  const [busy, setBusy] = useState("");
  const [sessionReady, setSessionReady] = useState(!localStorage.getItem("access_token"));
  const [lookupError, setLookupError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginMessage, setLoginMessage] = useState("");
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("user");
    if (!saved) {
      return null;
    }
    try {
      return JSON.parse(saved);
    } catch {
      return null;
    }
  });
  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [tickets, setTickets] = useState([]);
  const [ticketsError, setTicketsError] = useState("");
  const [technicians, setTechnicians] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [assets, setAssets] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [departmentId, setDepartmentId] = useState("");
  const [assetId, setAssetId] = useState("");
  const [ticketMessage, setTicketMessage] = useState("");
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [history, setHistory] = useState([]);
  const [detailsError, setDetailsError] = useState("");
  const [commentText, setCommentText] = useState("");
  const [commentMessage, setCommentMessage] = useState("");
  const [newStatus, setNewStatus] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [selectedTechnician, setSelectedTechnician] = useState("");
  const [assignmentMessage, setAssignmentMessage] = useState("");
  async function runAction(name, action) {
    setBusy(name);
    try { await action(); }
    finally { setBusy(""); }
  }
  async function loadDashboard(token = null) {
    try {
      setDashboard(await request("/dashboard/summary", { token }));
      setDashboardError("");
    } catch (error) { setDashboard(null); setDashboardError(error.message); }
  }
  async function loadTickets(token = null) {
    try {
      const data = await request("/tickets/", { token });
      setTickets(data.tickets);
      setTicketsError("");
    } catch (error) { setTickets([]); setTicketsError(error.message); }
  }
  async function loadLookups(token = null) {
    try {
      const [departmentData, assetData] = await Promise.all([
        request("/lookups/departments", { token }), request("/assets/", { token }),
      ]);
      setDepartments(departmentData.departments);
      setAssets(assetData.assets);
      if (JSON.parse(localStorage.getItem("user") || "{}").role === "ADMIN") {
        const data = await request("/technicians/", { token });
        setTechnicians(data.technicians);
      }
      setLookupError("");
    } catch (error) { setLookupError(error.message); }
  }
  async function refreshAll(token = null) {
    await Promise.all([loadDashboard(token), loadTickets(token), loadLookups(token)]);
  }
  useEffect(() => {
    const controller = new AbortController();
    const expire = () => {
      handleLogout();
      setLoginMessage("Your session expired. Please sign in again.");
    };
    window.addEventListener("session-expired", expire);
    async function restore() {
      const token = localStorage.getItem("access_token");
      if (!token) { handleLogout(); return; }
      try {
        const data = await request("/auth/me", { token });
        if (controller.signal.aborted) return;
        const identity = { ...data.user, role: data.user.role_name };
        localStorage.setItem("user", JSON.stringify(identity));
        setUser(identity);
        await refreshAll(token);
      } catch (error) {
        if (!controller.signal.aborted) {
          handleLogout();
          setLoginMessage(error.message);
        }
      } finally {
        if (!controller.signal.aborted) setSessionReady(true);
      }
    }
    restore();
    return () => {
      controller.abort();
      window.removeEventListener("session-expired", expire);
    };
    // Initialize once; current identity is always checked with the server.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  async function handleLogin(event) {
    event.preventDefault();
    setLoginMessage("");
    await runAction("login", async () => {
      try {
        const data = await request("/auth/login", {
          method: "POST", publicRequest: true,
          body: new URLSearchParams({ username: email.trim(), password }),
        });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        setUser(data.user);
        setEmail(""); setPassword("");
        await refreshAll(data.access_token);
      } catch (error) { setLoginMessage(error.message); }
    });
  }
  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null); setDashboard(null); setTickets([]);
    setTechnicians([]); setDepartments([]); setAssets([]);
    setSelectedTicket(null); setSelectedAsset(null);
    setComments([]); setHistory([]);
    setLoginMessage(""); setTicketMessage(""); setCommentMessage("");
    setStatusMessage(""); setAssignmentMessage(""); setLookupError("");
    setTitle(""); setDescription(""); setCategory(""); setPriority("MEDIUM");
    setDepartmentId(""); setAssetId(""); setCommentText("");
    setSearch(""); setStatusFilter(""); setPriorityFilter("");
    setDetailsError(""); setTicketsError(""); setDashboardError("");
    setSessionReady(true);
  }
  async function createTicket(event) {
    event.preventDefault();
    setTicketMessage("");
    await runAction("create", async () => {
      try {
        await request("/tickets/", { method: "POST", body: {
          title, description, category, priority,
          department_id: departmentId ? Number(departmentId) : null,
          asset_id: assetId ? Number(assetId) : null,
        }});
        setTitle(""); setDescription(""); setCategory(""); setPriority("MEDIUM");
        setDepartmentId(""); setAssetId("");
        setTicketMessage("Ticket created successfully.");
        await Promise.all([loadTickets(), loadDashboard()]);
      } catch (error) { setTicketMessage(error.message); }
    });
  }
  async function loadTicket(ticketId) {
    const [ticketData, commentData, historyData] = await Promise.all([
      request(`/tickets/${ticketId}`), request(`/tickets/${ticketId}/comments`),
      request(`/tickets/${ticketId}/history`),
    ]);
    setSelectedTicket(ticketData.ticket);
    setComments(commentData.comments); setHistory(historyData.history);
    setNewStatus(ticketData.ticket.status); setSelectedTechnician("");
  }
  async function openTicket(ticketId) {
    setDetailsError(""); setCommentMessage(""); setStatusMessage(""); setAssignmentMessage("");
    setSelectedTicket(null); setSelectedAsset(null);
    await runAction("details", async () => {
      try { await loadTicket(ticketId); }
      catch (error) { setDetailsError(error.message); }
    });
  }
  async function addComment(event) {
    event.preventDefault();
    if (!selectedTicket) return;
    await runAction("comment", async () => {
      try {
        await request(`/tickets/${selectedTicket.ticket_id}/comments`, {
          method: "POST", body: { comment_text: commentText },
        });
        setCommentText("");
        await loadTicket(selectedTicket.ticket_id);
        setCommentMessage("Comment added successfully.");
      } catch (error) { setCommentMessage(error.message); }
    });
  }
  async function updateStatus(event) {
    event.preventDefault();
    if (!selectedTicket) return;
    await runAction("status", async () => {
      try {
        const data = await request(`/tickets/${selectedTicket.ticket_id}/status`, {
          method: "PUT", body: { new_status: newStatus },
        });
        await loadTicket(selectedTicket.ticket_id);
        await Promise.all([loadTickets(), loadDashboard()]);
        setStatusMessage(data.message);
      } catch (error) { setStatusMessage(error.message); }
    });
  }
  async function assignTechnician(event) {
    event.preventDefault();
    if (!selectedTicket || !selectedTechnician) return;
    await runAction("assign", async () => {
      try {
        await request(`/tickets/${selectedTicket.ticket_id}/assign`, {
          method: "POST", body: { technician_id: Number(selectedTechnician) },
        });
        await loadTicket(selectedTicket.ticket_id);
        await Promise.all([loadTickets(), loadDashboard()]);
        setAssignmentMessage("Technician assigned successfully.");
      } catch (error) { setAssignmentMessage(error.message); }
    });
  }
  async function openAsset(assetId) {
    setDetailsError(""); setSelectedAsset(null);
    await runAction("asset", async () => {
      try { setSelectedAsset(await request(`/assets/${assetId}`)); }
      catch (error) { setDetailsError(error.message); }
    });
  }
  const visibleTickets = tickets.filter((ticket) => {
    const matchesSearch = [ticket.title, ticket.ticket_id, ticket.category, ticket.requester,
      ticket.department_name, ticket.asset_name].some((value) =>
      String(value ?? "").toLowerCase().includes(search.toLowerCase().trim()));
    return matchesSearch && (!statusFilter || ticket.status === statusFilter) &&
      (!priorityFilter || ticket.priority === priorityFilter);
  });
  const allowedStatuses = selectedTicket ? [selectedTicket.status, ...({
    OPEN: ["IN_PROGRESS"], IN_PROGRESS: ["OPEN", "RESOLVED"],
    RESOLVED: ["IN_PROGRESS", "CLOSED"], CLOSED: user.role === "ADMIN" ? ["OPEN"] : [],
  }[selectedTicket.status] || [])] : [];
  const filteredAssets =
    departmentId
      ? assets.filter(
          (asset) =>
            String(
              asset.department_id
            ) ===
            String(
              departmentId
            )
        )
      : assets;
  if (!sessionReady) return <main className="login-page"><p role="status">Restoring your session...</p></main>;
  if (!user) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1>
            Campus ServiceDesk
          </h1>
          <p className="subtitle">
            IT Support & Asset Management
          </p>
          <h2>
            Login
          </h2>
          <form
            onSubmit={handleLogin}
          >
            <label htmlFor="email">
              Email
            </label>
            <input autoComplete="username" id="email" aria-label="email"
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(
                  event.target.value
                )
              }
              placeholder=
                "admin@example.com"
              required
            />
            <label htmlFor="password">
              Password
            </label>
            <input autoComplete="current-password" id="password" aria-label="password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
              required
            />
            <button type="submit" disabled={Boolean(busy)}>
              {busy === "login" ? "Signing in..." : "Login"}
            </button>
          </form>
          {loginMessage && (
            <p role="alert" className="message error">
              {loginMessage}
            </p>
          )}
        </div>
      </div>
    );
  }
  if (selectedTicket) {
    return (
      <div className="app">
        <header className="topbar">
          <div>
            <h1>
              Campus ServiceDesk
            </h1>
            <p>
              Logged in as{" "}
              {user.full_name}
              {" "}
              ({user.role})
            </p>
          </div>
          <button disabled={Boolean(busy)}
            className=
              "secondary-button"
            onClick=
              {handleLogout}
          >
            Logout
          </button>
        </header>
        <main className="content">
          <p className="activity" role="status" aria-live="polite">{busy ? "Working..." : ""}</p>
          {lookupError && <p role="alert" className="message error">{lookupError}</p>}
          <button disabled={Boolean(busy)}
            className=
              "secondary-button"
            onClick={() =>
              setSelectedTicket(null)
            }
          >
            ← Back to Tickets
          </button>
          <section
            className=
              "panel ticket-detail"
          >
            <h2>
              {selectedTicket.title}
            </h2>
            <div className="detail-grid">
              <div>
                <strong>
                  Ticket ID
                </strong>
                <span>
                  {
                    selectedTicket
                    .ticket_id
                  }
                </span>
              </div>
              <div>
                <strong>
                  Status
                </strong>
                <span>
                  {
                    selectedTicket
                    .status
                  }
                </span>
              </div>
              <div>
                <strong>
                  Priority
                </strong>
                <span>
                  {
                    selectedTicket
                    .priority
                  }
                </span>
              </div>
              <div>
                <strong>
                  Category
                </strong>
                <span>
                  {
                    selectedTicket
                    .category
                  }
                </span>
              </div>
              <div>
                <strong>
                  Requester
                </strong>
                <span>
                  {
                    selectedTicket
                    .requester ||
                    "Unknown"
                  }
                </span>
              </div>
              <div>
                <strong>
                  Department
                </strong>
                <span>
                  {
                    selectedTicket
                    .department_name ||
                    "None"
                  }
                </span>
              </div>
              <div>
                <strong>
                  Asset
                </strong>
                <span>
                  {
                    selectedTicket
                    .asset_name ||
                    "None"
                  }
                </span>
              </div>
              <div>
                <strong>
                  Technician
                </strong>
                <span>
                  {
                    selectedTicket
                    .assigned_technician ||
                    "Unassigned"
                  }
                </span>
              </div>
            </div>
            <h3>
              Description
            </h3>
            <p>
              {
                selectedTicket
                .description ||
                "No description available."
              }
            </p>
          </section>
          {user.role === "ADMIN" && (
            <section className="panel">
              <h2>
                Assign Technician
              </h2>
              <form
                className="inline-form"
                onSubmit=
                  {assignTechnician}
              >
                <select id="technician" aria-label="technician"
                  value=
                    {selectedTechnician}
                  onChange={(event) =>
                    setSelectedTechnician(
                      event.target.value
                    )
                  }
                  required
                >
                  <option value="">
                    Select technician
                  </option>
                  {technicians.map(
                    (technician) => (
                      <option
                        key={
                          technician
                          .technician_id
                        }
                        value={
                          technician
                          .technician_id
                        }
                        disabled={
                          !technician
                          .is_available
                        }
                      >
                        {
                          technician
                          .full_name
                        }
                        {
                          technician
                          .specialization
                            ? ` - ${
                                technician
                                .specialization
                              }`
                            : ""
                        }
                        {
                          !technician
                          .is_available
                            ? " (Unavailable)"
                            : ""
                        }
                      </option>
                    )
                  )}
                </select>
                <button type="submit" disabled={Boolean(busy)}>
                  Assign Technician
                </button>
              </form>
              {assignmentMessage && (
                <p role="status" className="message">
                  {assignmentMessage}
                </p>
              )}
            </section>
          )}
          {(
            user.role === "ADMIN" ||
            user.role === "TECHNICIAN"
          ) && (
            <section className="panel">
              <h2>
                Update Status
              </h2>
              <form
                className="inline-form"
                onSubmit=
                  {updateStatus}
              >
                <select id="workflow-status" aria-label="workflow status"
                  value={newStatus}
                  onChange={(event) =>
                    setNewStatus(
                      event.target.value
                    )
                  }
                >
                  {allowedStatuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
                </select>
                <button type="submit" disabled={Boolean(busy)}>
                  Update Status
                </button>
              </form>
              {statusMessage && (
                <p role="status" className="message">
                  {statusMessage}
                </p>
              )}
            </section>
          )}
          <section className="panel">
            <h2>
              Comments
            </h2>
            {comments.length === 0 ? (
              <p>
                No comments yet.
              </p>
            ) : (
              <div className="comments">
                {comments.map(
                  (comment) => (
                    <div
                      className="comment"
                      key={
                        comment.comment_id
                      }
                    >
                      <strong>
                        {
                          comment
                          .commented_by ||
                          "Unknown User"
                        }
                      </strong>
                      <p>
                        {
                          comment
                          .comment_text
                        }
                      </p>
                      <small>
                        {
                          comment
                          .created_at ||
                          ""
                        }
                      </small>
                    </div>
                  )
                )}
              </div>
            )}
            <form
              className="comment-form"
              onSubmit=
                {addComment}
            >
              <textarea minLength={2} maxLength={1000} required id="comment" aria-label="comment"
                value={commentText}
                onChange={(event) =>
                  setCommentText(
                    event.target.value
                  )
                }
                placeholder=
                  "Add a comment..."
                required
              />
              <button type="submit" disabled={Boolean(busy)}>
                Add Comment
              </button>
            </form>
            {commentMessage && (
              <p role="status" className="message">
                {commentMessage}
              </p>
            )}
          </section>
          <section className="panel">
            <h2>
              Status History
            </h2>
            {history.length === 0 ? (
              <p>
                No status history available.
              </p>
            ) : (
              <div className="history-list">
                {history.map(
                  (item) => (
                    <div
                      className="history-item"
                      key={
                        item.history_id
                      }
                    >
                      <strong>
                        {item.old_status}
                        {" → "}
                        {item.new_status}
                      </strong>
                      <span>
                        Changed by:{" "}
                        {
                          item.changed_by ||
                          "Unknown"
                        }
                      </span>
                      <small>
                        {
                          item.changed_at ||
                          ""
                        }
                      </small>
                    </div>
                  )
                )}
              </div>
            )}
          </section>
          {detailsError && (
            <p role="alert" className="message error">
              {detailsError}
            </p>
          )}
        </main>
      </div>
    );
  }
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>
            Campus ServiceDesk
          </h1>
          <p>
            Welcome,{" "}
            {user.full_name}
            {" · "}
            {user.role}
          </p>
        </div>
        <div className="header-actions">
          <button disabled={Boolean(busy)}
            className=
              "secondary-button"
            onClick={() =>
              runAction("refresh", () => refreshAll())
            }
          >
            Refresh
          </button>
          <button disabled={Boolean(busy)}
            className=
              "secondary-button"
            onClick=
              {handleLogout}
          >
            Logout
          </button>
        </div>
      </header>
      <main className="content">
          <p className="activity" role="status" aria-live="polite">{busy ? "Working..." : ""}</p>
          {lookupError && <p role="alert" className="message error">{lookupError}</p>}
        <Dashboard dashboard={dashboard} role={user.role} error={dashboardError} busy={Boolean(busy)} onRefresh={() => runAction("refresh", () => loadDashboard())} />
        <section className="panel">
          <h2>
            Create Ticket
          </h2>
          <form
            className="ticket-form"
            onSubmit=
              {createTicket}
          >
            <label htmlFor="title">
              Title
            </label>
            <input minLength={3} maxLength={150} id="title" aria-label="title"
              type="text"
              value={title}
              onChange={(event) =>
                setTitle(
                  event.target.value
                )
              }
              placeholder=
                "Brief description of the issue"
              required
            />
            <label htmlFor="description">
              Description
            </label>
            <textarea minLength={5} maxLength={2000} id="description" aria-label="description"
              value={description}
              onChange={(event) =>
                setDescription(
                  event.target.value
                )
              }
              placeholder=
                "Describe the issue..."
              required
            />
            <div className="form-row">
              <div>
                <label htmlFor="category">
                  Category
                </label>
                <select id="category" aria-label="category"
                  value={category}
                  onChange={(event) =>
                    setCategory(
                      event.target.value
                    )
                  }
                  required
                >
                  <option value="">
                    Select category
                  </option>
                  <option value="Hardware">
                    Hardware
                  </option>
                  <option value="Software">
                    Software
                  </option>
                  <option value="Network">
                    Network
                  </option>
                  <option value="Access">
                    Access
                  </option>
                  <option value="Other">
                    Other
                  </option>
                </select>
              </div>
              <div>
                <label htmlFor="priority">
                  Priority
                </label>
                <select id="priority" aria-label="priority"
                  value={priority}
                  onChange={(event) =>
                    setPriority(
                      event.target.value
                    )
                  }
                >
                  <option value="LOW">
                    LOW
                  </option>
                  <option value="MEDIUM">
                    MEDIUM
                  </option>
                  <option value="HIGH">
                    HIGH
                  </option>
                  <option value="CRITICAL">
                    CRITICAL
                  </option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div>
                <label htmlFor="department">
                  Department
                </label>
                <select id="department" aria-label="department"
                  value={departmentId}
                  onChange={(event) => {
                    setDepartmentId(
                      event.target.value
                    );
                    setAssetId("");
                  }}
                >
                  <option value="">
                    No department
                  </option>
                  {departments.map(
                    (department) => (
                      <option
                        key={
                          department
                          .department_id
                        }
                        value={
                          department
                          .department_id
                        }
                      >
                        {
                          department
                          .department_name
                        }
                      </option>
                    )
                  )}
                </select>
              </div>
              <div>
                <label htmlFor="asset">
                  Asset
                </label>
                <select id="asset" aria-label="asset"
                  value={assetId}
                  onChange={(event) =>
                    setAssetId(
                      event.target.value
                    )
                  }
                >
                  <option value="">
                    No asset
                  </option>
                  {filteredAssets.map(
                    (asset) => (
                      <option
                        key={
                          asset.asset_id
                        }
                        value={
                          asset.asset_id
                        }
                      >
                        {
                          asset.asset_name
                        }
                      </option>
                    )
                  )}
                </select>
              </div>
            </div>
            <button type="submit" disabled={Boolean(busy)}>
              Create Ticket
            </button>
          </form>
          {ticketMessage && (
            <p role="status" className="message">
              {ticketMessage}
            </p>
          )}
        </section>
        {detailsError && <p role="alert" className="message error">{detailsError}</p>}
        <section className="panel">
          <div className="section-heading">
            <h2>
              Tickets
            </h2>
            <button disabled={Boolean(busy)}
              onClick={() =>
                runAction("refresh", () => loadTickets())
              }
            >
              Refresh Tickets
            </button>
          </div>
          {ticketsError && (
            <p role="alert" className="message error">
              {ticketsError}
            </p>
          )}
          <div className="filters">
            <label>Search tickets<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Title, ID, requester or asset" /></label>
            <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{["OPEN","IN_PROGRESS","RESOLVED","CLOSED"].map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
            <label>Priority<select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="">All priorities</option>{["LOW","MEDIUM","HIGH","CRITICAL"].map((priority) => <option key={priority}>{priority}</option>)}</select></label>
          </div>
          <p className="subtitle">{visibleTickets.length} visible tickets</p>
          {visibleTickets.length === 0 ? (
            <p>
              No tickets match your filters. Create a ticket or adjust the filters.
            </p>
          ) : (
            <div className="ticket-list">
              {visibleTickets.map(
                (ticket) => (
                  <button disabled={Boolean(busy)}
                    className="ticket-card"
                    key={
                      ticket.ticket_id
                    }
                    onClick={() =>
                      openTicket(
                        ticket.ticket_id
                      )
                    }
                  >
                    <div
                      className=
                        "ticket-card-header"
                    >
                      <h3>
                        {ticket.title}
                      </h3>
                      <span>
                        #{ticket.ticket_id}
                      </span>
                    </div>
                    <div className="ticket-meta">
                      <span>
                        Status:{" "}
                        <span className={`badge status-${ticket.status}`}>{ticket.status.replaceAll("_", " ")}</span>
                      </span>
                      <span>
                        Priority:{" "}
                        <span className={`badge priority-${ticket.priority}`}>{ticket.priority}</span>
                      </span>
                      <span>
                        Category:{" "}
                        {ticket.category}
                      </span>
                      <span>
                        Requester:{" "}
                        {
                          ticket.requester ||
                          "Unknown"
                        }
                      </span>
                    </div>
                  </button>
                )
              )}
            </div>
          )}
        </section>
        <AssetBrowser assets={assets} selectedAsset={selectedAsset} busy={Boolean(busy)} onOpen={openAsset} onClose={() => setSelectedAsset(null)} onTicket={openTicket} />
      </main>
    </div>
  );
}
export default App;
