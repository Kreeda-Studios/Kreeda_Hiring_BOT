# Streamlit Cloud Free Tier Deployment Guide

## ✅ Changes Made for Streamlit Cloud Compatibility

### 1. Reduced Parallel Workers
- **Changed:** `MAX_WORKERS` from 5 to 2
- **Location:** `main.py` line 312
- **Reason:** Free tier has limited CPU/RAM resources

### 2. Added Data Loss Warning
- **Added:** Warning banner at top of app
- **Added:** Note in documentation tab
- **Reason:** Users need to know data is ephemeral

### 3. Made Caching Graceful
- **Updated:** `utils/cache.py` to handle failures silently
- **Behavior:** Cache attempts to work, but fails gracefully on ephemeral storage
- **Result:** App works fine without caching (just slower)

---

## 🚀 Deployment Steps

### Step 1: Prepare Your Repository

1. **Ensure all changes are committed:**
   ```bash
   git add .
   git commit -m "Optimize for Streamlit Cloud free tier"
   git push
   ```

2. **Verify these files exist:**
   - ✅ `main.py` (entry point)
   - ✅ `requirements.txt` (all dependencies)
   - ✅ `.gitignore` (excludes venv, .env, cache files)

### Step 2: Deploy to Streamlit Cloud

1. **Go to:** https://share.streamlit.io/
2. **Sign in** with GitHub
3. **Click:** "New app"
4. **Select:**
   - Repository: Your GitHub repo
   - Branch: `main` (or your default branch)
   - Main file path: `main.py`
5. **Click:** "Deploy"

### Step 3: Configure Secrets

1. **In your app dashboard**, go to **Settings** → **Secrets**
2. **Add your OpenAI API key:**
   ```toml
   OPENAI_API_KEY = "sk-your-actual-api-key-here"
   ```
3. **Click:** "Save"

### Step 4: Test Your Deployment

1. **Wait for deployment** to complete (usually 1-2 minutes)
2. **Open your app** from the dashboard
3. **Test with small batch:**
   - Upload a JD
   - Upload 3-5 resumes (not 20+)
   - Process and verify results
   - **Download results** before closing

---

## ⚠️ Important Limitations

### Data Persistence
- ❌ **All files are deleted** when app restarts or sleeps
- ❌ **Cache files are lost** (caching disabled automatically)
- ❌ **Processed resumes are lost** after session ends
- ✅ **JD can be re-processed** (it's fast)

### Performance Limits
- ⚠️ **Timeout:** ~5 minutes max per request
- ⚠️ **Resources:** Limited CPU/RAM (2 workers max)
- ⚠️ **Sleep mode:** App sleeps after inactivity

### Best Practices
1. **Process small batches** (5-10 resumes at a time)
2. **Download results immediately** after processing
3. **Re-upload JD** if needed (it's fast)
4. **Don't rely on caching** - expect slower processing

---

## 🔧 Environment Variables (Optional)

You can set these in Streamlit Secrets if needed:

```toml
OPENAI_API_KEY = "sk-your-key-here"
ENABLE_PARALLEL = "true"
MAX_WORKERS = "2"
CACHE_ENABLED = "false"  # Disable caching entirely (optional)
```

**Note:** `OPENAI_API_KEY` is required. Others have sensible defaults.

---

## 📋 Pre-Deployment Checklist

- [ ] Code is committed and pushed to GitHub
- [ ] `requirements.txt` is up to date
- [ ] `.gitignore` excludes venv, .env, cache files
- [ ] `main.py` is the entry point
- [ ] Tested locally with small batch
- [ ] OpenAI API key ready for Secrets
- [ ] Understand data loss limitations

---

## 🐛 Troubleshooting

### App won't start
- **Check:** `requirements.txt` has all dependencies
- **Check:** `main.py` is the correct entry point
- **Check:** No syntax errors in code

### API key not working
- **Check:** Secrets are saved correctly
- **Check:** Format is `OPENAI_API_KEY = "sk-..."`
- **Check:** No extra quotes or spaces

### Timeout errors
- **Solution:** Process fewer resumes (5-10 max)
- **Solution:** Reduce batch size
- **Solution:** Consider paid tier or self-hosting

### Files disappearing
- **Expected:** This is normal on free tier
- **Solution:** Download results immediately
- **Solution:** Use paid tier for persistence

---

## 📊 Expected Performance

### Processing Times (Free Tier)
- **JD Processing:** 5-10 seconds
- **5 Resumes:** 30-60 seconds
- **10 Resumes:** 1-2 minutes
- **20 Resumes:** 2-4 minutes (may timeout)

### Resource Usage
- **CPU:** Limited (2 workers)
- **Memory:** ~500MB-1GB
- **Storage:** Ephemeral (lost on restart)

---

## 🎯 Next Steps

### If Free Tier Works for You
- ✅ Continue using it for demos/testing
- ✅ Always download results
- ✅ Process small batches

### If You Need More
1. **Upgrade to Streamlit Team** ($20/month)
   - Persistent storage
   - No sleep mode
   - Better resources

2. **Self-host on Railway/Render** ($5-10/month)
   - Full control
   - Persistent storage
   - Better performance
   - See `DEPLOYMENT_GUIDE.md` for details

---

## 📝 Notes

- **Caching:** Automatically disabled if filesystem is read-only
- **Workers:** Reduced to 2 for free tier compatibility
- **Data Loss:** Expected behavior - always download results
- **API Costs:** You pay for OpenAI API usage (not included in free tier)

---

**Last Updated:** 2025-01-XX  
**Version:** Optimized for Streamlit Cloud Free Tier




