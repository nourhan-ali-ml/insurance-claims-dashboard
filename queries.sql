-- ============================================================
-- Insurance Claims Dashboard — Practice Queries
-- Written/tested against SQLite (insurance_claims.db)
-- MySQL/PostgreSQL syntax notes added where it differs
-- ============================================================

-- 1) BASIC: Claim counts by status
SELECT claim_status, COUNT(*) AS num_claims
FROM fact_claims
GROUP BY claim_status
ORDER BY num_claims DESC;


-- 2) BASIC: Approval rate overall
SELECT
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS approval_rate_pct
FROM fact_claims;


-- 3) GROUP BY: Average processing days and total paid amount per claim type
SELECT
    claim_type,
    COUNT(*)                       AS num_claims,
    ROUND(AVG(processing_days), 1) AS avg_processing_days,
    ROUND(SUM(paid_amount), 2)     AS total_paid
FROM fact_claims
GROUP BY claim_type
ORDER BY total_paid DESC;


-- 4) GROUP BY + HAVING: Regions with approval rate below 80%
SELECT
    region,
    COUNT(*) AS total_claims,
    ROUND(100.0 * SUM(CASE WHEN claim_status='Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS approval_rate_pct
FROM fact_claims
GROUP BY region
HAVING approval_rate_pct < 80
ORDER BY approval_rate_pct;


-- 5) JOIN: Claims volume and average claim amount by age group and plan type
SELECT
    CASE
        WHEN c.age < 30 THEN 'Under 30'
        WHEN c.age BETWEEN 30 AND 49 THEN '30-49'
        WHEN c.age BETWEEN 50 AND 64 THEN '50-64'
        ELSE '65+'
    END AS age_group,
    f.plan_type,
    COUNT(*)                    AS num_claims,
    ROUND(AVG(f.billed_amount), 2) AS avg_billed_amount
FROM fact_claims f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY age_group, f.plan_type
ORDER BY age_group, f.plan_type;


-- 6) JOIN: Are smokers / high-risk customers filing larger claims?
SELECT
    c.smoker,
    c.is_high_risk,
    COUNT(f.claim_id)              AS num_claims,
    ROUND(AVG(f.billed_amount), 2) AS avg_billed_amount,
    ROUND(SUM(f.paid_amount), 2)   AS total_paid
FROM dim_customers c
LEFT JOIN fact_claims f ON c.customer_id = f.customer_id
GROUP BY c.smoker, c.is_high_risk
ORDER BY avg_billed_amount DESC;


-- 7) WINDOW FUNCTION: Rank customers by total paid claims (Top 10)
SELECT
    customer_id,
    total_paid,
    RANK() OVER (ORDER BY total_paid DESC) AS paid_rank
FROM (
    SELECT customer_id, SUM(paid_amount) AS total_paid
    FROM fact_claims
    GROUP BY customer_id
) t
ORDER BY paid_rank
LIMIT 10;


-- 8) WINDOW FUNCTION: Month-over-month claims trend with LAG
-- SQLite: use strftime('%Y-%m', claim_date)
-- MySQL:  use DATE_FORMAT(claim_date, '%Y-%m')
-- Postgres: use TO_CHAR(claim_date, 'YYYY-MM')
SELECT
    month,
    num_claims,
    LAG(num_claims) OVER (ORDER BY month) AS prev_month_claims,
    ROUND(
        100.0 * (num_claims - LAG(num_claims) OVER (ORDER BY month))
        / LAG(num_claims) OVER (ORDER BY month), 2
    ) AS mom_growth_pct
FROM (
    SELECT strftime('%Y-%m', claim_date) AS month, COUNT(*) AS num_claims
    FROM fact_claims
    GROUP BY month
) monthly
ORDER BY month;


-- 9) VIEW: Pre-aggregated summary for Power BI to connect to directly
-- v2: added policy/premium columns so Loss Ratio can be computed correctly
-- (Paid Claims / Premiums Earned, not Paid / Billed)
DROP VIEW IF EXISTS vw_claims_summary;
CREATE VIEW vw_claims_summary AS
SELECT
    f.claim_id,
    f.customer_id,
    f.claim_date,
    strftime('%Y-%m', f.claim_date) AS claim_month,
    f.claim_type,
    f.claim_status,
    f.billed_amount,
    f.paid_amount,
    f.processing_days,
    f.region,
    f.plan_type,
    c.age,
    c.sex,
    c.marital_status,
    c.employment_status,
    c.smoker,
    c.is_high_risk,
    c.chronic_count,
    c.risk_score,
    -- newly added policy / provider attributes
    c.annual_premium,
    c.monthly_premium,
    c.deductible,
    c.copay,
    c.network_tier,
    c.policy_term_years,
    c.policy_changes_last_2yrs,
    c.provider_quality,
    -- per-claim share of this customer's annual premium (premium allocated proportionally
    -- across that customer's claims, so SUM(premium_allocated) per customer = annual_premium)
    ROUND(c.annual_premium * 1.0 / NULLIF(c.claims_count, 0), 2) AS premium_allocated
FROM fact_claims f
JOIN dim_customers c ON f.customer_id = c.customer_id;

-- Quick check on the view
SELECT * FROM vw_claims_summary LIMIT 5;


-- 10) VIEW: Monthly KPI rollup (handy for a trend visual in Power BI)
DROP VIEW IF EXISTS vw_monthly_kpis;
CREATE VIEW vw_monthly_kpis AS
SELECT
    strftime('%Y-%m', claim_date)                                   AS claim_month,
    COUNT(*)                                                        AS total_claims,
    SUM(paid_amount)                                                AS total_paid,
    ROUND(100.0 * SUM(CASE WHEN claim_status='Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS approval_rate_pct,
    ROUND(AVG(processing_days), 1)                                  AS avg_processing_days
FROM fact_claims
GROUP BY claim_month
ORDER BY claim_month;

SELECT * FROM vw_monthly_kpis LIMIT 12;
