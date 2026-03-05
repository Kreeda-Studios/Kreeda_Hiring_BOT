# ============================================
# PRODUCTION DEPLOYMENT - Tailscale Setup
# ============================================

## 📋 Step-by-Step Deployment Guide

### 1. Update Environment Variables

Edit `.env` file and set:

```bash
# Your Tailscale public URL (get this after setting up Tailscale)
NEXT_PUBLIC_BASE_URL=https://your-machine.tailnet-name.ts.net

# Your OpenAI API key (already set)
OPENAI_API_KEY=sk-proj-...
```

### 2. Update docker-compose.yml

In the `nextjs` service, change:

```yaml
environment:
  - NODE_ENV=production  # Change from development
  - NEXT_PUBLIC_BASE_URL=${NEXT_PUBLIC_BASE_URL}  # Use from .env
```

### 3. Deploy on Server

```bash
# 1. Clone repository on server
git clone <your-repo> /path/to/kreeda

# 2. Navigate to directory
cd /path/to/kreeda

# 3. Update .env file with Tailscale URL
nano .env
# Set NEXT_PUBLIC_BASE_URL=https://your-tailscale-url

# 4. Build and start services
docker compose up --build -d

# 5. Check logs
docker compose logs -f
```

### 4. Setup Tailscale Tunnel

On your server:

```bash
# Install Tailscale (if not installed)
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale and authenticate
sudo tailscale up

# Get your Tailscale URL
tailscale ip -4
# Your URL will be: https://<machine-name>.<tailnet>.ts.net
```

Then expose port 3000:

```bash
# Option A: Use Tailscale Serve (recommended)
tailscale serve https / http://localhost:3000

# Option B: Use Tailscale Funnel (public internet access)
tailscale funnel 3000
```

### 5. Update .env with Actual URL

Once you have your Tailscale URL, update `.env`:

```bash
NEXT_PUBLIC_BASE_URL=https://your-actual-tailscale-url.ts.net
```

Then restart:

```bash
docker compose restart nextjs
```

---

## 🔒 Security Notes

✅ **Exposed:**
- Port 3000 (Next.js) - via Tailscale tunnel

✅ **Internal Only (Secure):**
- Port 27017 (MongoDB)
- Port 6379 (Redis)  
- Port 9000 (MinIO)
- Port 9001 (MinIO Console)

All file access goes through Next.js API proxy at `/api/files/*`

---

## 🧪 Testing

After deployment, test:

1. **Frontend:** `https://your-tailscale-url.ts.net`
2. **Upload resume:** Should work without exposing MinIO
3. **View PDF:** URLs will be `https://your-tailscale-url.ts.net/api/files/resumes/...`

---

## 📝 Environment Variables Reference

### Required in `.env`:
- `OPENAI_API_KEY` - Your OpenAI API key
- `NEXT_PUBLIC_BASE_URL` - Your Tailscale public URL

### Set in docker-compose.yml (automatic):
- `NODE_ENV=production`
- `MONGODB_URI=mongodb://mongodb:27017/kreeda_hiring`
- `REDIS_URL=redis://redis:6379`
- `MINIO_ENDPOINT=minio:9000`
- `MINIO_ACCESS_KEY=minioadmin`
- `MINIO_SECRET_KEY=minioadmin`
- `MINIO_BUCKET_RESUMES=resumes`
- `MINIO_USE_SSL=false`

All internal services use Docker network names - no changes needed!
