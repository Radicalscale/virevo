# How to View Your MongoDB Data

## Method 1: MongoDB Atlas Web Interface (Easiest)

1. Go to https://cloud.mongodb.com
2. Login to your account
3. Click on your cluster name (should see "Andramada" cluster)
4. Click **"Browse Collections"** button
5. Select database: **test_database**
6. You'll see all collections:
   - **users** - Click to see demo user
   - **agents** - Click to see all 14 agents
   - **phone_numbers** - 2 phone numbers
   - **call_logs** - 203 call history records
   - **knowledge_base** - 6 KB items
   - **api_keys** - 2 API configurations

You can:
- View documents
- Edit documents
- Delete documents
- Add new documents
- Export data

## Method 2: MongoDB Compass (Desktop App - Best for Development)

1. Download from: https://www.mongodb.com/products/compass
2. Install and open Compass
3. Click "New Connection"
4. Paste your connection string:
   ```
   mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
   ```
5. Click "Connect"
6. Navigate to **test_database**
7. Browse all collections with full GUI

Benefits:
- Better visual interface
- Query builder
- Schema analysis
- Easy data editing

## Method 3: Command Line (mongosh)

```bash
mongosh "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/test_database?appName=Andramada"

# Once connected:
show collections              # List all collections
db.users.find().pretty()      # View all users
db.agents.find().pretty()     # View all agents
db.agents.countDocuments()    # Count agents (should be 14)
```

## Verify It's YOUR Database

Check the demo user:
```javascript
db.users.findOne({email: "kendrickbowman9@gmail.com"})
```

Should show:
- email: kendrickbowman9@gmail.com
- id: dcafa642-6136-4096-b77d-a4cb99a62651
- created_at, last_login, etc.

## Current Connection Status

Your app is NOW connected to:
- **Host:** andramada.rznsqrc.mongodb.net (YOUR Atlas cluster)
- **Database:** test_database
- **Owner:** YOU (not Emergent)

To confirm, check backend/.env:
```
MONGO_URL="mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
```

This is YOUR connection string, YOUR cluster, YOUR data!
