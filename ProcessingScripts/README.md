# Resume Processing Worker

Clean, minimal queue processing system for resume analysis jobs.

## 🎯 Key Design Principles

**main.py is MINIMAL** (171 lines):
- ONLY queue orchestration
- NO business logic
- Easy to add more queues
- Clear concurrency settings

**All business logic → resumeprocessing/ folder**

## 📁 Project Structure

```
ProcessingScripts/
├── main.py                  # ← Queue config ONLY (minimal!)
├── Dockerfile               # Production Docker build
├── .env.example             # Environment variables template
├── .dockerignore            # Files to exclude from Docker build
├── requirements.txt         # Python dependencies
└── resumeprocessing/        # ← ALL business logic here
    ├── __init__.py          # Package exports
    ├── job_handler.py       # ← Main job processing flow (NEW!)
    ├── processor.py         # AI extraction and parsing
    ├── api_client.py        # Backend API communication
    ├── s3_handler.py        # S3/MinIO file operations
    └── test_local.py        # Local testing utilities
```

## 🔧 Adding a New Queue (Super Easy!)

1. Create handler function in `resumeprocessing/`
2. Add to `QUEUES` list in `main.py`:

```python
QUEUES = [
    {
        'name': 'your-queue-name',
        'handler': your_handler_function,
        'concurrency': int(os.getenv('YOUR_QUEUE_CONCURRENCY', '2')),
        'lockDuration': 60000,  # milliseconds
    },
]
```

3. Add env var `YOUR_QUEUE_CONCURRENCY=2` to `.env.example`

Done! main.py handles the rest.

## 🚀 Quick Start

### Run with Docker (Production)

```bash
docker compose up --build -d hrbot-processing
```

### Run Locally (Development)

```bash
cd ProcessingScripts

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env and add your OPENAI_API_KEY

# Start the worker
python main.py
```

## ⚙️ Configuration

Edit `main.py` to configure:

### Queue Settings
```python
# Line ~50-56
QUEUE_NAME = 'resume-processing'
QUEUE_NAMES = [
    QUEUE_NAME,
    # Add more queues here
]
```

### Concurrency
```python
# Line ~59
CONCURRENCY = 1  # Process 1 job at a time
```

### Redis Connection
```python
# Line ~46-48
REDIS_HOST = os.getenv('REDIS_HOST', 'hrbot-redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
```

## 📋 How It Works

### Flow:
1. **Listens** to BullMQ queue for new resume jobs
2. **Downloads** PDF file from S3 storage
3. **Processes** resume with AI (OpenAI GPT)
4. **Extracts** structured data (profile, skills, experience, etc.)
5. **Sends** extracted data to backend API
6. **Updates** resume status in database
7. **Cleans up** temporary files

### Job Data Format:
```json
{
  "resumeId": "507f1f77bcf86cd799439011",
  "s3Key": "uuid_Resume.pdf",
  "s3Bucket": "resumes",
  "fileName": "Resume.pdf"
}
```

## 📂 Working on Resume Processing

### To modify AI extraction logic:
- Edit `resumeprocessing/processor.py`
- Change prompts, schema, or parsing logic
- Test locally: `python resumeprocessing/test_local.py`

### To modify API communication:
- Edit `resumeprocessing/api_client.py`
- Functions: `update_resume_status()`, `send_extracted_data()`

### To modify S3 operations:
- Edit `resumeprocessing/s3_handler.py`
- Functions: `download_from_s3()`, `cleanup_temp_file()`

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | hrbot-redis | Redis server hostname |
| `REDIS_PORT` | 6379 | Redis server port |
| `MONGODB_URI` | mongodb://hrbot-mongodb:27017/hrbot_hiring | Database connection |
| `S3_ENDPOINT` | hrbot-s3:9000 | S3/MinIO endpoint |
| `S3_ACCESS_KEY` | minioadmin | S3 access key |
| `S3_SECRET_KEY` | minioadmin | S3 secret key |
| `S3_BUCKET` | resumes | S3 bucket name |
| `API_BASE_URL` | http://hrbot-fullstack:3000 | Backend API URL |
| `OPENAI_API_KEY` | *required* | OpenAI API key |
| `WORKER_CONCURRENCY` | 1 | Number of concurrent jobs |

## 📊 Monitoring

```bash
# View logs
docker compose logs -f hrbot-processing

# Check worker status
docker compose ps hrbot-processing

# Restart worker
docker compose restart hrbot-processing
```

## 🧪 Testing Locally

```bash
# Run test with a sample resume
cd resumeprocessing
python test_local.py
```

## 🐛 Troubleshooting

### Worker not processing jobs
- Check Redis connection: `docker compose logs hrbot-redis`
- Verify queue name matches in main.py and backend
- Check worker logs: `docker compose logs hrbot-processing`

### AI extraction failing
- Verify OPENAI_API_KEY is set correctly
- Check OpenAI API quota/billing
- View detailed error in logs

### S3 download failing
- Check S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY
- Verify bucket exists: `docker compose exec hrbot-s3 mc ls myminio/`
- Check file exists in bucket

## 📝 Adding New Features

### Add a new queue:
1. Edit `main.py` line ~50-56
2. Add queue name to `QUEUE_NAMES` list
3. Create new handler function
4. Register in worker config

### Modify AI prompt:
1. Edit `resumeprocessing/processor.py`
2. Find `SYSTEM_PROMPT` variable
3. Modify instructions or schema
4. Test locally before deploying

### Add new extracted fields:
1. Update schema in `resumeprocessing/processor.py`
2. Update backend API to handle new fields
3. Update database schema in FullStack

## 🚢 Deployment

```bash
# Build and deploy
docker compose up --build -d hrbot-processing

# Check if running
docker compose ps

# View startup logs
docker compose logs --tail=50 hrbot-processing
```

## 📚 Key Files Explained

- **main.py**: Entry point. Handles queue, job processing flow, error handling
- **processor.py**: AI extraction logic, PDF parsing, OpenAI API calls
- **api_client.py**: HTTP functions to communicate with backend API
- **s3_handler.py**: Download files from S3, cleanup temp files
- **__init__.py**: Package exports for cleaner imports

## 💡 Tips for Engineers

1. **Never edit main.py for AI logic** - use processor.py
2. **All config is at the top of main.py** - easy to find
3. **Test changes locally first** - faster iteration
4. **Check logs frequently** - clear error messages
5. **Resume data structure** - defined in processor.py schema
