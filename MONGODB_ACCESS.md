# MongoDB Access Information

## Current Pre-Deployment Environment

**Connection String:**
```
mongodb://localhost:27017
```

**Database Name:**
```
test_database
```

**⚠️ Important:** This MongoDB is running **locally inside the pre-deployment container**, not accessible from outside.

## Options for Local Development

### Option 1: Export Data & Use Your Own MongoDB (Recommended)

I can export all the data for you to import locally:

```bash
# Export all collections from this environment
mongodump --uri="mongodb://localhost:27017/test_database" --out=/app/mongodb_backup

# Then you download the backup and import to your local MongoDB:
mongorestore --uri="mongodb://localhost:27017/test_database" /path/to/mongodb_backup/test_database
```

### Option 2: Use MongoDB Atlas (Free Tier)

1. Create free account at https://cloud.mongodb.com
2. Create a free cluster
3. Get connection string like:
   ```
   mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/test_database
   ```
4. I can export and you import to Atlas
5. Use this connection string in your local `.env`

### Option 3: Start Fresh Locally

```bash
# Install MongoDB locally
brew install mongodb-community  # macOS
# or
sudo apt install mongodb  # Linux

# Start MongoDB
brew services start mongodb-community

# Your local connection:
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database

# Then run the migration script to create demo user:
python migrate_to_multi_tenant.py
```

## What Data You Need

The pre-deployment database contains:

**Users Collection:**
- Demo user: kendrickbowman9@gmail.com
- User ID: dcafa642-6136-4096-b77d-a4cb99a62651

**Agents Collection:** 14 agents
**Phone Numbers Collection:** 2 numbers
**Calls Collection:** 194 call logs
**Knowledge Base Collection:** 6 items
**API Keys Collection:** 2 keys

## Recommendation

**For Testing/Development:**
Use MongoDB Atlas free tier or local MongoDB. I can export the data for you.

**For Production:**
The deployed app on Emergent will use their managed MongoDB, automatically configured via environment variables.

## Need Help?

Let me know if you want me to:
1. Export all data to JSON files you can import
2. Export to MongoDB dump format
3. Generate SQL-like inserts for specific collections
4. Create a fresh database with just the demo user

The data export can be downloaded with your git files.
