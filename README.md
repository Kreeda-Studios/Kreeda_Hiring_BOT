# HR Bot - Docker Setup

AI-powered resume processing system with Next.js frontend and Python worker.

## 🚀 Quick Start

**Start everything:**
```bash
docker compose up --build -d
```

**Stop everything:**
```bash
docker compose down
```

**Access the app:** http://localhost:3000

---

## 🛠️ Development

### Run Everything in Docker

```bash
docker compose up --build -d
```

### Work on Frontend/Backend Locally

```bash
# Stop the fullstack container
docker compose stop hrbot-fullstack

# Run locally with hot reload
cd FullStack
npm install
npm run dev
```

### Work on Processing Script Locally

```bash
# Stop the processing container
docker compose stop hrbot-processing

# Run locally with hot reload
cd ProcessingScripts
pip install -r requirements.txt
python Main.py
```

When running locally, your code will connect to the infrastructure services (MongoDB, Redis, S3) running in Docker.

---

## 📊 View Logs

```bash
# Frontend/Backend logs
docker compose logs -f hrbot-fullstack

# Processing worker logs
docker compose logs -f hrbot-processing

# All logs
docker compose logs -f
```

---

## 🔄 Common Commands

```bash
# Rebuild and restart
docker compose up --build -d

# Restart specific service
docker compose restart hrbot-fullstack
docker compose restart hrbot-processing

# Check status
docker compose ps

# Clean restart (removes all data)
docker compose down -v
docker compose up --build -d
```

---

## 🌐 URLs

- **Application**: http://localhost:3000
- **S3 Console**: http://localhost:9001 (minioadmin / minioadmin)

---

## 🔐 Environment Setup

Copy `.env.example` to `.env` and update `OPENAI_API_KEY`:

```bash
cp .env.example .env
```

Then edit `.env` and add your OpenAI API key.

---

## 📝 Notes

- Uses S3-compatible storage (MinIO for local/dev, easily switch to AWS S3 for production)
- All S3 environment variables are prefixed with `S3_` for future AWS S3 migration
- S3 bucket is automatically created on first startup (no manual setup needed)
- Data persists in Docker volumes
