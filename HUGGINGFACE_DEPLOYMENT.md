# Hugging Face Space Deployment Guide

## Quick Deploy to Hugging Face Space

### Option 1: Direct Upload (Easiest)

1. **Create New Space on huggingface.co**
   - Go to: https://huggingface.co/new-space
   - Name: `hackinsight-air-quality-pakistan`
   - License: `cc-by-4.0`
   - SDK: **Docker** (for full control)
   - Hardware: **CPU basic** (free tier)
   - Visibility: **Public**

2. **Clone Your HF Space Repository**
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan
   cd hackinsight-air-quality-pakistan
   ```

3. **Copy Files from This Repository**
   ```bash
   # Copy README for HF Space (with metadata header)
   cp /workspace/README_HF.md README.md
   
   # Copy application files
   cp /workspace/app.py .
   cp /workspace/requirements.txt .
   cp /workspace/Makefile .
   
   # Copy dashboard
   cp -r /workspace/dashboard .
   
   # Copy pipeline
   cp -r /workspace/pipeline .
   
   # Copy config
   cp -r /workspace/config .
   
   # Copy data artifacts (for dashboard to serve)
   mkdir -p data/processed data/quality data/reports
   cp /workspace/data/processed/gold_air_quality.csv data/processed/
   cp /workspace/data/quality/quality_report.json data/quality/
   cp /workspace/data/reports/execution_status.json data/reports/
   cp /workspace/data/reports/forecast_metrics.json data/reports/
   cp /workspace/data/reports/forecast_predictions.csv data/reports/
   
   # Copy pipeline log
   cp /workspace/prefect_runs.csv .
   ```

4. **Create Dockerfile for HF Space**
   ```bash
   cat > Dockerfile << 'EOF'
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# HF Spaces runs on port 7860 by default
ENV PORT=7860
ENV HOST=0.0.0.0

# Expose port
EXPOSE 7860

# Run the dashboard
CMD ["python3", "app.py"]
EOF
   ```

5. **Commit and Push**
   ```bash
   git add .
   git commit -m "🚀 Initial deployment of HackInsight dashboard"
   git push
   ```

6. **Wait for Build**
   - HF will automatically build and deploy
   - Check build logs on your Space page
   - Should be live in ~2-3 minutes

7. **Verify Deployment**
   - Visit: `https://huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan`
   - Test dashboard loads
   - Test Insight Agent chat
   - Test dark mode toggle
   - Check `/api/dashboard` endpoint

---

### Option 2: Git Integration (Automatic Sync)

1. **Create Space with Git Integration**
   - On HF Space creation, select "Git" option
   - Link to: `https://github.com/UzairAhmed87/HackInsight-TeamHaseen`

2. **Configure Build**
   - HF will auto-detect Python project
   - Use Dockerfile above
   - Set environment variables if needed

3. **Auto-Deploy on Push**
   - Every push to GitHub main branch triggers HF rebuild
   - Automatic continuous deployment

---

## Dockerfile Configuration

Create `Dockerfile` in repository root:

```dockerfile
FROM python:3.12-slim

# Install system dependencies (none needed - standard library only!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application
COPY . .

# Create data directories (will be populated from copied files)
RUN mkdir -p data/raw data/cleaned data/processed data/quality data/reports

# Expose port (HF Spaces default: 7860)
EXPOSE 7860

# Set environment variables
ENV PORT=7860
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/dashboard')"

# Run dashboard
CMD ["python3", "app.py"]
```

---

## Testing Locally with Docker

Before deploying to HF Space, test locally:

```bash
# Build Docker image
docker build -t hackinsight-dashboard .

# Run container
docker run -p 7860:7860 hackinsight-dashboard

# Test in browser
open http://localhost:7860
```

---

## Environment Variables (Optional)

If you need to configure runtime behavior:

**In HF Space Settings → Variables:**
- `PORT`: 7860 (default)
- `HOST`: 0.0.0.0 (default)
- `HACKINSIGHT_DISABLE_LIVE`: 1 (to disable live sensors)

---

## Troubleshooting

### Build Fails
- **Check Dockerfile syntax:** Use standard FROM/COPY/CMD
- **Check Python version:** Must be 3.12+
- **Check file paths:** All COPY paths must exist

### Dashboard Not Loading
- **Check logs:** HF Space → Logs tab
- **Check port binding:** Must be 7860 or $PORT
- **Check health endpoint:** `/api/dashboard` should return 200

### Data Files Missing
- **Ensure copied:** `data/processed/gold_air_quality.csv` must exist
- **Check paths:** Dashboard looks in `data/` subdirectories
- **Commit files:** Must be in git (not .gitignored)

### Hourly Pipeline Not Running on HF
- **HF Spaces are static:** They don't run scheduled jobs
- **Pipeline runs on GitHub Actions:** That's where hourly automation happens
- **HF Space serves results:** It reads prefect_runs.csv committed by GH Actions

---

## Architecture: GitHub Actions + HF Space

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Hourly Cron Job (0 * * * *)                     │  │
│  │  1. Run: python3 run_pipeline.py                 │  │
│  │  2. Generate: prefect_runs.csv                   │  │
│  │  3. Update: data/quality/quality_report.json     │  │
│  │  4. Commit & Push to GitHub                      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Git Push
                 ▼
┌─────────────────────────────────────────────────────────┐
│                   GitHub Repository                      │
│  - Source code                                           │
│  - prefect_runs.csv (updated hourly)                    │
│  - Data artifacts (updated hourly)                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Auto-deploy
                 ▼
┌─────────────────────────────────────────────────────────┐
│               Hugging Face Space                         │
│  - Serves dashboard at port 7860                        │
│  - Reads latest prefect_runs.csv                        │
│  - Shows freshness/quality/last run                     │
│  - Static serving (no pipeline execution)               │
└─────────────────────────────────────────────────────────┘
```

**Key Insight:** 
- **GitHub Actions** = Automation (runs pipeline)
- **HF Space** = Serving (displays results)
- They work together via git commits

---

## Post-Deployment Checklist

After deploying to HF Space:

- [ ] **Dashboard loads** (https://huggingface.co/spaces/...)
- [ ] **Forecast chart renders** (SVG visualization)
- [ ] **Calendar heatmap shows** (daily history)
- [ ] **Dark mode toggles** (theme switcher works)
- [ ] **Insight Agent responds** (/api/ask endpoint)
- [ ] **Export CSV works** (download button)
- [ ] **Export PNG works** (chart download)
- [ ] **Mobile responsive** (test on phone)
- [ ] **prefect_runs.csv visible** (logs endpoint)
- [ ] **Quality report accessible** (API endpoint)

---

## Update HF Space After Changes

When GitHub Actions makes hourly commits:

**If using Git integration:**
- HF auto-pulls and rebuilds (may take 2-3 min)

**If manual deploy:**
```bash
cd /path/to/hf-space-clone
git pull origin main  # Pull from GitHub
git push              # Push to HF Space
```

---

## Add HF Space Link to Repository

After deployment, update README.md:

```markdown
## Live Deployments

**Hugging Face Space:** https://huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan

**Render (backup):** https://hackinsight-air-quality-pakistan.onrender.com
```

---

## Support

If issues persist:
1. Check HF Space logs
2. Test locally with Docker
3. Verify all files copied
4. Check HF Space discussions: https://huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan/discussions

---

**Deployment Status:** Ready ✅  
**Estimated Time:** 15 minutes  
**Difficulty:** Easy (standard Docker deploy)
