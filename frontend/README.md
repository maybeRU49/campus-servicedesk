# Campus ServiceDesk frontend

React/Vite interface for the existing FastAPI application. See the [project README](../README.md) for database, accounts, backend setup and role behavior.

```powershell
Copy-Item .env.example .env
npm ci
npm run dev
```

`VITE_API_URL` selects the backend and defaults to `http://127.0.0.1:8000`. Restart Vite after changing it. The backend CORS allowlist must include the frontend origin.

Checks: `npm test`, `npm run lint`, `npm run build`.

`src/api.js` centralizes authentication/error handling. Dashboard and asset presentation are in `src/components/`; existing ticket screens and interactions remain in `src/App.jsx`. Ticket search/filters run locally on the API-authorized list. UI controls do not grant backend permissions.
