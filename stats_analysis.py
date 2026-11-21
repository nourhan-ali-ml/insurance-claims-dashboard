"""
Insurance Claims - Hypothesis Testing & Regression
===================================================
Run from the folder that contains fact_claims.csv and dim_customers.csv:

    pip install pandas numpy scipy statsmodels scikit-posthocs matplotlib
    python stats_analysis.py

Outputs (written to ./stats_output/):
    results.json, smoker_test.png, regression_forest.png, plan_comparison.png

Design notes
------------
* Cost measure = billed_amount (defined for every claim; paid_amount is 0 for
  Denied/Pending claims, which would distort a "cost" comparison).
* Claim cost is heavily right-skewed -> non-parametric tests + log scale.
* Claims are clustered inside customers (ICC ~ 0.5), so claim-level tests would
  treat 162K correlated rows as independent and overstate significance.
    - Hypothesis tests run at CUSTOMER level (one value per customer).
    - Regression runs at CLAIM level with customer-clustered standard errors.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
import scikit_posthocs as sp

RNG = np.random.default_rng(42)
OUT = Path("stats_output")
OUT.mkdir(exist_ok=True)
res = {}

# ---------------------------------------------------------------- load
fc = pd.read_csv("fact_claims.csv")
dc = pd.read_csv(
    "dim_customers.csv",
    usecols=["customer_id", "age", "bmi", "smoker", "plan_type"],
)
claims = fc.drop(columns=["plan_type"]).merge(dc, on="customer_id", how="left")
claims["log_cost"] = np.log(claims["billed_amount"])

# one row per customer: average billed amount per claim
cust = (
    claims.groupby("customer_id")
    .agg(avg_cost=("billed_amount", "mean"),
         n_claims=("claim_id", "count"),
         smoker=("smoker", "first"),
         plan_type=("plan_type", "first"))
    .reset_index()
)
cust["log_avg_cost"] = np.log(cust["avg_cost"])
res["n_claims"] = int(len(claims))
res["n_customers_with_claims"] = int(len(cust))
res["skew_claim_cost"] = float(stats.skew(claims["billed_amount"]))


def boot_ci(a, b, stat, n=5000, alpha=0.05):
    """Percentile bootstrap CI for stat(a) - stat(b)."""
    d = np.empty(n)
    for i in range(n):
        d[i] = stat(RNG.choice(a, len(a))) - stat(RNG.choice(b, len(b)))
    return [float(np.percentile(d, 100 * alpha / 2)),
            float(np.percentile(d, 100 * (1 - alpha / 2)))]


# ------------------------------------------------ 1) smokers vs non-smokers
cur = cust.loc[cust.smoker == "Current", "avg_cost"].to_numpy()
nev = cust.loc[cust.smoker == "Never", "avg_cost"].to_numpy()

u, p_mw = stats.mannwhitneyu(cur, nev, alternative="two-sided")
prob_sup = u / (len(cur) * len(nev))               # P(smoker cost > non-smoker cost)
rank_biserial = 2 * prob_sup - 1

lc_cur, lc_nev = np.log(cur), np.log(nev)
t, p_t = stats.ttest_ind(lc_cur, lc_nev, equal_var=False)
diff = lc_cur.mean() - lc_nev.mean()
se = np.sqrt(lc_cur.var(ddof=1) / len(cur) + lc_nev.var(ddof=1) / len(nev))
dfw = se**4 / ((lc_cur.var(ddof=1) / len(cur))**2 / (len(cur) - 1)
               + (lc_nev.var(ddof=1) / len(nev))**2 / (len(nev) - 1))
tcrit = stats.t.ppf(0.975, dfw)
ratio_ci = [float(np.exp(diff - tcrit * se)), float(np.exp(diff + tcrit * se))]

res["smoker"] = {
    "n_current": int(len(cur)), "n_never": int(len(nev)),
    "mean_current": float(cur.mean()), "mean_never": float(nev.mean()),
    "median_current": float(np.median(cur)), "median_never": float(np.median(nev)),
    "mann_whitney_U": float(u), "mann_whitney_p": float(p_mw),
    "prob_superiority": float(prob_sup), "rank_biserial": float(rank_biserial),
    "welch_t_on_log": float(t), "welch_p": float(p_t),
    "geo_mean_ratio": float(np.exp(diff)), "geo_mean_ratio_ci95": ratio_ci,
    "mean_diff": float(cur.mean() - nev.mean()),
    "mean_diff_ci95_bootstrap": boot_ci(cur, nev, np.mean),
    "median_diff": float(np.median(cur) - np.median(nev)),
    "median_diff_ci95_bootstrap": boot_ci(cur, nev, np.median),
}

# three-group check incl. Former smokers
groups3 = [cust.loc[cust.smoker == g, "avg_cost"] for g in ["Never", "Former", "Current"]]
res["smoker_kruskal_3groups"] = {
    "H": float(stats.kruskal(*groups3).statistic),
    "p": float(stats.kruskal(*groups3).pvalue),
    "median_former": float(groups3[1].median()),
}

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
order = ["Never", "Former", "Current"]
ax[0].boxplot([np.log10(cust.loc[cust.smoker == g, "avg_cost"]) for g in order],
              tick_labels=order, showfliers=False)
ax[0].set_ylabel("log10 avg claim cost per customer ($)")
ax[0].set_title("Claim cost by smoking status (customer level)")
m = [cust.loc[cust.smoker == g, "avg_cost"].mean() for g in order]
lo, hi = [], []
for g in order:
    v = cust.loc[cust.smoker == g, "avg_cost"].to_numpy()
    bs = [RNG.choice(v, len(v)).mean() for _ in range(1000)]
    lo.append(np.percentile(bs, 2.5)); hi.append(np.percentile(bs, 97.5))
ax[1].errorbar(order, m, yerr=[np.array(m) - lo, np.array(hi) - m], fmt="o", capsize=6)
ax[1].set_ylabel("Mean avg claim cost ($)")
ax[1].set_title("Mean with 95% bootstrap CI")
plt.tight_layout(); plt.savefig(OUT / "smoker_test.png", dpi=150); plt.close()

# ------------------------------------------------ 2) regression on claim cost
model_df = claims.dropna(subset=["age", "bmi"]).copy()
ols = smf.ols(
    "log_cost ~ age + bmi + C(smoker, Treatment('Never')) + C(plan_type, Treatment('PPO'))",
    data=model_df,
).fit(cov_type="cluster", cov_kwds={"groups": model_df["customer_id"]})

coef = pd.DataFrame({
    "coef": ols.params,
    "ci_low": ols.conf_int()[0],
    "ci_high": ols.conf_int()[1],
    "p": ols.pvalues,
})
coef["pct_effect"] = (np.exp(coef["coef"]) - 1) * 100
coef["pct_low"] = (np.exp(coef["ci_low"]) - 1) * 100
coef["pct_high"] = (np.exp(coef["ci_high"]) - 1) * 100
res["regression"] = {
    "n_obs": int(ols.nobs), "r_squared": float(ols.rsquared),
    "adj_r_squared": float(ols.rsquared_adj),
    "coefficients": coef.round(5).reset_index().rename(columns={"index": "term"}).to_dict("records"),
}

# robustness: Gamma GLM (log link) on raw cost, same clustered SEs
glm = smf.glm(
    "billed_amount ~ age + bmi + C(smoker, Treatment('Never')) + C(plan_type, Treatment('PPO'))",
    data=model_df, family=sm.families.Gamma(sm.families.links.Log()),
).fit(cov_type="cluster", cov_kwds={"groups": model_df["customer_id"]})
res["glm_gamma_pct_effect"] = {
    k: float((np.exp(v) - 1) * 100) for k, v in glm.params.items() if k != "Intercept"
}

# multicollinearity check on numeric predictors
from statsmodels.stats.outliers_influence import variance_inflation_factor
X = sm.add_constant(model_df[["age", "bmi"]])
res["vif"] = {c: float(variance_inflation_factor(X.values, i))
              for i, c in enumerate(X.columns) if c != "const"}

plot = coef.drop(index="Intercept")
labels = [i.replace("C(smoker, Treatment('Never'))[T.", "smoker: ")
           .replace("C(plan_type, Treatment('PPO'))[T.", "plan: ").replace("]", "")
          for i in plot.index]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
y = np.arange(len(plot))
ax.errorbar(plot["pct_effect"], y,
            xerr=[plot["pct_effect"] - plot["pct_low"], plot["pct_high"] - plot["pct_effect"]],
            fmt="o", capsize=4)
ax.axvline(0, color="grey", ls="--")
ax.set_yticks(y); ax.set_yticklabels(labels)
ax.set_xlabel("% change in claim cost (95% CI, cluster-robust)")
ax.set_title("Regression: effect on claim cost (ref: Never-smoker, PPO)")
plt.tight_layout(); plt.savefig(OUT / "regression_forest.png", dpi=150); plt.close()

# ------------------------------------------------ 3) compare plans
plans = ["PPO", "HMO", "EPO", "POS"]
pg = [cust.loc[cust.plan_type == p, "avg_cost"].to_numpy() for p in plans]
H, p_kw = stats.kruskal(*pg)
N, k = len(cust), len(plans)
eps2 = (H - k + 1) / (N - k)                       # epsilon-squared effect size
F, p_f = stats.f_oneway(*[np.log(g) for g in pg])  # ANOVA on log cost (confirmation)
dunn = sp.posthoc_dunn(cust, val_col="avg_cost", group_col="plan_type", p_adjust="holm")

res["plans"] = {
    "kruskal_H": float(H), "kruskal_p": float(p_kw), "epsilon_squared": float(eps2),
    "anova_log_F": float(F), "anova_log_p": float(p_f),
    "group_stats": {p: {"n": int(len(g)), "mean": float(g.mean()), "median": float(np.median(g))}
                    for p, g in zip(plans, pg)},
    "dunn_holm_p": dunn.loc[plans, plans].round(4).to_dict(),
}

fig, ax = plt.subplots(figsize=(6.5, 4))
means, los, his = [], [], []
for g in pg:
    bs = [RNG.choice(g, len(g)).mean() for _ in range(1000)]
    means.append(g.mean()); los.append(np.percentile(bs, 2.5)); his.append(np.percentile(bs, 97.5))
ax.errorbar(plans, means, yerr=[np.array(means) - los, np.array(his) - means], fmt="o", capsize=6)
ax.set_ylabel("Mean avg claim cost ($)")
ax.set_title(f"Claim cost by plan type (Kruskal-Wallis p={p_kw:.3g})")
plt.tight_layout(); plt.savefig(OUT / "plan_comparison.png", dpi=150); plt.close()

(OUT / "results.json").write_text(json.dumps(res, indent=2, default=float))
print(json.dumps(res, indent=2, default=float))
