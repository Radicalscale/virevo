# Import MongoDB Data to Your Personal Account

## ✅ Data Exported Successfully

Location: `/app/mongodb_export/test_database/`

Contains:
- **users** (1 document) - Demo account
- **agents** (14 documents) - All AI agents
- **phone_numbers** (2 documents) - Phone configurations
- **call_logs** (203 documents) - Call history
- **knowledge_base** (6 documents) - KB items
- **api_keys** (2 documents) - API configurations

## Step 1: Download the Export

The `mongodb_export` folder is in your downloaded git files. If not, download it from the Emergent workspace.

## Step 2: Choose Your MongoDB

### Option A: MongoDB Atlas (Recommended - Free)
1. Go to https://cloud.mongodb.com
2. Sign up for free account
3. Create a free cluster (M0)
4. Click "Connect" → "Connect your application"
5. Copy connection string like:
   ```
   mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
   ```

### Option B: Local MongoDB
```bash
# Install MongoDB
brew install mongodb-community  # macOS
# or
sudo apt install mongodb  # Linux

# Start MongoDB
brew services start mongodb-community  # macOS
sudo systemctl start mongodb  # Linux

# Your connection string:
mongodb://localhost:27017
```

## Step 3: Import the Data

### Using MongoDB Atlas:
```bash
mongorestore --uri="mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/test_database" /path/to/mongodb_export/test_database
```

### Using Local MongoDB:
```bash
mongorestore --uri="mongodb://localhost:27017/test_database" /path/to/mongodb_export/test_database
```

This will create the `test_database` database with all collections.

## Step 4: Update Your Local .env

In your local `backend/.env`:

```env
# For MongoDB Atlas:
MONGO_URL=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
DB_NAME=test_database

# OR for Local MongoDB:
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
```

## Step 5: Verify Import

```bash
# Connect to your MongoDB
mongosh "YOUR_CONNECTION_STRING/test_database"

# Check collections
show collections

# Verify user exists
db.users.find({email: "kendrickbowman9@gmail.com"})

# Count documents
db.agents.countDocuments()  # Should show 14
```

## Step 6: Run Your Local App

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn server:app --reload --port 8001

# Frontend (new terminal)
cd frontend
yarn start
```

Login with: kendrickbowman9@gmail.com / B!LL10n$$

## Important Notes

- This is YOUR database now - completely separate from Emergent's
- When you deploy to Emergent, it will use THEIR managed MongoDB (different instance)
- Your local changes won't affect the deployed version's data
- To sync data between local and deployed, you'll need to export/import manually

## Need to Re-export?

If you need fresh data from the pre-deployment environment later, just run:
```bash
mongodump --uri="mongodb://localhost:27017" --db=test_database --out=/app/mongodb_export_new
```

That's it! You now have full control of your own MongoDB with all the data.
