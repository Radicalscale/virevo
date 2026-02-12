# Reference Environment Variables
**Source Project:** `respectful-wholeness` (Production)
**Extracted:** 2026-02-11

## Service: web (Backend)

These are the variables currently running in production.

| Variable | Value | Notes |
| :--- | :--- | :--- |
| `BACKEND_URL` | `api.li-ai.org` | Custom domain |
| `CORS_ORIGINS` | `https://app.li-ai.org,https://li-ai.org` | Frontend domains |
| `DB_NAME` | `test_database` | Managed in MongoDB Atlas |
| `ENCRYPTION_KEY` | `XQoX5As6wDkbFVB-rlEDtr0xFzdgxHtb-65FfaXfbeY=` | **critical** for decrypting user keys |
| `JWT_SECRET_KEY` | `andromeda-jwt-secret-key-2024-production-secure` | Session signing |
| `MAYA_TTS_API_URL` | `http://203.57.40.173:10197` | External TTS service |
| `MONGO_URL` | `mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada` | **Atlas Cluster** (External) |
| `REDIS_URL` | `redis://default:GISuvUUdpUSgsiETDXFiIjQgKgQHIIcU@redis.railway.internal:6379` | Internal Railway Redis |
| `TELNYX_API_KEY` | `KEY0199EBFE1BCD21C2E7B0F316A3E980CC_vM9JBdNR3gZ1qlUiqziXCN` | Platform Telnyx Key |
| `TELNYX_CONNECTION_ID` | `2777245537294877821` | Telnyx App ID |

## Service: Redis

Connection details for the Redis service in the source project.

| Variable | Value |
| :--- | :--- |
| `REDIS_URL` (Internal) | `redis://default:GISuvUUdpUSgsiETDXFiIjQgKgQHIIcU@redis.railway.internal:6379` |
| `REDIS_PASSWORD` | `GISuvUUdpUSgsiETDXFiIjQgKgQHIIcU` |
| `REDIS_PUBLIC_URL` | `redis://default:GISuvUUdpUSgsiETDXFiIjQgKgQHIIcU@redis-production-537c.up.railway.app:6379` |
| `REDISPORT` | `6379` |
| `REDISUSER` | `default` |
| `REDISHOST` | `redis.railway.internal` |

---

## Migration Notes for New Project

1.  **MongoDB:** The source uses an external Atlas cluster (`andramada`).
    *   *Option A:* Reuse this URL (connects to same data).
    *   *Option B:* Create new Mongo in Railway and migrate data.
2.  **Redis:** The source uses an internal Railway Redis.
    *   **Action:** You must create a new Redis service in the new project.
    *   **Note:** The `REDIS_URL` will be different (new password/host) but extraction format `redis://:[password]@[host]:[port]` remains the same.
3.  **Encryption Key:** You MUST copy the `ENCRYPTION_KEY` exactly if you want to support existing encrypted data (if sharing DB).
4.  **Domains:** `BACKEND_URL` and `CORS_ORIGINS` might need updating if the new project is for a different environment (e.g. `staging` vs `prod`).
