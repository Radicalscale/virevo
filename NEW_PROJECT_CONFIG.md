# New Project Configuration
**Project:** `miraculous-playfulness`
**Target Service:** `virevo` (Backend)
**Date:** 2026-02-11

## Architecture Setup
I have replicated the architecture of the old project (`respectful-wholeness`) by ensuring the following services exist and are connected:

1.  **Redis:** Created a new internal Redis service.
2.  **MongoDB:** Used the existing/new MongoDB service in this project.
3.  **Backend:** Configured `virevo` to connect to both.

## Environment Variables Applied
The following variables have been set on the `virevo` service.

| Variable | Value | Notes |
| :--- | :--- | :--- |
| `PORT` | `8001` | |
| `ENABLE_RAG` | `true` | |
| `COOKIE_SECURE` | `true` | |
| `DB_NAME` | `virevo` | |
| `BACKEND_URL` | `https://virevo-production.up.railway.app` | **NEW Domain** |
| `CORS_ORIGINS` | `https://virevo.ai,https://api.virevo.ai,https://virevo-production.up.railway.app` | Updated with new domain |
| `MONGO_URL` | `${{MongoDB.MONGO_URL}}` | Dynamic Reference |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Dynamic Reference |
| `ENCRYPTION_KEY` | `XQoX5As6wDkbFVB...` | Copied from old project |
| `JWT_SECRET_KEY` | `andromeda-...` | Copied from old project |
| `TELNYX_API_KEY` | `KEY0199...` | Copied from old project |
| `TELNYX_CONNECTION_ID`| `2777...` | Copied from old project |
| `MAYA_TTS_API_URL` | `http://203...` | Copied from old project |

## Next Steps
1.  **Deployment:** The service has been triggered to redeploy with these new settings.
2.  **DNS (Optional):** If you want to use `api.li-ai.org` or similar on this new project, you will need to update your DNS records to point to `virevo-production.up.railway.app` or add a Custom Domain in Railway settings.
