# Local Docker Testing Guide

Before deploying to Railway, you can test the Docker build locally to catch any issues early.

## Prerequisites

- Docker installed on your local machine
- Git repository cloned locally

## Build Docker Image

```bash
# Navigate to project root
cd /path/to/your/project

# Build the Docker image
docker build -t andromeda-backend .
```

This will:
1. Install all Python dependencies from `requirements.txt`
2. Copy backend code into the container
3. Set up Gunicorn with 4 Uvicorn workers
4. Expose port 8001

Expected build time: 5-10 minutes (first build)

## Run Docker Container

### Option 1: Using .env file

```bash
docker run -p 8001:8001 --env-file backend/.env andromeda-backend
```

### Option 2: Using production environment variables

```bash
docker run -p 8001:8001 \
  -e MONGO_URL="mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada" \
  -e DB_NAME="test_database" \
  -e CORS_ORIGINS="http://localhost:3000" \
  -e DEEPGRAM_API_KEY="your_key" \
  -e OPENAI_API_KEY="your_key" \
  -e ELEVEN_API_KEY="your_key" \
  -e ENABLE_RAG="true" \
  andromeda-backend
```

## Test the Container

### Health Check

```bash
curl http://localhost:8001/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-...",
  "database": "connected"
}
```

### Create Test User

```bash
curl -X POST http://localhost:8001/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test User"}'
```

### Login

```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}' \
  -c cookies.txt
```

### Get Agents (Authenticated)

```bash
curl http://localhost:8001/api/agents -b cookies.txt
```

## Check Logs

```bash
# View container logs
docker logs [container_id]

# Follow logs in real-time
docker logs -f [container_id]

# Get container ID
docker ps
```

## Test Concurrent Connections

```bash
# Install Apache Bench (if not already installed)
# macOS: brew install httpd
# Ubuntu: sudo apt-get install apache2-utils

# Send 100 requests with 20 concurrent connections
ab -n 100 -c 20 http://localhost:8001/api/health
```

Expected results:
- All requests should succeed (200 OK)
- Average response time < 100ms
- No failed requests

## Common Issues

### Issue: "Cannot connect to database"

**Solution:** Check MongoDB Atlas IP whitelist
- MongoDB Atlas → Network Access → Add IP Address
- For local testing, add your current IP
- For Railway, use 0.0.0.0/0 (allow all)

### Issue: "Port 8001 already in use"

**Solution:** Kill existing process or use different port
```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Or use different port
docker run -p 8002:8001 --env-file backend/.env andromeda-backend
# Then test on http://localhost:8002
```

### Issue: "Build fails with dependency errors"

**Solution:** Check requirements.txt versions
```bash
# View Docker build output
docker build -t andromeda-backend . 2>&1 | tee build.log

# Check for specific errors in build.log
```

### Issue: "RAG not working in container"

**Solution:** Mount data directory for ChromaDB persistence
```bash
docker run -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  --env-file backend/.env \
  andromeda-backend
```

## Performance Testing

### Test WebSocket Connections

```bash
# Install wscat
npm install -g wscat

# Test WebSocket connection (replace with your test endpoint)
wscat -c ws://localhost:8001/ws/test
```

### Test TTS Streaming

```bash
curl -X POST http://localhost:8001/api/text-to-speech \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","voice_id":"21m00Tcm4TlvDq8ikWAM"}' \
  --output test_audio.mp3
```

### Memory Usage

```bash
# Check container stats
docker stats [container_id]
```

Expected memory usage:
- Idle: ~500MB-1GB
- With RAG: ~1.5GB-2GB  
- Under load (20 concurrent): ~2GB-3GB

## Cleanup

```bash
# Stop container
docker stop [container_id]

# Remove container
docker rm [container_id]

# Remove image
docker rmi andromeda-backend

# Remove all unused containers and images
docker system prune -a
```

## Production-like Testing

To test exactly as it will run on Railway:

```bash
# Create production env file (without .env extension to avoid git)
cp .env.production.template env.production
# Edit env.production with your actual keys

# Build with production settings
docker build -t andromeda-backend-prod .

# Run with production settings
docker run -p 8001:8001 --env-file env.production andromeda-backend-prod

# Test with production-like CORS
curl http://localhost:8001/api/health \
  -H "Origin: https://li-ai.org"
```

## Next Steps

Once local Docker testing passes:
1. Push to GitHub
2. Connect Railway to GitHub repo
3. Railway will build and deploy automatically
4. Monitor Railway logs for any production-specific issues

## Troubleshooting Resources

- **Gunicorn Docs:** https://docs.gunicorn.org/
- **Uvicorn Docs:** https://www.uvicorn.org/
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/docker/
- **Docker Best Practices:** https://docs.docker.com/develop/dev-best-practices/

---

**Pro Tip:** Test locally before every deployment to catch issues early!
