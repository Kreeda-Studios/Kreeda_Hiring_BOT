# Single Port Setup with Nginx Reverse Proxy

## Overview

The Kreeda Hiring Bot now uses an **nginx reverse proxy** to serve both frontend and backend through a **single port (80)**. This solves the Tailscale funnel limitation of only exposing one port.

## Architecture

```
Internet (Tailscale Funnel)
         ↓ Port 80
    nginx (Port 80)
    ├── /api/* → backend:3001
    ├── /api/sse/* → backend:3001 (Server-Sent Events)
    └── /* → frontend:3000
```

## Services

- **nginx**: Reverse proxy on port 80 (the only exposed port)
- **backend**: Internal port 3001 (not exposed externally)
- **frontend**: Internal port 3000 (not exposed externally)
- **mongodb**: Port 27017 (internal only)
- **redis**: Port 6379 (internal only)
- **python-processor**: No ports (worker service)

## URLs

When using Tailscale funnel, expose only port 80, then:

- **Frontend**: `http://your-tailscale-url/`
- **Backend API**: `http://your-tailscale-url/api/`
- **Health Check**: `http://your-tailscale-url/health`

## Local Development

For local development, access via:

- **Frontend**: `http://localhost/`
- **Backend API**: `http://localhost/api/`
- **Health Check**: `http://localhost/health`

## Tailscale Funnel Setup

1. **Start services**:
   ```bash
   docker compose up -d
   ```

2. **Expose single port with Tailscale funnel**:
   ```bash
   tailscale funnel 80
   ```

3. **Access your application**:
   - Your app will be available at your Tailscale node URL
   - Both frontend and API will work through the same URL

## Configuration Files

### nginx/nginx.conf
- Routes `/api/*` to backend:3001
- Routes everything else to frontend:3000
- Handles CORS and file upload limits
- Optimized for SSE (Server-Sent Events)

### docker-compose.yml
- Only nginx exposes port 80
- All other services use internal networking
- Frontend uses relative API URLs (`/api`)

### .env
- `NEXT_PUBLIC_API_URL=/api` (relative URL)
- `BACKEND_API_URL=http://backend:3001/api` (internal container name)

## Benefits

1. **Single Port**: Only port 80 needs to be exposed
2. **Tailscale Compatible**: Works perfectly with Tailscale funnel
3. **SSL Ready**: Nginx can easily handle SSL termination
4. **Performance**: Nginx efficiently handles static files and proxying
5. **Security**: Backend and database are not directly exposed

## Troubleshooting

### Check service status:
```bash
docker compose ps
```

### Check nginx logs:
```bash
docker logs kreeda-nginx
```

### Test routing:
```bash
curl http://localhost/health          # Should return "healthy"
curl http://localhost/api/health      # Should return backend health JSON
curl http://localhost/               # Should return frontend HTML
```

### Restart services:
```bash
docker compose restart nginx
```

## Development Notes

- Frontend development server runs on container port 3000
- Backend development server runs on container port 3001
- All external access goes through nginx on port 80
- Internal services communicate using Docker networking