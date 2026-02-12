# Virevo Setup Guide

This guide details how to set up the new `virevo.ai` infrastructure on Railway and migrate your data.

## 1. Railway Infrastructure

1.  **Create Project**: Go to [Railway.app](https://railway.app), create a "New Project", and deploy from this repo (`Radicalscale/virevo`).
2.  **Environment Variables**: Add these variables in Railway:

    | Variable | Value | Description |
    | :--- | :--- | :--- |
    | `PORT` | `8001` | Matching the Dockerfile default |
    | `MONGO_URL` | `...` | **New** MongoDB Connection String |
    | `DB_NAME` | `virevo` | Name of the new database |
    | `BACKEND_URL` | `https://api.virevo.ai` | Custom domain for backend |
    | `TELNYX_API_KEY` | `...` | Your Telnyx API Key |
    | `OPENAI_API_KEY` | `...` | Your OpenAI API Key |
    | `DEEPGRAM_API_KEY`| `...` | Your Deepgram API Key |
    | `ELEVEN_API_KEY` | `...` | Your ElevenLabs API Key |

3.  **Networking**: Add custom domain `api.virevo.ai` in Railway Settings.

## 2. MongoDB Migration

A script `migrate_mongo.py` is provided to copy data from your old database.

1.  **Get Connection Strings**:
    -   Find your **OLD** MongoDB URI (e.g., from old Railway project).
    -   Get your **NEW** MongoDB URI (from new cluster).

2.  **Run Migration**:
    ```bash
    # Install requirements
    pip install motor tqdm

    # Execute
    python migrate_mongo.py --source "mongodb+srv://OLD_URI..." --dest "mongodb+srv://NEW_URI..."
    ```

## 3. Frontend

1.  Deploy `frontend/` to Netlify.
2.  Set `REACT_APP_BACKEND_URL` = `https://api.virevo.ai`.
3.  The `netlify.toml` file is already updated to redirect `/api` calls correctly if needed, but the React app uses the env var directly.

## 4. Verification

-   Visit `https://api.virevo.ai/docs` (FastAPI Swagger UI) to test backend connectivity.
-   Check `https://virevo.ai` (frontend) and login to verify database connectivity.
