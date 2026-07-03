-- ============================================================
-- Insurance Claims Dashboard — Database Schema
-- Star-schema style: dim_customers (dimension) + fact_claims (fact)
-- Compatible with MySQL / PostgreSQL (minor type tweaks noted below)
-- ============================================================

DROP TABLE IF EXISTS fact_claims;
DROP TABLE IF EXISTS dim_customers;

-- ------------------------------------------------------------
-- DIMENSION TABLE: dim_customers
-- One row per policyholder. Demographics, health profile,
-- policy/plan details, and lifetime claims summary.
-- ------------------------------------------------------------
CREATE TABLE dim_customers (
    customer_id                    INT PRIMARY KEY,
    age                            INT,
    sex                            VARCHAR(10),
    region                         VARCHAR(20),
    urban_rural                    VARCHAR(20),
    income                         DECIMAL(12,2),
    education                      VARCHAR(30),
    marital_status                 VARCHAR(20),
    employment_status              VARCHAR(20),
    household_size                 INT,
    dependents                     INT,
    bmi                            DECIMAL(5,2),
    smoker                         VARCHAR(10),
    alcohol_freq                   VARCHAR(15),
    visits_last_year               INT,
    hospitalizations_last_3yrs     INT,
    days_hospitalized_last_3yrs    INT,
    medication_count               INT,
    systolic_bp                    DECIMAL(5,2),
    diastolic_bp                   DECIMAL(5,2),
    ldl                             DECIMAL(6,2),
    hba1c                          DECIMAL(5,2),
    plan_type                      VARCHAR(10),
    network_tier                   VARCHAR(15),
    deductible                     INT,
    copay                          INT,
    policy_term_years              INT,
    policy_changes_last_2yrs       INT,
    provider_quality                DECIMAL(4,2),
    risk_score                     DECIMAL(6,4),
    annual_medical_cost            DECIMAL(12,2),
    annual_premium                 DECIMAL(10,2),
    monthly_premium                DECIMAL(10,2),
    claims_count                   INT,
    avg_claim_amount               DECIMAL(12,2),
    total_claims_paid              DECIMAL(12,2),
    chronic_count                  INT,
    hypertension                   TINYINT,
    diabetes                       TINYINT,
    asthma                         TINYINT,
    copd                           TINYINT,
    cardiovascular_disease         TINYINT,
    cancer_history                 TINYINT,
    kidney_disease                 TINYINT,
    liver_disease                  TINYINT,
    arthritis                      TINYINT,
    mental_health                  TINYINT,
    proc_imaging_count             INT,
    proc_surgery_count             INT,
    proc_physio_count              INT,
    proc_consult_count             INT,
    proc_lab_count                 INT,
    is_high_risk                   TINYINT,
    had_major_procedure            TINYINT
);

-- ------------------------------------------------------------
-- FACT TABLE: fact_claims
-- One row per individual claim transaction.
-- Engineered from dim_customers.claims_count / total_claims_paid
-- (see project notes — original dataset was customer-level only)
-- ------------------------------------------------------------
CREATE TABLE fact_claims (
    claim_id            INT PRIMARY KEY,
    customer_id         INT NOT NULL,
    claim_date          DATE,
    claim_type          VARCHAR(20),       -- Imaging / Surgery / Physiotherapy / Consultation / Lab Test
    billed_amount       DECIMAL(12,2),
    paid_amount         DECIMAL(12,2),
    claim_status        VARCHAR(15),       -- Approved / Denied / Pending
    processing_days     INT,
    region              VARCHAR(20),
    plan_type           VARCHAR(10),
    CONSTRAINT fk_customer
        FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
);

-- Indexes to speed up the most common dashboard filters/aggregations
CREATE INDEX idx_fact_customer ON fact_claims(customer_id);
CREATE INDEX idx_fact_date     ON fact_claims(claim_date);
CREATE INDEX idx_fact_status   ON fact_claims(claim_status);
CREATE INDEX idx_fact_region   ON fact_claims(region);

-- ------------------------------------------------------------
-- NOTES FOR MySQL:
--   - TINYINT is native; DECIMAL works as-is.
-- NOTES FOR PostgreSQL:
--   - Replace TINYINT with SMALLINT.
--   - Loading: use COPY dim_customers FROM '...' CSV HEADER;
-- ------------------------------------------------------------
