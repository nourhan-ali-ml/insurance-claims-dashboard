# 🏥 Insurance Claims Analytics Dashboard
### SQL · Power BI · Tableau

An end-to-end analytics project analyzing **162,000 insurance claims** across **100,000 policyholders**, built to demonstrate real-world data engineering, SQL, and BI reporting skills.

---

## 📌 Project Overview

Insurance companies need to understand claim patterns, financial exposure, and risk distribution across their customer base. This project simulates that need by:

- Engineering a **claim-level dataset** from customer-level raw data
- Building a **star schema** database with SQL
- Creating an interactive **Power BI dashboard** (3 pages)
- Publishing a **Tableau Public** version for public access

> **Note:** The original dataset is customer-level (one row per policyholder). A key data engineering step was performed to **explode** each customer's record into individual claim transactions based on `claims_count` and `total_claims_paid` — documented in detail in the SQL files.

---

## 🔍 Key Findings

| Finding | Detail |
|---|---|
| Total Claims Analyzed | 162,178 claims from 100,000 policyholders |
| Overall Approval Rate | 85.15% |
| Avg Processing Time | 11.01 days across all claim types |
| Current Smokers | Claim 56% more on average ($1,213 vs $775) |
| High-Risk vs Standard | High-risk patients show proportionally higher Loss Ratio (345% vs 264%) |
| Network Tier Pattern | Bronze: 354% Loss Ratio vs Platinum: 244% |
| Most Common Claim Type | Lab Test (37,736 claims) |
| Surgery Claims | Fewest in volume (12,787) but highest avg claim amount |

---

## 📁 Project Structure

```
insurance-claims-dashboard/
│
├── sql/
│   ├── schema.sql              ← DDL: CREATE TABLE statements
│   └── queries.sql             ← 10 SQL queries (GROUP BY, JOIN, Window Functions, Views)
│
├── data/
│   ├── fact_claims.csv         ← 162K claim transactions (engineered from raw data)
│   └── vw_monthly_kpis.csv     ← Monthly KPI summary (37 rows)
│
├── dashboard/
│   └── insurance_claims.pbix   ← Power BI Desktop file
│
├── screenshots/
│   ├── 01_claims_overview.png
│   ├── 02_risk_analysis.png
│   └── 03_insights.png
│
├── powerbi_guide.md            ← Full DAX measures + step-by-step guide
└── README.md
```

> **Why is `dim_customers.csv` and `vw_claims_summary.csv` not included?**
> Both exceed GitHub's 25MB file limit. Regenerate by downloading the original
> dataset from Kaggle and running `queries.sql`.

---

## 🛠️ Tools & Technologies

| Tool | Usage |
|---|---|
| **SQL (SQLite / MySQL)** | Schema design, window functions, views |
| **Power BI Desktop** | DAX measures, data modeling, interactive dashboard |
| **Tableau Public** | Alternative visualization layer |
| **Python (pandas)** | Customer-level → claim-level data engineering |

---

## ⚙️ Data Model — Star Schema

```
dim_customers (100,000 rows — dimension table)
      │
      │  customer_id (FK)
      │
fact_claims (162,178 rows — fact table)
      ├── claim_id
      ├── claim_date
      ├── claim_type     (Imaging / Surgery / Physiotherapy / Consultation / Lab Test)
      ├── claim_status   (Approved / Denied / Pending)
      ├── billed_amount
      ├── paid_amount
      ├── processing_days
      ├── region
      └── plan_type
```

---

## 📊 Dashboard Pages

### Page 1 — Claims Overview
KPI Cards · Line Chart (monthly trend) · Bar Chart (by claim type) · Donut (by status)
Slicers: claim_status, plan_type, date range

### Page 2 — Risk Analysis
Decomposition Tree · Scatter Plot (risk_score vs billed_amount) · Top 10 Risk Priority Table
Dynamic DAX Insight Cards

### Page 3 — Insights & Recommendations
Data-backed findings · Business recommendations

---

## 📐 DAX Measures (12 total)

| Category | Measures |
|---|---|
| Basic | Total Claims, Total Billed Amount, Total Paid Amount, Avg Processing Days |
| Rates | Approval Rate %, Denial Rate %, Loss Ratio %, Payment Rate % |
| Risk | High Risk Claims, High Risk Claim Rate %, Avg Risk Score |
| Time Intelligence | YTD Paid Amount, MOM Claims Change %, YOY Claims Growth % |

> Full DAX code in `powerbi_guide.md`

---

## ⚠️ Data Engineering Notes

### Customer-Level → Claim-Level Transformation
Original data had one row per customer. Individual claims were engineered using:
- **Claim amounts:** Gamma-distributed splits of `total_claims_paid`
- **Claim types:** Weighted by each customer's procedure counts
- **Claim status:** 85% Approved / 9% Denied / 6% Pending
- **Claim dates:** Random distribution June 2023 – June 2026

### Loss Ratio Limitation
The absolute Loss Ratio (~300%) is unrealistic for a real insurer because `annual_premium` and synthetic claim amounts were generated independently. Loss Ratio is used here for **comparative analysis only** (high-risk vs standard, tier vs tier).

### Null Values
30,083 apparent nulls in `alcohol_freq` were `"None"` strings (non-drinker) misread by pandas — corrected using `keep_default_na=False`.

---

## 💡 Business Recommendations

1. **Re-evaluate Bronze-tier pricing** — 45% higher Loss Ratio than Platinum suggests underpricing
2. **Implement risk-weighted underwriting** — High-risk patients show proportionally higher claim costs
3. **Factor smoking status into pricing** — Current smokers claim 56% more on average
4. **Review Surgery pre-authorization** — Highest avg claim amount despite low volume
5. **Reduce processing time SLA** — Target under 7 days vs current 11-day average

---

## 🔗 Links
- 📁 **Dataset:** Kaggle — Medical Insurance Dataset

---

*Built with SQL · Power BI · Tableau | 2026*
