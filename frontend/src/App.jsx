import { useState } from "react";

function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const [user, setUser] = useState(null);

  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState("");

  const [tickets, setTickets] = useState([]);
  const [ticketsError, setTicketsError] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [ticketMessage, setTicketMessage] = useState("");

  async function handleLogin(event) {
    event.preventDefault();

    const formData = new URLSearchParams();

    formData.append("username", email);
    formData.append("password", password);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/auth/login",
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
        setMessage(data.detail || "Login failed");
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      setUser(data.user);
      setMessage("");
    } catch (error) {
      setMessage("Could not connect to the backend.");
    }
  }

  async function loadDashboard() {
    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/dashboard/summary",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setDashboardError("Could not load dashboard.");
        return;
      }

      setDashboard(data);
      setDashboardError("");
    } catch (error) {
      setDashboardError("Could not connect to the backend.");
    }
  }

  async function loadTickets() {
    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/tickets/",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setTicketsError("Could not load tickets.");
        return;
      }

      setTickets(data.tickets);
      setTicketsError("");
    } catch (error) {
      setTicketsError("Could not connect to the backend.");
    }
  }

  async function createTicket(event) {
    event.preventDefault();

    const token = localStorage.getItem("access_token");

    const newTicket = {
      title: title,
      description: description,
      category: category,
      priority: priority,
      department_id: null,
      asset_id: null,
    };

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/tickets/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(newTicket),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setTicketMessage("Could not create ticket.");
        return;
      }

      setTicketMessage("Ticket created successfully.");

      setTitle("");
      setDescription("");
      setCategory("");
      setPriority("MEDIUM");

      loadTickets();
      loadDashboard();
    } catch (error) {
      setTicketMessage("Could not connect to the backend.");
    }
  }

  if (user) {
    return (
      <div>
        <h1>Campus ServiceDesk</h1>

        <h2>Welcome, {user.full_name}</h2>

        <p>Role: {user.role}</p>

        <button onClick={loadDashboard}>
          Load Dashboard
        </button>

        <button onClick={loadTickets}>
          Load Tickets
        </button>

        <p>{dashboardError}</p>
        <p>{ticketsError}</p>

        <h2>Create Ticket</h2>

        <form onSubmit={createTicket}>
          <div>
            <label>Title</label>
            <br />

            <input
              type="text"
              value={title}
              onChange={(event) =>
                setTitle(event.target.value)
              }
              required
            />
          </div>

          <br />

          <div>
            <label>Description</label>
            <br />

            <textarea
              value={description}
              onChange={(event) =>
                setDescription(event.target.value)
              }
              required
            />
          </div>

          <br />

          <div>
            <label>Category</label>
            <br />

            <input
              type="text"
              value={category}
              onChange={(event) =>
                setCategory(event.target.value)
              }
              required
            />
          </div>

          <br />

          <div>
            <label>Priority</label>
            <br />

            <select
              value={priority}
              onChange={(event) =>
                setPriority(event.target.value)
              }
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <br />

          <button type="submit">
            Create Ticket
          </button>
        </form>

        <p>{ticketMessage}</p>

        {dashboard && (
          <div>
            <h2>Dashboard</h2>

            <p>Total Tickets: {dashboard.total_tickets}</p>
            <p>Open Tickets: {dashboard.open_tickets}</p>
            <p>
              In Progress: {dashboard.in_progress_tickets}
            </p>
            <p>Resolved: {dashboard.resolved_tickets}</p>
            <p>
              High Priority: {dashboard.high_priority_tickets}
            </p>
            <p>Unassigned: {dashboard.unassigned_tickets}</p>
          </div>
        )}

        {tickets.length > 0 && (
          <div>
            <h2>Tickets</h2>

            {tickets.map((ticket) => (
              <div key={ticket.ticket_id}>
                <h3>{ticket.title}</h3>

                <p>Ticket ID: {ticket.ticket_id}</p>
                <p>Category: {ticket.category}</p>
                <p>Status: {ticket.status}</p>
                <p>Priority: {ticket.priority}</p>
                <p>Requester: {ticket.requester}</p>

                <p>
                  Department:{" "}
                  {ticket.department_name || "None"}
                </p>

                <p>
                  Asset: {ticket.asset_name || "None"}
                </p>

                <hr />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <h1>Campus ServiceDesk</h1>

      <h2>Login</h2>

      <form onSubmit={handleLogin}>
        <div>
          <label>Email</label>
          <br />

          <input
            type="email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
          />
        </div>

        <br />

        <div>
          <label>Password</label>
          <br />

          <input
            type="password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            required
          />
        </div>

        <br />

        <button type="submit">
          Login
        </button>
      </form>

      <p>{message}</p>
    </div>
  );
}

export default App;