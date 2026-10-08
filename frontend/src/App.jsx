import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginMessage, setLoginMessage] = useState("");

  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      return null;
    }

    try {
      return JSON.parse(savedUser);
    } catch {
      return null;
    }
  });

  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState("");

  const [tickets, setTickets] = useState([]);
  const [ticketsError, setTicketsError] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [ticketMessage, setTicketMessage] = useState("");

  const [selectedTicket, setSelectedTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [history, setHistory] = useState([]);
  const [detailsError, setDetailsError] = useState("");

  const [commentText, setCommentText] = useState("");
  const [commentMessage, setCommentMessage] = useState("");

  const [newStatus, setNewStatus] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const [technicians, setTechnicians] = useState([]);
  const [selectedTechnician, setSelectedTechnician] = useState("");
  const [assignmentMessage, setAssignmentMessage] = useState("");

  function getToken() {
    return localStorage.getItem("access_token");
  }

  function authHeaders(token = null) {
    return {
      Authorization: `Bearer ${token || getToken()}`,
    };
  }

  async function handleLogin(event) {
    event.preventDefault();

    setLoginMessage("");

    const formData = new URLSearchParams();

    formData.append("username", email);
    formData.append("password", password);

    try {
      const response = await fetch(
        `${API_URL}/auth/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setLoginMessage(
          data.detail || "Login failed."
        );
        return;
      }

      localStorage.setItem(
        "access_token",
        data.access_token
      );

      localStorage.setItem(
        "user",
        JSON.stringify(data.user)
      );

      setUser(data.user);

      setEmail("");
      setPassword("");

      await loadDashboard(data.access_token);
      await loadTickets(data.access_token);
      await loadTechnicians(data.access_token);
    } catch {
      setLoginMessage(
        "Could not connect to the backend."
      );
    }
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");

    setUser(null);

    setDashboard(null);
    setTickets([]);

    setSelectedTicket(null);
    setComments([]);
    setHistory([]);

    setTechnicians([]);
    setSelectedTechnician("");

    setLoginMessage("");
    setTicketMessage("");
    setCommentMessage("");
    setStatusMessage("");
    setAssignmentMessage("");
  }

  async function loadDashboard(optionalToken = null) {
    const token = optionalToken || getToken();

    try {
      const response = await fetch(
        `${API_URL}/dashboard/summary`,
        {
          headers: authHeaders(token),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setDashboardError(
          "Could not load dashboard."
        );
        return;
      }

      setDashboard(data);
      setDashboardError("");
    } catch {
      setDashboardError(
        "Could not connect to the backend."
      );
    }
  }

  async function loadTickets(optionalToken = null) {
    const token = optionalToken || getToken();

    try {
      const response = await fetch(
        `${API_URL}/tickets/`,
        {
          headers: authHeaders(token),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setTicketsError(
          "Could not load tickets."
        );
        return;
      }

      setTickets(data.tickets || []);
      setTicketsError("");
    } catch {
      setTicketsError(
        "Could not connect to the backend."
      );
    }
  }

  async function loadTechnicians(
    optionalToken = null
  ) {
    const token = optionalToken || getToken();

    try {
      const response = await fetch(
        `${API_URL}/technicians/`,
        {
          headers: authHeaders(token),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        return;
      }

      setTechnicians(
        data.technicians || []
      );
    } catch {
      console.log(
        "Could not load technicians."
      );
    }
  }

  async function createTicket(event) {
    event.preventDefault();

    setTicketMessage("");

    const newTicket = {
      title,
      description,
      category,
      priority,
      department_id: null,
      asset_id: null,
    };

    try {
      const response = await fetch(
        `${API_URL}/tickets/`,
        {
          method: "POST",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify(newTicket),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        if (data.detail) {
          setTicketMessage(
            typeof data.detail === "string"
              ? data.detail
              : "Please check the entered values."
          );
        } else {
          setTicketMessage(
            "Could not create ticket."
          );
        }

        return;
      }

      setTicketMessage(
        "Ticket created successfully."
      );

      setTitle("");
      setDescription("");
      setCategory("");
      setPriority("MEDIUM");

      await loadTickets();
      await loadDashboard();
    } catch {
      setTicketMessage(
        "Could not connect to the backend."
      );
    }
  }

  async function openTicket(ticketId) {
    setDetailsError("");
    setCommentMessage("");
    setStatusMessage("");
    setAssignmentMessage("");

    await loadTechnicians();

    try {
      const headers = authHeaders();

      const [
        ticketResponse,
        commentsResponse,
        historyResponse,
      ] = await Promise.all([
        fetch(
          `${API_URL}/tickets/${ticketId}`,
          { headers }
        ),

        fetch(
          `${API_URL}/tickets/${ticketId}/comments`,
          { headers }
        ),

        fetch(
          `${API_URL}/tickets/${ticketId}/history`,
          { headers }
        ),
      ]);

      if (!ticketResponse.ok) {
        setDetailsError(
          "Could not load ticket details."
        );
        return;
      }

      const ticketData =
        await ticketResponse.json();

      const commentsData =
        commentsResponse.ok
          ? await commentsResponse.json()
          : { comments: [] };

      const historyData =
        historyResponse.ok
          ? await historyResponse.json()
          : { history: [] };

      const ticket =
        ticketData.ticket || ticketData;

      setSelectedTicket(ticket);

      setComments(
        commentsData.comments || []
      );

      setHistory(
        historyData.history || []
      );

      setNewStatus(
        ticket.status || ""
      );

      setSelectedTechnician("");
    } catch {
      setDetailsError(
        "Could not connect to the backend."
      );
    }
  }

  async function addComment(event) {
    event.preventDefault();

    if (!selectedTicket) {
      return;
    }

    setCommentMessage("");

    try {
      const response = await fetch(
        `${API_URL}/tickets/${selectedTicket.ticket_id}/comments`,
        {
          method: "POST",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            comment_text: commentText,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setCommentMessage(
          typeof data.detail === "string"
            ? data.detail
            : "Could not add comment."
        );

        return;
      }

      setCommentText("");

      setCommentMessage(
        "Comment added successfully."
      );

      await openTicket(
        selectedTicket.ticket_id
      );
    } catch {
      setCommentMessage(
        "Could not connect to the backend."
      );
    }
  }

  async function updateStatus(event) {
    event.preventDefault();

    if (!selectedTicket) {
      return;
    }

    setStatusMessage("");

    try {
      const response = await fetch(
        `${API_URL}/tickets/${selectedTicket.ticket_id}/status`,
        {
          method: "PUT",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            new_status: newStatus,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setStatusMessage(
          typeof data.detail === "string"
            ? data.detail
            : "Could not update status."
        );

        return;
      }

      setStatusMessage(
        "Status updated successfully."
      );

      await openTicket(
        selectedTicket.ticket_id
      );

      await loadTickets();
      await loadDashboard();
    } catch {
      setStatusMessage(
        "Could not connect to the backend."
      );
    }
  }

  async function assignTechnician(event) {
    event.preventDefault();

    if (
      !selectedTicket ||
      !selectedTechnician
    ) {
      setAssignmentMessage(
        "Please select a technician."
      );
      return;
    }

    setAssignmentMessage("");

    try {
      const response = await fetch(
        `${API_URL}/tickets/${selectedTicket.ticket_id}/assign`,
        {
          method: "POST",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            technician_id:
              Number(selectedTechnician),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setAssignmentMessage(
          typeof data.detail === "string"
            ? data.detail
            : "Could not assign technician."
        );

        return;
      }

      setAssignmentMessage(
        "Technician assigned successfully."
      );

      setSelectedTechnician("");

      await openTicket(
        selectedTicket.ticket_id
      );

      await loadTickets();
      await loadDashboard();
    } catch {
      setAssignmentMessage(
        "Could not connect to the backend."
      );
    }
  }

  async function refreshAll() {
    await loadDashboard();
    await loadTickets();
    await loadTechnicians();
  }

  if (!user) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1>Campus ServiceDesk</h1>

          <p className="subtitle">
            IT Support & Asset Management
          </p>

          <h2>Login</h2>

          <form onSubmit={handleLogin}>
            <label>Email</label>

            <input
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              placeholder="admin@example.com"
              required
            />

            <label>Password</label>

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              required
            />

            <button type="submit">
              Login
            </button>
          </form>

          {loginMessage && (
            <p className="message error">
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
            <h1>Campus ServiceDesk</h1>

            <p>
              Logged in as{" "}
              {user.full_name} ({user.role})
            </p>
          </div>

          <button
            className="secondary-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </header>

        <main className="content">
          <button
            className="secondary-button"
            onClick={() =>
              setSelectedTicket(null)
            }
          >
            ← Back to Tickets
          </button>

          <section className="panel ticket-detail">
            <h2>
              {selectedTicket.title}
            </h2>

            <div className="detail-grid">
              <div>
                <strong>
                  Ticket ID
                </strong>

                <span>
                  {selectedTicket.ticket_id}
                </span>
              </div>

              <div>
                <strong>Status</strong>

                <span>
                  {selectedTicket.status}
                </span>
              </div>

              <div>
                <strong>Priority</strong>

                <span>
                  {selectedTicket.priority}
                </span>
              </div>

              <div>
                <strong>Category</strong>

                <span>
                  {selectedTicket.category}
                </span>
              </div>

              <div>
                <strong>Requester</strong>

                <span>
                  {selectedTicket.requester ||
                    "Unknown"}
                </span>
              </div>

              <div>
                <strong>
                  Department
                </strong>

                <span>
                  {selectedTicket.department_name ||
                    "None"}
                </span>
              </div>

              <div>
                <strong>Asset</strong>

                <span>
                  {selectedTicket.asset_name ||
                    "None"}
                </span>
              </div>

              <div>
                <strong>
                  Technician
                </strong>

                <span>
                  {selectedTicket.assigned_technician ||
                    "Unassigned"}
                </span>
              </div>
            </div>

            <h3>Description</h3>

            <p>
              {selectedTicket.description ||
                "No description available."}
            </p>
          </section>

          {user.role === "ADMIN" && (
            <section className="panel">
              <h2>
                Assign Technician
              </h2>

              <form
                className="inline-form"
                onSubmit={
                  assignTechnician
                }
              >
                <select
                  value={
                    selectedTechnician
                  }
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
                          technician.technician_id
                        }
                        value={
                          technician.technician_id
                        }
                        disabled={
                          !technician.is_available
                        }
                      >
                        {
                          technician.full_name
                        }

                        {technician.specialization
                          ? ` - ${technician.specialization}`
                          : ""}

                        {!technician.is_available
                          ? " (Unavailable)"
                          : ""}
                      </option>
                    )
                  )}
                </select>

                <button type="submit">
                  Assign Technician
                </button>
              </form>

              {assignmentMessage && (
                <p className="message">
                  {assignmentMessage}
                </p>
              )}
            </section>
          )}

          {(user.role === "ADMIN" ||
            user.role ===
              "TECHNICIAN") && (
            <section className="panel">
              <h2>Update Status</h2>

              <form
                className="inline-form"
                onSubmit={updateStatus}
              >
                <select
                  value={newStatus}
                  onChange={(event) =>
                    setNewStatus(
                      event.target.value
                    )
                  }
                >
                  <option value="OPEN">
                    OPEN
                  </option>

                  <option value="IN_PROGRESS">
                    IN_PROGRESS
                  </option>

                  <option value="RESOLVED">
                    RESOLVED
                  </option>

                  <option value="CLOSED">
                    CLOSED
                  </option>
                </select>

                <button type="submit">
                  Update Status
                </button>
              </form>

              {statusMessage && (
                <p className="message">
                  {statusMessage}
                </p>
              )}
            </section>
          )}

          <section className="panel">
            <h2>Comments</h2>

            {comments.length === 0 ? (
              <p>No comments yet.</p>
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
                        {comment.commented_by ||
                          "Unknown User"}
                      </strong>

                      <p>
                        {
                          comment.comment_text
                        }
                      </p>

                      <small>
                        {comment.created_at ||
                          ""}
                      </small>
                    </div>
                  )
                )}
              </div>
            )}

            <form
              className="comment-form"
              onSubmit={addComment}
            >
              <textarea
                value={commentText}
                onChange={(event) =>
                  setCommentText(
                    event.target.value
                  )
                }
                placeholder="Add a comment..."
                required
              />

              <button type="submit">
                Add Comment
              </button>
            </form>

            {commentMessage && (
              <p className="message">
                {commentMessage}
              </p>
            )}
          </section>

          <section className="panel">
            <h2>Status History</h2>

            {history.length === 0 ? (
              <p>
                No status history available.
              </p>
            ) : (
              <div className="history-list">
                {history.map((item) => (
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
                      {item.changed_by ||
                        "Unknown"}
                    </span>

                    <small>
                      {item.changed_at ||
                        ""}
                    </small>
                  </div>
                ))}
              </div>
            )}
          </section>

          {detailsError && (
            <p className="message error">
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
            Welcome, {user.full_name} ·{" "}
            {user.role}
          </p>
        </div>

        <div className="header-actions">
          <button
            className="secondary-button"
            onClick={refreshAll}
          >
            Refresh
          </button>

          <button
            className="secondary-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </header>

      <main className="content">
        <section className="panel">
          <div className="section-heading">
            <h2>Dashboard</h2>

            <button
              onClick={() =>
                loadDashboard()
              }
            >
              Load Dashboard
            </button>
          </div>

          {dashboardError && (
            <p className="message error">
              {dashboardError}
            </p>
          )}

          {dashboard ? (
            <div className="dashboard-grid">
              <div className="stat-card">
                <span>
                  Total Tickets
                </span>

                <strong>
                  {
                    dashboard.total_tickets
                  }
                </strong>
              </div>

              <div className="stat-card">
                <span>Open</span>

                <strong>
                  {
                    dashboard.open_tickets
                  }
                </strong>
              </div>

              <div className="stat-card">
                <span>
                  In Progress
                </span>

                <strong>
                  {
                    dashboard.in_progress_tickets
                  }
                </strong>
              </div>

              <div className="stat-card">
                <span>
                  Resolved
                </span>

                <strong>
                  {
                    dashboard.resolved_tickets
                  }
                </strong>
              </div>

              <div className="stat-card">
                <span>
                  High Priority
                </span>

                <strong>
                  {
                    dashboard.high_priority_tickets
                  }
                </strong>
              </div>

              <div className="stat-card">
                <span>
                  Unassigned
                </span>

                <strong>
                  {
                    dashboard.unassigned_tickets
                  }
                </strong>
              </div>
            </div>
          ) : (
            <p>
              Click Load Dashboard to
              retrieve current statistics.
            </p>
          )}
        </section>

        <section className="panel">
          <h2>Create Ticket</h2>

          <form
            className="ticket-form"
            onSubmit={createTicket}
          >
            <label>Title</label>

            <input
              type="text"
              value={title}
              onChange={(event) =>
                setTitle(
                  event.target.value
                )
              }
              placeholder="Brief description of the issue"
              required
            />

            <label>
              Description
            </label>

            <textarea
              value={description}
              onChange={(event) =>
                setDescription(
                  event.target.value
                )
              }
              placeholder="Describe the issue..."
              required
            />

            <div className="form-row">
              <div>
                <label>
                  Category
                </label>

                <input
                  type="text"
                  value={category}
                  onChange={(event) =>
                    setCategory(
                      event.target.value
                    )
                  }
                  placeholder="Hardware, Network..."
                  required
                />
              </div>

              <div>
                <label>
                  Priority
                </label>

                <select
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

            <button type="submit">
              Create Ticket
            </button>
          </form>

          {ticketMessage && (
            <p className="message">
              {ticketMessage}
            </p>
          )}
        </section>

        <section className="panel">
          <div className="section-heading">
            <h2>Tickets</h2>

            <button
              onClick={() =>
                loadTickets()
              }
            >
              Load Tickets
            </button>
          </div>

          {ticketsError && (
            <p className="message error">
              {ticketsError}
            </p>
          )}

          {tickets.length === 0 ? (
            <p>No tickets loaded.</p>
          ) : (
            <div className="ticket-list">
              {tickets.map(
                (ticket) => (
                  <button
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
                    <div className="ticket-card-header">
                      <h3>
                        {ticket.title}
                      </h3>

                      <span>
                        #
                        {
                          ticket.ticket_id
                        }
                      </span>
                    </div>

                    <div className="ticket-meta">
                      <span>
                        Status:{" "}
                        {ticket.status}
                      </span>

                      <span>
                        Priority:{" "}
                        {ticket.priority}
                      </span>

                      <span>
                        Category:{" "}
                        {ticket.category}
                      </span>

                      <span>
                        Requester:{" "}
                        {ticket.requester ||
                          "Unknown"}
                      </span>
                    </div>
                  </button>
                )
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;