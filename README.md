
# HackInsight '26 — Karachi Air Quality

**Team Name:** Team Haseen  
**Track:** Air Quality

## Team Members & Roles

| Team Member | Role | Responsibilities |
|---|---|---|
| **Muhammad Taha Farrukh** | Team Lead | Project leadership, team coordination, and overall project direction |
| **Muhammad Uzzam Siddiqui** | Data Cleaning & Modelling | Data cleaning, preprocessing, data quality analysis, and forecasting model development |
| **Uzair Ahmed** | Website Development & Backend | Website development, backend implementation, and dashboard integration |
| **Bilal Rasheed** | Deployment & Documentation | Application deployment, deployment configuration, and project documentation |

## Project Links

- **Live Dashboard:** https://hackinsight-air-quality-pakistan.onrender.com/
- **Hugging Face Space:** Gradio application (`app.py`; see `README_HF.md`)
- **GitHub Repository:** https://github.com/UzairAhmed87/HackInsight-TeamHaseen
- **Release Tag:** `v1.0-final`

## Project Overview

HaseenInsight is an evidence-driven air-quality intelligence system focused on Karachi, Pakistan. It builds a three-source PM2.5 data warehouse with raw, cleaned, and processed layers. A deterministic Data Quality Agent decides whether to FIX, FILL, or FLAG data-quality issues and records its reasoning.

The forecasting component evaluates a next-day PM2.5 model against a persistence baseline using chronological splits, prediction uncertainty, and group-wise error analysis. An evidence-grounded Insight Agent answers questions with traceable citations and abstains when the available evidence is insufficient. A scheduled Prefect pipeline supports automated data processing, while the dashboard communicates source freshness, data quality, cross-source agreement, and model evaluation.
