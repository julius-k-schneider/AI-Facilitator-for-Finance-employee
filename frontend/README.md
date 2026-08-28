# Frontend

React 19 + Vite SPA, styled with Mantine and fully bilingual (German/English)
via i18next.

## Running it

The standard way is **not** to start this on its own — `docker compose up` from
the repository root brings up the frontend together with Django, Postgres and
n8n, which is what the app needs to do anything useful. See the root
[`README.md`](../README.md).

Run it standalone only when you want a faster Vite reload than the container
gives you. The backend still has to be running, because `vite.config.js` proxies
`/api` to it:

```bash
docker compose up -d db web    # backend on http://127.0.0.1:8000
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Without a reachable backend the app renders the login screen and every request
fails.

## Scripts

```bash
npm run dev       # dev server with the /api proxy
npm run build     # production build into dist/ (base '/static/')
npm run preview   # serve the production build locally
npm run lint      # ESLint
```

There is no frontend test suite; `npm run lint` and `npm run build` are the
checks that exist.

## Layout

```
src/
├── App.jsx        # routing, session bootstrap, login/logout
├── pages/         # one module per screen
│   └── missions/  # mission runner + one module per mission type
├── components/    # sidebar, login screen, shared learning views
├── services/      # fetch wrappers, one per API area
├── onboarding/    # onboarding flow and its content
├── i18n/          # de.json / en.json — every user-facing string lives here
├── auth/          # role and permission constants
└── hooks/         # shared React hooks
```

## Conventions

- **No hard-coded user-facing text.** Add the key to both `i18n/locales/de.json`
  and `en.json`; the two files must always have an identical key set.
- **Adding a mission type** means adding a module under
  `pages/missions/missionTypes/` that exports the shared interface (`Runner`,
  `Solution`, `ResultDetails`, …) and registering it in that folder's
  `index.js`. The type also has to exist in `Mission.TYPE_CHOICES` on the
  backend.
- The production build sets `base: '/static/'` so Django's WhiteNoise can serve
  `dist/` — don't change it without adjusting `config/settings.py`.

## Environment

`VITE_API_BASE` overrides the API origin. It is empty by default, which is what
both the Vite proxy (dev) and the single-origin production deployment expect.
Never put backend secrets in a `VITE_*` variable — everything prefixed `VITE_`
is inlined into the client bundle.
