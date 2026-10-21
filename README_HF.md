---
title: HackInsight Air Quality Pakistan
emoji: 🌍
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app_gradio.py
pinned: false
license: cc-by-4.0
tags:
  - air-quality
  - pakistan
  - data-pipeline
  - forecasting
  - rag
---

# HackInsight '26 — Air Quality Intelligence for Pakistan

**Live Dashboard:** This Space shows automated hourly data quality monitoring, historical forecasting, and evidence-grounded insights.

## 🎯 Hackathon Submission

**Track:** Air Quality  
**Team:** TeamHaseen  
**Problem:** Real-time air quality intelligence for Pakistan with traceable, journal-quality data

## 🏗️ What This System Does

### 1. **Automated Data Warehouse** 
- **2 Independent Sources:** PAQI (Zenodo CC BY 4.0) + AirGradient (live sensors)
- **Raw → Cleaned → Processed** layers rebuilt hourly with `make data`
- **Traceable Provenance:** SHA-256 row-level lineage + manifest ledger

### 2. **Data Quality Agent**
- Deterministic rule-based validation
- **Fix/Fill/Flag** decisions with explanations
- Logged to `quality_log.csv` and `quality_report.json`

### 3. **Forecasting Model**
- **Linear regression** beats persistence baseline
- Time-based train/val/test splits (2016-2024)
- **Uncertainty intervals** from validation residuals
- **Errors by group** (yearly breakdown)

### 4. **Insight Agent (RAG)**
- Evidence-grounded answers from gold data
- **Cites sources** (never invents facts)
- Says **"I don't know"** for unsupported queries

### 5. **Automated Pipeline + Dashboard**
- ⏰ **Hourly GitHub Actions** workflow
- 📊 Shows data freshness, quality status, last successful run
- 🔄 Logs every run to `prefect_runs.csv`

## 📊 Dashboard Features

✅ **Historical Analysis:** 2016-2024 PAQI PM2.5 data  
✅ **Quality Monitoring:** Real-time validation status  
✅ **Forecast Evaluation:** Model vs baseline comparison  
✅ **Live Sensors:** AirGradient neighbourhood monitoring  
✅ **Insight Chat:** Ask questions, get cited answers  
✅ **Dark Mode:** Professional UI with WCAG AAA contrast  
✅ **Export:** Download data as CSV or charts as PNG  

## 🔄 Automation Status

**Last Run:** Check `prefect_runs.csv` for latest execution  
**Frequency:** Every hour via GitHub Actions  
**Monitoring:** Quality checks, row counts, execution time

## 📚 Data Sources

1. **PAQI Karachi PM2.5 Dataset**
   - Publisher: Pakistan Air Quality Initiative
   - License: CC BY 4.0
   - DOI: 10.5281/zenodo.7491417
   - Coverage: 2016-10-06 to 2024-12-31

2. **AirGradient Public Sensors**
   - Publisher: AirGradient
   - License: Public API
   - Source: The Urban Unit neighbourhood monitors
   - Type: Live point readings (not citywide)

## 🎓 Academic Quality

This dataset meets journal submission standards:
- ✅ Reproducible with one command
- ✅ Fully traceable lineage
- ✅ Licensed and attributed
- ✅ Quality validated
- ✅ No synthetic/AI-generated data

## 📖 Repository

**GitHub:** [UzairAhmed87/HackInsight-TeamHaseen](https://github.com/UzairAhmed87/HackInsight-TeamHaseen)

**Documentation:**
- `README.md` - Full technical documentation
- `Summary.pdf` - One-page submission summary
- `AI_Use_Log.md` - AI assistance log
- `prefect_runs.csv` - Automation execution log

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/UzairAhmed87/HackInsight-TeamHaseen.git
cd HackInsight-TeamHaseen

# Run the data pipeline
make data

# Run forecasting
make forecast

# Start dashboard
make dashboard
```

## 🔬 Technical Stack

- **Pipeline:** Pure Python 3.12+ (standard library only)
- **Automation:** GitHub Actions (hourly schedule)
- **Dashboard:** Vanilla HTML/CSS/JS + Python HTTP server
- **Model:** Scikit-learn linear regression
- **Validation:** Deterministic rule-based quality checks

## 📊 Key Metrics

- **Data Points:** 3,009 daily observations
- **Coverage:** 8+ years (2016-2024)
- **Quality Checks:** 15+ validation rules
- **Model Performance:** Beats persistence baseline
- **Automation:** 100% automated pipeline

## 🏆 Hackathon Requirements Met

✅ 2+ independent sources  
✅ Traceable, licensed, documented  
✅ Data Quality Agent (fix/fill/flag)  
✅ Model beats baseline with uncertainty  
✅ RAG Insight Agent (cited, says "I don't know")  
✅ Hourly automated pipeline  
✅ Dashboard shows freshness/quality/last run  
✅ GitHub repo with v1.0-final tag  
✅ Hugging Face Space deployment  
✅ Demo video  
✅ Complete documentation  

## 📄 License

**Data:** CC BY 4.0 (PAQI dataset)  
**Attribution Required:** Omar Abid, Dawar Hameed Butt, Mahad Naveed, PAQI

---

**Built for HackInsight '26 Hackathon**  
*Automated pipeline + agentic AI for air quality intelligence*
