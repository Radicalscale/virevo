# Local Development Setup Guide

## Prerequisites
- Node.js 16+ and Yarn
- Python 3.10+
- MongoDB (local or cloud instance)
- VS Code

## Step 1: MongoDB Setup

### Option A: Use This Pre-Deployment Database (Recommended for Testing)
You can connect directly to this environment's MongoDB to access all existing data including the demo account.

**Connection Details:**
- **Host:** Contact Emergent support for remote access credentials
- **Database:** `test_database`
- **Contains:** Demo user (kendrickbowman9@gmail.com) + all agents, phone numbers, KB items

### Option B: Local MongoDB
```bash
# Install MongoDB locally
brew install mongodb-community@7.0  # macOS
# or
sudo apt install mongodb  # Linux
# or download from mongodb.com for Windows

# Start MongoDB
brew services start mongodb-community  # macOS
sudo systemctl start mongodb  # Linux
```

## Step 2: Backend Setup

### 2.1 Create Virtual Environment
```bash
cd backend
python -m venv venv

# Activate
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### 2.2 Install Dependencies
```bash
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables
Create `backend/.env` file:

```env
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database

# Or connect to remote (ask Emergent support for credentials)
# MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/
# DB_NAME=test_database

# RAG (optional - disable for faster startup)
ENABLE_RAG=true

# JWT Secret
JWT_SECRET_KEY=your-local-secret-key-change-me

# Environment
ENVIRONMENT=development

# TTS Services (optional - uses defaults if not set)
# DIA_TTS_API_URL=http://203.57.40.158:10230
# MELO_TTS_API_URL=http://203.57.40.160:10162
# KOKORO_TTS_API_URL=http://203.57.40.151:10213
# SESAME_TTS_API_URL=https://6qt2ld98tmdhu2-8000.proxy.runpod.net/generate
# SESAME_TTS_BASE_URL=https://6qt2ld98tmdhu2-8000.proxy.runpod.net

# External API Keys (add your own)
ELEVENLABS_API_KEY=your_key_here
SONIOX_API_KEY=your_key_here
TELNYX_API_KEY=your_key_here
GROK_API_KEY=your_key_here
```

### 2.4 Start Backend
```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

Backend will be at: `http://localhost:8001`

## Step 3: Frontend Setup

### 3.1 Install Dependencies
```bash
cd frontend
yarn install
```

### 3.2 Configure Environment Variables
Create `frontend/.env` file:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
PORT=3000
```

### 3.3 Start Frontend
```bash
yarn start
```

Frontend will be at: `http://localhost:3000`

## Step 4: Access the Application

### Demo Account Credentials
**Email:** kendrickbowman9@gmail.com  
**Password:** B!LL10n$$

This account has:
- 14 pre-configured agents
- 2 phone numbers
- 194 call logs
- 6 knowledge base items

### First Time Login
1. Go to `http://localhost:3000`
2. You'll be redirected to `/login`
3. Enter demo credentials above
4. Click "Sign in"
5. You'll be redirected to `/agents` page

## Step 5: VS Code Setup

### Recommended Extensions
- Python (Microsoft)
- Pylance
- ES7+ React/Redux/React-Native snippets
- MongoDB for VS Code
- REST Client (for API testing)

### VS Code Launch Configuration
Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "server:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8001"
      ],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    }
  ]
}
```

### VS Code Settings
Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.envFile": "${workspaceFolder}/backend/.env",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "black"
}
```

## Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
mongosh --eval "db.runCommand({ connectionStatus: 1 })"

# Or use MongoDB Compass GUI
# Download from: https://www.mongodb.com/products/compass
```

### Backend Won't Start
```bash
# Check Python version
python --version  # Should be 3.10+

# Verify dependencies
pip list | grep fastapi

# Check logs
tail -f backend.log
```

### Frontend Won't Start
```bash
# Clear cache
yarn cache clean
rm -rf node_modules
yarn install

# Check Node version
node --version  # Should be 16+
```

### RAG Not Loading
If you see errors about sentence-transformers:
```bash
# Option 1: Disable RAG in .env
ENABLE_RAG=false

# Option 2: Install ML dependencies manually
pip install torch transformers sentence-transformers
```

### CORS Errors
Make sure `REACT_APP_BACKEND_URL` in frontend/.env matches your backend URL exactly:
- Backend on `http://localhost:8001`
- Frontend on `http://localhost:3000`

## Database Migration (Optional)

If you want to create a NEW user instead of using the demo account:

```bash
cd backend
python migrate_to_multi_tenant.py
```

This will create a user and migrate existing data to them.

## Testing the Application

### 1. Test Authentication
- Sign up new user at `/signup`
- Login with demo account
- Check logout functionality

### 2. Test Agents
- Create a new agent
- Edit agent settings
- Test web caller with agent

### 3. Test Phone Numbers
- Add a phone number
- Assign inbound/outbound agents
- Test call routing (requires Telnyx setup)

### 4. Test Knowledge Base
- Upload a PDF to an agent
- Add a URL to scrape
- Test KB queries in web caller

## Production Deployment

When ready to deploy, this exact setup will work on Emergent platform - all environment variables are already configured to work in both local and production environments.

## Need Help?

- Check logs in backend terminal
- Use browser DevTools Console for frontend issues
- Check MongoDB data using MongoDB Compass
- Contact Emergent support for remote database access
