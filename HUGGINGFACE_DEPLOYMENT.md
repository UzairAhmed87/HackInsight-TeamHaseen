# Hugging Face Space Deployment Guide

## ✅ FREE Deployment Using Gradio SDK

**Important:** Docker SDK on HF Spaces requires paid hardware. We use **Gradio SDK (FREE)** instead!

## Quick Deploy to Hugging Face Space (15 minutes)

### Step 1: Create New Space on huggingface.co

1. **Go to:** https://huggingface.co/new-space
2. **Fill in:**
   - **Name:** `hackinsight-air-quality-pakistan`
   - **License:** `cc-by-4.0`
   - **SDK:** **Gradio** ⬅️ IMPORTANT: Choose Gradio (FREE)
   - **Hardware:** CPU basic (free tier)
   - **Visibility:** Public

3. **Click "Create Space"**

### Step 2: Clone Your New HF Space

```bash
# Clone the HF Space repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan
cd hackinsight-air-quality-pakistan
```

### Step 3: Copy Files from This Repository

```bash
# From your local machine, copy files to HF Space repo:

# Copy README for HF (with metadata header)
cp /workspace/README_HF.md README.md

# Copy Gradio app wrapper
cp /workspace/app_gradio.py app_gradio.py

# Copy requirements
cp /workspace/requirements.txt .

# Copy pipeline modules
cp -r /workspace/pipeline .

# Copy config
cp -r /workspace/config .

# Copy dashboard assets (for reference)
cp -r /workspace/dashboard .

# Copy data artifacts (needed for the agent)
mkdir -p data/processed data/quality data/reports
cp /workspace/data/processed/gold_air_quality.csv data/processed/
cp /workspace/data/quality/quality_report.json data/quality/
cp /workspace/data/reports/execution_status.json data/reports/
cp /workspace/data/reports/forecast_metrics.json data/reports/
cp /workspace/data/reports/forecast_predictions.csv data/reports/

# Copy pipeline log
cp /workspace/prefect_runs.csv .
```

### Step 4: Commit and Push

```bash
git add .
git commit -m "🚀 Initial deployment of HackInsight dashboard"
git push
```

### Step 5: Wait for Build (2-3 minutes)

- HF will automatically install dependencies (just `gradio`)
- Watch build logs on your Space page
- Should be live in ~2-3 minutes

### Step 6: Verify Deployment

Visit: `https://huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan`

**Test:**
- ✅ Insight Agent tab loads
- ✅ Ask a question and get cited answer
- ✅ Pipeline Status tab shows runs
- ✅ About tab displays project info

---

## 🎯 What the Gradio App Provides

### Tab 1: Insight Agent 💬
- Interactive chat interface
- Ask questions, get cited answers
- Example questions provided
- Shows when agent says "I don't know"

### Tab 2: Pipeline Status ⚙️
- Latest pipeline run info
- Quality report summary
- Refresh button to reload

### Tab 3: About 📖
- Project overview
- Requirements checklist
- Key metrics
- Links to GitHub

---

## 📋 Alternative: One-Command Script

Save this as `deploy_to_hf.sh`:

```bash
#!/bin/bash
# Quick deploy script for Hugging Face Space

# Configuration
HF_USERNAME="YOUR_USERNAME"
SPACE_NAME="hackinsight-air-quality-pakistan"
HF_REPO="https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"

# Clone HF Space
echo "📦 Cloning HF Space..."
git clone $HF_REPO
cd $SPACE_NAME

# Copy files
echo "📄 Copying files..."
cp /workspace/README_HF.md README.md
cp /workspace/app_gradio.py app_gradio.py
cp /workspace/requirements.txt .
cp -r /workspace/pipeline .
cp -r /workspace/config .
cp -r /workspace/dashboard .

# Copy data
mkdir -p data/processed data/quality data/reports
cp /workspace/data/processed/gold_air_quality.csv data/processed/
cp /workspace/data/quality/quality_report.json data/quality/
cp /workspace/data/reports/execution_status.json data/reports/
cp /workspace/data/reports/forecast_metrics.json data/reports/
cp /workspace/data/reports/forecast_predictions.csv data/reports/
cp /workspace/prefect_runs.csv .

# Commit and push
echo "🚀 Deploying..."
git add .
git commit -m "🚀 Initial deployment"
git push

echo "✅ Deployment complete!"
echo "🔗 Visit: $HF_REPO"
```

Make executable and run:
```bash
chmod +x deploy_to_hf.sh
./deploy_to_hf.sh
```

---

## 🔧 Troubleshooting

### Build Fails with "Module not found"
**Fix:** Check `requirements.txt` includes `gradio==4.44.0`

### Agent Returns "Data not available"
**Fix:** Ensure data files copied to correct paths:
- `data/processed/gold_air_quality.csv`
- `data/quality/quality_report.json`
- `data/reports/execution_status.json`

### Space Shows Error on Launch
**Fix:** Check HF Space logs (Settings → Logs)
- Verify Python 3.12+ compatibility
- Check all imports work

### Can't Push to HF Space
**Fix:** Configure HF credentials:
```bash
# Install HF CLI (if needed)
pip install huggingface-hub

# Login
huggingface-cli login
# Enter your HF token
```

---

## 🎨 Customize the Interface

Edit `app_gradio.py` to customize:

### Change Theme
```python
demo = gr.Blocks(theme=gr.themes.Soft())  # Default
# Options: Base, Soft, Monochrome, Glass
```

### Add Custom CSS
```python
demo = gr.Blocks(css="""
    .gradio-container { max-width: 1200px; }
    .markdown { font-size: 16px; }
""")
```

### Add More Tabs
```python
with gr.Tab("🔬 New Tab"):
    gr.Markdown("Custom content here")
```

---

## 📊 Architecture: GitHub Actions + HF Space

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
                 │ Manual/auto sync
                 ▼
┌─────────────────────────────────────────────────────────┐
│           Hugging Face Space (Gradio SDK)                │
│  - Runs app_gradio.py                                   │
│  - Interactive Insight Agent interface                   │
│  - Shows pipeline status                                 │
│  - Displays quality metrics                              │
│  - FREE TIER (no Docker needed!)                        │
└─────────────────────────────────────────────────────────┘
```

**Key Insight:**
- **GitHub Actions** = Automation (runs pipeline hourly)
- **HF Space** = Interactive UI (serves Gradio interface)
- **Gradio SDK** = Free tier (no paid Docker needed)

---

## 🔄 Update HF Space After GitHub Changes

### Manual Update
```bash
cd /path/to/hf-space-clone

# Pull latest from your GitHub
# (you'll need to manually copy updated files from GitHub to HF repo)

# Or just copy updated files
cp /workspace/prefect_runs.csv .
cp /workspace/data/quality/quality_report.json data/quality/

# Commit and push to HF
git add .
git commit -m "📊 Update with latest pipeline run"
git push
```

### Automated Sync (Advanced)
Add to your GitHub Actions workflow to auto-push to HF Space:

```yaml
- name: Push to Hugging Face Space
  env:
    HF_TOKEN: ${{ secrets.HF_TOKEN }}
  run: |
    git clone https://$HF_TOKEN@huggingface.co/spaces/YOUR_USERNAME/hackinsight-air-quality-pakistan hf-space
    cd hf-space
    cp ../prefect_runs.csv .
    cp -r ../data/quality ./data/
    cp -r ../data/reports ./data/
    git add .
    git commit -m "🤖 Auto-update from GitHub Actions" || true
    git push
```

---

## ✅ Post-Deployment Checklist

After deploying to HF Space:

- [ ] **Space loads** at your HF URL
- [ ] **Insight Agent tab works** (ask a question)
- [ ] **Pipeline Status shows** (latest run info)
- [ ] **About tab displays** (project info)
- [ ] **Example questions work** (click and test)
- [ ] **Agent says "I don't know"** for unsupported questions
- [ ] **Mobile responsive** (test on phone)
- [ ] **Add HF link to README** (update main repo)

---

## 🆚 Why Gradio Instead of Docker?

| Feature | Docker SDK | Gradio SDK |
|---------|-----------|------------|
| **Cost** | 💰 Paid (requires hardware upgrade) | ✅ **FREE** |
| **Setup** | Complex Dockerfile | Simple Python script |
| **Build Time** | 5-10 minutes | 2-3 minutes |
| **Updates** | Rebuild entire container | Just restart app |
| **Interface** | Custom HTML/CSS | Beautiful pre-built UI |
| **Best For** | Full web apps | ML demos, agents, dashboards |

**For this hackathon:** Gradio is perfect because:
✅ Completely free  
✅ Fast deployment  
✅ Built-in beautiful UI  
✅ Perfect for showing RAG agent  
✅ Interactive question/answer interface  

---

## 📝 Final Notes

### What Gets Deployed
✅ Insight Agent (interactive Q&A)  
✅ Pipeline status viewer  
✅ Quality metrics dashboard  
✅ Project documentation  

### What Doesn't Get Deployed
❌ Full HTML/CSS dashboard (use GitHub Pages for that)  
❌ Live data fetching (uses committed data artifacts)  
❌ Pipeline execution (runs on GitHub Actions only)  

### Why This Works
The Gradio app provides a **clean, interactive interface** to:
1. Ask questions to the RAG Insight Agent
2. View pipeline automation status
3. Show quality metrics
4. Demonstrate project capabilities

For the **full dashboard**, direct users to your GitHub repo or add a GitHub Pages deployment.

---

## 🚀 Ready to Deploy!

**Estimated Time:** 15 minutes  
**Cost:** $0 (completely free)  
**Difficulty:** Easy

**Next Steps:**
1. Create Space on huggingface.co (SDK: Gradio)
2. Clone HF repo
3. Copy files from workspace
4. Push to HF
5. Wait 2-3 minutes
6. Visit your HF Space URL
7. Test Insight Agent
8. ✅ **DONE!**

---

**Support:** If issues persist, check HF Space logs in Settings → Logs

**Alternative:** If Gradio doesn't work, use GitHub Pages for the static HTML dashboard

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
