"""SAKHI Priority Index dashboard (Bihar prototype, expandable to other states).

Run:  pip install streamlit pandas numpy altair
      streamlit run sakhi_dashboard.py

Data: public NFHS-5 district CSV (github.com/pratapvardhan/NFHS-5), fetched on first run.
If you are offline, save that CSV next to this file as NFHS-5-Districts.csv.
It covers 21 states/UTs (NFHS-5 phase 1 only).
"""
import math
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

URL = "https://raw.githubusercontent.com/pratapvardhan/NFHS-5/master/NFHS-5-Districts.csv"
LOCAL = str(Path(__file__).parent / "data" / "NFHS-5-Districts.csv")
KEYS = {"19.": "hygienic", "15.": "schooling", "14.": "literate", "9.": "sanitation"}
# Bihar averages from the IIPS NFHS-5 Bihar compendium. Other states fall back to the district mean.
STATE_AVG = {"Bihar": {"hygienic": 58.8, "schooling": 28.8, "literate": 57.8, "sanitation": 49.4}}
# Press-reported banana districts in Bihar: must be confirmed with the Horticulture Department.
PRESS_BANANA = {"Bihar": ["Vaishali", "Katihar", "Kishanganj", "Purnia"]}
RESPONSE = {"Full bundle": "School + awareness first, then supply", "Awareness": "Volunteer programme",
            "School facilities": "Five-module school package", "Availability": "Banana-fibre supply chain",
            "No standout gap": "Monitor"}
SEV = ["Critical", "High", "Moderate", "Lower"]
SEV_SCALE = alt.Scale(domain=SEV, range=["#7A1F1F", "#C8742B", "#E0B65C", "#5E8C6A"])
RED = "#A4262C"

# key, label, default, min, step, help. All are planning assumptions from the concept note, not quotes.
PARAMS = [
    ("pads_cycle", "Pads per cycle", 10, 1, 1, "Assumption."),
    ("fibre_g", "Fibre g/pad", 5.0, 0.5, 0.5, "Assumption. Finer precision is not justified without a lab test."),
    ("fibre_price", "Fibre price Rs/kg", 75.0, 0.0, 5.0, "Quote needed. Feeds the cost per pad."),
    ("layers", "Layers + adhesive Rs/pad", 0.80, 0.0, 0.05, "Compostable layers may cost more: get quotes."),
    ("packaging", "Packaging Rs/pad", 0.20, 0.0, 0.05, "Paper sachet that doubles as disposal pouch."),
    ("power", "Power, water, rent Rs/shift/month", 4500.0, 0.0, 500.0, "Assumes rent-free space."),
    ("delivery", "Delivery Rs/pad", 0.10, 0.0, 0.05, "Rides existing school/ASHA/SHG routes."),
    ("qc_year", "Testing + QC Rs/year", 60000.0, 0.0, 5000.0, "Running tests, not the one-off ISO 17088 set."),
    ("speed", "Machine speed pads/min", 4.0, 1.0, 1.0, "2017 press report for a village machine."),
    ("hours", "Productive hours/shift/day", 5.0, 1.0, 1.0, ""),
    ("days", "Working days/month", 25, 1, 1, ""),
    ("gate_pct", "Demand gate (share of one shift)", 0.70, 0.1, 0.05, "Install a unit only above this."),
    ("fibre_kg_ha", "Fibre kg/ha", 500.0, 50.0, 50.0, "ICAR-NRCB range 400-600."),
    ("machine_kg", "Machine kg fibre/month", 75.0, 10.0, 5.0, "From a 2018 field note: about 3 kg a day."),
    ("used_g", "Used pad g", 9.0, 1.0, 1.0, "Implied by Toxics Link totals."),
    ("women_shift", "Women per shift", 4, 1, 1, "Assembly and packing."),
    ("wage", "Wage Rs/month", 10000.0, 0.0, 500.0, "Assumption: set from the state minimum wage."),
    ("women_1524", "Women 15-24 in district (PLACEHOLDER)", 250000, 1000, 10000, "Not data. Replace with a Census-based estimate."),
    ("uptake", "Uptake among non-users (scenario)", 0.50, 0.0, 0.05, "No evidence behind this: use as a scenario only."),
]

MON_COLS = ["month", "girls_attendance_pct", "pads_issued", "stockout_days", "audit_score_avg", "schools_bin_route_pct",
            "batch_pass_pct", "cost_per_pad", "demand_met_pct", "women_employed", "wages_paid", "sessions_held",
            "people_reached", "volunteers_trained"]
METRICS = pd.DataFrame([
    ["Girls' attendance trend", "School registers vs a pre-pilot term (and comparison schools if available)", "girls_attendance_pct", "Set from baseline"],
    ["Pads issued, stock-outs", "Pad corner log", "pads_issued, stockout_days", "Gate: >= demand gate pads/month"],
    ["Audit score", "Ten-point school checklist, 0-10", "audit_score_avg", "Set from baseline"],
    ["Bins + named disposal route", "Share of schools with a lidded bin and a named route", "schools_bin_route_pct", "Court direction: every school"],
    ["Batch pass rate", "Lab reports (IS 5405 + compostability)", "batch_pass_pct", "Gate: 100%, no release without a pass"],
    ["Cost per pad", "Unit accounts", "cost_per_pad", "Gate: <= Rs 3.5"],
    ["Share of demand met", "Pads supplied / pads requested", "demand_met_pct", "Set from baseline"],
    ["Women's work", "Unit records + a feedback meeting", "women_employed, wages_paid", "Projected: 4 per shift"],
    ["Reach", "Attendance sheets", "sessions_held, people_reached, volunteers_trained", "Set from plan"],
], columns=["Metric", "How measured", "Dashboard column", "Target or gate"])


@st.cache_data(show_spinner="Loading NFHS-5 district data...")
def load_raw():
    try:
        return pd.read_csv(LOCAL, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(URL, encoding="utf-8-sig")


def districts(raw, state):
    d = raw[raw["State"].str.lower().str.startswith(state.lower())].copy()
    d["pref"] = d["Indicator"].str.split(" ").str[0]
    d = d[d["pref"].isin(KEYS)]
    d["key"] = d["pref"].map(KEYS)
    d["NFHS-5"] = pd.to_numeric(d["NFHS-5"], errors="coerce")
    d["NFHS-4"] = pd.to_numeric(d["NFHS-4"], errors="coerce")
    t = d.pivot_table(index="District", columns="key", values="NFHS-5")
    t["hygienic_nfhs4"] = d[d["key"] == "hygienic"].set_index("District")["NFHS-4"]
    t = t.reset_index().rename(columns={"District": "district"})
    t["driver_score"] = t[["schooling", "literate", "sanitation"]].mean(axis=1)
    t["rank"] = t["driver_score"].rank(method="first").astype(int)
    return t


def add_gaps(t):
    """Relative deficits (z-scores within the state). The biggest deficit names the main gap."""
    t = t.copy()
    z = lambda c: (t[c] - t[c].mean()) / t[c].std()
    t["aw"] = -(z("schooling") + z("literate")) / 2
    t["fa"] = -z("sanitation") + t["audit"].lt(6).astype(float)  # a weak audit adds to the facilities gap
    t["av"] = -z("hygienic")
    v = t[["aw", "fa", "av"]].to_numpy()
    o, i = np.argsort(-v, axis=1), np.arange(len(t))
    top, second = v[i, o[:, 0]], v[i, o[:, 1]]
    names = np.array(["Awareness", "School facilities", "Availability"])
    t["main"] = names[o[:, 0]]
    t.loc[top < 0.25, "main"] = "No standout gap"
    t["margin"] = top - second
    t["call"] = np.where(t["margin"] >= 0.3, "clear", "close call")
    t["also"] = np.where(second >= 0.5, names[o[:, 1]], "")
    t["severity"] = pd.cut(t["driver_score"].rank(pct=True), [0, .25, .5, .75, 1], labels=SEV)
    multi = (v >= 0.5).sum(axis=1) >= 2
    t["gap"] = t["main"].where(~((t["severity"] == "Critical") & multi), "Full bundle")
    t["weakest"] = names[o[:, 0]]
    t["second"] = names[o[:, 1]]
    fb = t["gap"] == "Full bundle"
    t["gap_detail"] = t["gap"]
    t.loc[fb, "gap_detail"] = "Full bundle: " + t.loc[fb, "weakest"] + " + " + t.loc[fb, "second"]
    t["response"] = t["gap"].map(RESPONSE)
    t.loc[fb, "response"] = ("Full bundle, led by " + t.loc[fb, "weakest"] + " and " + t.loc[fb, "second"] +
                             ": tackle these two first, then review product supply")
    hi = (t["gap"] == "No standout gap") & t["severity"].isin(["Critical", "High"])
    t.loc[hi, "response"] = "Not a clear single gap, but high vulnerability: improve weakest area (" + t.loc[hi, "weakest"] + ")"
    return t


PRIORITIES = {
    "Full bundle": ["Start school facilities and awareness work now (fast, cheap).", "Run the ten-point school audit to find bin, privacy and disposal gaps.", "Review product availability and price; start supply only after the pad passes lab tests."],
    "Awareness": ["Train NSS volunteers, ASHAs and SHG members to run peer sessions.", "Share where to buy pads and how to report stock-outs.", "Include boys and mothers to address stigma."],
    "School facilities": ["Audit toilets: lock, water, soap, light, lidded bin, named disposal route.", "Set up a student-run pad corner with a stock log.", "Name one disposal route out of each school."],
    "Availability": ["Check price and stock in local shops and Kendras first.", "If supply is the real gap, test the banana-fibre pad supply chain (see Pilot site).", "Apply the demand gate before building anything."],
    "No standout gap": ["Keep existing programmes and monitor.", "If severity is High or Critical, work on the weakest area shown."]}
CSS = """<style>
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp td, .stApp th, .stApp input,
.stApp textarea, .stApp button, [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] {font-family: Arial, Helvetica, sans-serif !important;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#FBF6F0 !important; color:#2B1B17 !important}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {background:#F1E2D5 !important}
.stApp p, .stApp li, .stApp label, .stApp td, .stApp th {color:#2B1B17}
.stApp h1, .stApp h2, .stApp h3 {color:#7A1F1F}
[data-testid="stMetric"] {background:#fff; border-left:5px solid #A4262C; padding:.6rem .9rem; border-radius:4px; box-shadow:0 1px 3px #0001}
.hero {background:linear-gradient(135deg,#A4262C,#7A1F1F); padding:2rem; border-radius:8px; margin-bottom:1rem}
.hero h1 {color:#fff !important; font-size:5rem; letter-spacing:.35rem; margin:0; padding:0}
.hero p {color:#FBE9DD !important; font-size:1.2rem; margin:.4rem 0 0}
.grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:.9rem; margin:.6rem 0 1.2rem}
.card {background:#fff; border-top:4px solid #A4262C; border-radius:4px; padding:.9rem 1rem; box-shadow:0 1px 3px #0002}
.card h4 {margin:0 0 .35rem; color:#7A1F1F} .card p {margin:0; font-size:.95rem}
.tag {display:inline-block; background:#F1E2D5; color:#7A1F1F; padding:.1rem .5rem; border-radius:3px; font-size:.8rem; margin-right:.3rem}
</style>"""


def capacity(P):
    return P["speed"] * 60 * P["hours"] * P["days"]


def cost_model(P, pads_month):
    shifts = max(1, math.ceil(pads_month / capacity(P)))
    pm = max(pads_month, 1)
    items = {
        "Banana fibre": P["fibre_g"] / 1000 * P["fibre_price"],
        "Layers + adhesive": P["layers"],
        "Packaging": P["packaging"],
        "Labour": shifts * P["women_shift"] * P["wage"] / pm,
        "Power, water, rent": shifts * P["power"] / pm,
        "Testing + QC": P["qc_year"] / 12 / pm,
        "Delivery": P["delivery"],
    }
    return shifts, items, sum(items.values())


def size_unit(P, schoolgirls, community):
    users = schoolgirls + community
    pads_year = users * P["pads_cycle"] * 12
    pm = pads_year / 12
    shifts, items, cost = cost_model(P, pm)
    fibre = pads_year * P["fibre_g"] / 1000
    return {
        "Users": f"{users:,.0f}",
        "Pads a year / month": f"{pads_year:,.0f} / {pm:,.0f}",
        "Shifts needed": shifts,
        "Demand gate": f"{P['gate_pct'] * capacity(P):,.0f} pads/month: " + ("passes" if pm >= P["gate_pct"] * capacity(P) else "fails, supply from a nearby unit"),
        "Cost per pad": f"Rs {cost:.2f}",
        "State cost for schoolgirls a year": f"Rs {schoolgirls * P['pads_cycle'] * 12 * cost:,.0f} (Rs {P['pads_cycle'] * 12 * cost:,.0f} a girl)",
        "Fibre a year": f"{fibre:,.0f} kg",
        "Banana area needed": f"{fibre / P['fibre_kg_ha']:.1f} ha",
        "Extraction machines (own spoke)": math.ceil(fibre / 12 / P["machine_kg"]),
        "Assembly jobs": shifts * P["women_shift"],
        "Assembly wages a month": f"Rs {shifts * P['women_shift'] * P['wage']:,.0f}",
        "Used-pad waste a year": f"{pads_year * P['used_g'] / 1e6:.1f} tonnes",
    }


def demo_monitoring():
    m = np.arange(0, 13)
    ramp = np.clip((m - 4) / 3, 0, 1)
    return pd.DataFrame({
        "month": m, "girls_attendance_pct": np.round(78 + 8 * ramp, 1), "pads_issued": np.round(21000 * ramp),
        "stockout_days": np.where(m < 5, np.nan, np.maximum(0, 6 - m // 2)), "audit_score_avg": np.round(4 + 4.5 * np.minimum(m / 4, 1), 1),
        "schools_bin_route_pct": np.round(100 * np.minimum(m / 4, 1)), "batch_pass_pct": np.where(m < 5, np.nan, 100.0),
        "cost_per_pad": np.where(m < 5, np.nan, np.round(3.9 - 0.12 * (m - 5), 2)), "demand_met_pct": np.round(90 * ramp),
        "women_employed": np.where(m < 5, 0, 8), "wages_paid": np.where(m < 5, 0, 40000), "sessions_held": np.round(12 * np.minimum(m / 4, 1)),
        "people_reached": np.round(900 * np.minimum(m / 4, 1)), "volunteers_trained": np.round(20 * np.minimum(m / 2, 1))})


def main():
    st.set_page_config(page_title="SAKHI", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    raw = load_raw()
    states = sorted(raw["State"].unique())
    state = st.sidebar.selectbox("State", states, index=states.index("Bihar") if "Bihar" in states else 0)
    st.sidebar.caption(f"{len(states)} states/UTs are in this dataset (NFHS-5 phase 1 only). Phase 2 states such as "
                       "Uttar Pradesh, Madhya Pradesh, Rajasthan, Tamil Nadu and Odisha need another data source.")
    P = {}
    with st.sidebar.expander("Planning assumptions (editable)"):
        for k, label, d, lo, step, h in PARAMS:
            if k in ("gate_pct", "uptake"):
                P[k] = st.slider(label, float(lo), 1.0, float(d), float(step), help=h)
            else:
                P[k] = st.number_input(label, min_value=type(d)(lo), value=d, step=type(d)(step), help=h)

    t = districts(raw, state)
    avg = STATE_AVG.get(state) or t[["hygienic", "schooling", "literate", "sanitation"]].mean().to_dict()
    st.sidebar.caption("Build v4.1 · merged dashboard · light theme")

    ik = f"inputs_{state}"
    if ik not in st.session_state:
        st.session_state[ik] = pd.DataFrame({"district": t["district"], "kendras": np.nan, "audit": np.nan, "stockouts": np.nan})
    t = add_gaps(t.merge(st.session_state[ik], on="district")).sort_values("rank")

    tabs = st.tabs(["Home", "Rank and triage", "Pilot site", "Indicator plots", "Intervention planner", "Unit and cost model", "Pilot monitoring", "Markers and method"])

    with tabs[0]:
        st.markdown(f"""<div class="hero"><h1>SAKHI</h1><p>Menstrual health, safe disposal and local pad supply: a district-by-district decision tool. Now showing: <b>{state}</b>.</p></div>""", unsafe_allow_html=True)
        st.header("What does SAKHI do?")
        st.markdown("It answers three questions in order for every district in the chosen state: **1. Where** is menstrual health weakest? **2. What** is the biggest gap there? **3. What** should be done first, and how should it be delivered?")
        st.header("How is it useful?")
        st.markdown("""<div class="grid">
<div class="card"><h4>Decide where to act</h4><p>Ranks districts on women's schooling, literacy and sanitation, so limited volunteers, pads and funds go where need is greatest.</p></div>
<div class="card"><h4>Match the fix to the gap</h4><p>Each district gets a response: awareness, school facilities, a supply check, or a full bundle.</p></div>
<div class="card"><h4>Plan and cost the supply</h4><p>The cost model works out cost per pad line by line, so changing fibre price, wage or output changes the answer.</p></div>
<div class="card"><h4>Stay honest</h4><p>Measured data, calculated scores and planning assumptions are labelled separately. Nothing is silently filled in.</p></div></div>""", unsafe_allow_html=True)
        st.header("What each tab means")
        st.markdown("""<div class="grid">
<div class="card"><h4>Rank and triage</h4><p>All districts ranked, with severity, main gap, recommended response and indicators. Filter, search, download CSV.</p></div>
<div class="card"><h4>Pilot site</h4><p>Shortlists the most vulnerable districts, then checks banana supply to pick a pilot district.</p></div>
<div class="card"><h4>Indicator plots</h4><p>Charts showing how the indicators relate and how far each district has moved since NFHS-4.</p></div>
<div class="card"><h4>Intervention planner</h4><p>Pick a district: its weak spots, recommended response, target population and next steps.</p></div>
<div class="card"><h4>Unit and cost model</h4><p>Pads, shifts, fibre, banana hectares, jobs and cost per pad, with every step shown and a live what-if table.</p></div>
<div class="card"><h4>Pilot monitoring</h4><p>An empty template for pilot results, with go/no-go gates. Demo data is clearly marked synthetic.</p></div>
<div class="card"><h4>Markers and method</h4><p>Every indicator, its source, how it is used, and the limits of the method.</p></div></div>""", unsafe_allow_html=True)
        st.markdown('<span class="tag">Measured</span> NFHS-5 survey values (2019-21, historical). <span class="tag">Calculated</span> driver score, rank, severity, gaps. <span class="tag">Assumption</span> costs, yields, banana districts, population: editable in the sidebar and unverified.', unsafe_allow_html=True)
        st.info("Use the State box and the Planning assumptions in the sidebar. The tabs above recalculate instantly. Rules are preliminary, not validated predictions.")

    with tabs[1]:
        st.caption("Driver score = mean of schooling 10+, literacy and sanitation (lower = more vulnerable); hygienic use is kept "
                   "out of the score and used to check it. Severity = quartile within the state. The main gap is the district's "
                   "biggest deficit relative to other districts in the state, so rankings are relative, not absolute.")
        rho = t["driver_score"].corr(t["hygienic"], method="spearman")
        c = st.columns(5)
        c[0].metric("Districts ranked", len(t))
        c[1].metric("Below state hygienic-use average", int((t["hygienic"] < avg["hygienic"]).sum()))
        c[2].metric("Critical severity", int((t["severity"] == "Critical").sum()))
        c[3].metric("Close-call main gap", int((t["call"] == "close call").sum()),
                    help="Top two gaps within 0.3 SD of each other: treat the main gap as a coin flip.")
        c[4].metric("Rank correlation: index vs hygienic use", f"{rho:.2f}")
        with st.expander("Optional local data: Jan Aushadhi Kendras, school audit score /10, stock-out reports"):
            st.session_state[ik] = st.data_editor(st.session_state[ik], disabled=["district"], hide_index=True, width="stretch")
        f1, f2, f3 = st.columns(3)
        g = f1.selectbox("Main gap", ["All"] + sorted(t["gap"].unique()))
        sv = f2.multiselect("Severity", SEV, default=SEV)
        q = f3.text_input("Search district")
        v = t[t["severity"].isin(sv)]
        v = v if g == "All" else v[v["gap"] == g]
        v = v[v["district"].str.lower().str.contains(q.lower())] if q else v
        v = v.assign(vs_nfhs4=v["hygienic"] - v["hygienic_nfhs4"])
        cols = ["rank", "district", "severity", "gap_detail", "call", "also", "response", "hygienic", "vs_nfhs4", "schooling", "literate",
                "sanitation", "driver_score"] + [x for x in ["kendras", "audit", "stockouts"] if v[x].notna().any()]
        show = v[cols].round(1)
        low = {k: avg[k] for k in ("hygienic", "schooling", "literate", "sanitation")}
        styled = show.style.apply(lambda col: ["color:#A4262C;font-weight:600" if x < low[col.name] else "" for x in col]
                                  if col.name in low else [""] * len(col), axis=0)
        st.dataframe(styled, width="stretch", hide_index=True)
        st.caption("Orange = below the state average. 'also' = a second gap at least 0.5 SD worse than the state mean. "
                   "vs_nfhs4 is blank where NFHS-4 has no value (districts created after 2015-16). Values describe women aged 15-24, "
                   "not school-going girls. NFHS-5 district data; NFHS-6 not loaded.")
        st.download_button("Export CSV", show.to_csv(index=False), f"sakhi_{state.lower()}_ranking.csv", "text/csv")

    with tabs[2]:
        st.markdown("**Need first, then a supply check on the shortlist.** Banana data is not loaded for every district, so the "
                    "supply check applies only to the most vulnerable districts.")
        n = st.slider("Shortlist: most vulnerable districts", 3, 15, 8)
        min_ha = st.number_input("Minimum banana area to count as supplied (ha)", 0.0, value=10.0,
                                 help="A single-shift unit needs about 3.6 ha a year, so 10 ha is a cautious floor.")
        sk = f"supply_{state}"
        if sk not in st.session_state:
            st.session_state[sk] = pd.DataFrame({"district": t["district"], "banana_ha": np.nan,
                                                 "supply_ok": t["district"].isin(PRESS_BANANA.get(state, []))})
        sub = t.nsmallest(n, "driver_score")[["rank", "district", "hygienic", "driver_score", "gap_detail"]].merge(
            st.session_state[sk], on="district")
        ed = st.data_editor(sub.round(1), hide_index=True, width="stretch",
                            disabled=[x for x in sub.columns if x not in ("banana_ha", "supply_ok")])
        base = st.session_state[sk].set_index("district")
        base.update(ed.set_index("district")[["banana_ha", "supply_ok"]])
        st.session_state[sk] = base.reset_index()
        if state in PRESS_BANANA:
            st.caption("Ticked by default: districts press reports list as banana growers (" + ", ".join(PRESS_BANANA[state])
                       + "). Confirm with the Horticulture Department, then enter hectares.")
        ok = ed[ed["supply_ok"] | (ed["banana_ha"].fillna(0) >= min_ha)]
        if ok.empty:
            st.info("No shortlisted district has confirmed banana supply yet. Enter hectares or tick the box.")
        else:
            p = ok.sort_values("rank").iloc[0]
            st.success(f"Pilot pick: {p.district} (rank {int(p['rank'])} of {len(t)}, hygienic use {p.hygienic:.1f}% against "
                       f"{avg['hygienic']:.1f}% state average, gap: {p.gap_detail}). Demand gate: install a unit only if the catchment "
                       f"fills {P['gate_pct']:.0%} of one shift ({P['gate_pct'] * capacity(P):,.0f} pads a month).")

    with tabs[3]:
        st.caption("Plots of the indicators behind the ranking.")
        tip = ["district", alt.Tooltip("hygienic:Q", format=".1f"), alt.Tooltip("driver_score:Q", format=".1f"), "gap"]
        a, b = st.columns(2)
        a.markdown("**Driver score by district** (lower = more vulnerable)")
        a.altair_chart(alt.Chart(t).mark_bar().encode(
            x=alt.X("driver_score:Q", title=None), y=alt.Y("district:N", sort="x", title=None),
            color=alt.Color("severity:N", scale=SEV_SCALE, sort=SEV), tooltip=tip).properties(height=max(300, 16 * len(t))),
            width="stretch")
        b.markdown("**Does the index track hygienic use?** (dashed = state average)")
        pts = alt.Chart(t).mark_circle(size=70).encode(
            x=alt.X("driver_score:Q", scale=alt.Scale(zero=False), title="Driver score"),
            y=alt.Y("hygienic:Q", scale=alt.Scale(zero=False), title="Hygienic use %"),
            color=alt.Color("severity:N", scale=SEV_SCALE, sort=SEV), tooltip=tip)
        rule = alt.Chart(pd.DataFrame({"y": [avg["hygienic"]]})).mark_rule(strokeDash=[4, 4], color="gray").encode(y="y:Q")
        b.altair_chart(pts + pts.transform_regression("driver_score", "hygienic").mark_line(color="gray") + rule, width="stretch")
        c1, c2 = st.columns(2)
        c1.markdown("**Distribution of hygienic use** across districts")
        c1.altair_chart(alt.Chart(t).mark_bar().encode(alt.X("hygienic:Q", bin=alt.Bin(maxbins=12), title="Hygienic use %"),
                                                       alt.Y("count()", title="Districts")), width="stretch")
        ch = t.dropna(subset=["hygienic_nfhs4"]).assign(change=lambda x: x["hygienic"] - x["hygienic_nfhs4"])
        c2.markdown(f"**Change since NFHS-4** (percentage points, {len(ch)} districts with data)")
        c2.altair_chart(alt.Chart(ch).mark_bar().encode(
            x=alt.X("change:Q", title=None), y=alt.Y("district:N", sort="x", title=None),
            color=alt.condition("datum.change < 0", alt.value("#A4262C"), alt.value("#5E8C6A")),
            tooltip=["district", alt.Tooltip("change:Q", format=".1f")]).properties(height=max(300, 14 * len(ch))), width="stretch")
        d1, d2 = st.columns(2)
        sel = d1.selectbox("District gap profile", list(t["district"]))
        r = t[t["district"] == sel].iloc[0]
        d1.altair_chart(alt.Chart(pd.DataFrame({"gap": ["Awareness", "School facilities", "Availability"], "deficit": [r.aw, r.fa, r.av]}))
                        .mark_bar().encode(x=alt.X("deficit:Q", title="Deficit vs state mean, in SD (right = worse)"),
                                           y=alt.Y("gap:N", sort=None, title=None)).properties(height=140), width="stretch")
        d1.caption(f"{sel}: main gap {r['main']} ({r['call']}), severity {r['severity']}.")
        cm = t[["hygienic", "schooling", "literate", "sanitation"]].corr().round(2).stack().reset_index()
        cm.columns = ["a", "b", "r"]
        d2.markdown("**How redundant are the indicators?** (correlation across districts)")
        heat = alt.Chart(cm).mark_rect().encode(x=alt.X("a:N", title=None), y=alt.Y("b:N", title=None),
                                                 color=alt.Color("r:Q", scale=alt.Scale(scheme="oranges", domain=[0, 1]), legend=None))
        d2.altair_chart(heat + heat.mark_text().encode(text="r:Q", color=alt.value("black")), width="stretch")
        d2.caption("Schooling and literacy move almost together, so the 'awareness' signal is thin. Treat close-call gaps as ties.")

    with tabs[4]:
        sel2 = st.selectbox("Choose a district", list(t["district"]), key="plan")
        r2 = t[t["district"] == sel2].iloc[0]
        st.subheader(f"{sel2}: rank {int(r2['rank'])} of {len(t)} (1 = most vulnerable), severity {r2['severity']}")
        mc = st.columns(4)
        for col, (k, lab) in zip(mc, [("hygienic", "Hygienic use %"), ("schooling", "Schooling 10+ %"), ("literate", "Women literate %"), ("sanitation", "Improved sanitation %")]):
            col.metric(lab, f"{r2[k]:.1f}", f"{r2[k] - avg[k]:+.1f} vs state avg")
        dv = {"Awareness": r2.aw, "School facilities": r2.fa, "Availability": r2.av}
        if r2["gap"] == "Full bundle":
            g1, g2 = r2["weakest"], r2["second"]
            st.markdown(f"**Two main gaps:** **{g1}** ({dv[g1]:+.1f} SD worse than the state mean) and **{g2}** ({dv[g2]:+.1f} SD). This district is in the full bundle because at least two gaps are large.")
        else:
            st.markdown(f"**Main gap:** {r2['gap']} ({r2['call']})" + (f". Also weak: {r2['also']}." if r2["also"] else "."))
        st.markdown(f"**Recommended response:** {r2['response']}")
        st.markdown("**Implementation priorities**")
        if r2["gap"] == "Full bundle":
            for gname in (r2["weakest"], r2["second"]):
                st.markdown(f"*For {gname}:*")
                for x in PRIORITIES[gname]:
                    st.markdown(f"- {x}")
            st.markdown("*Sequence:* facilities and awareness first (fast, cheap); start product supply only after the pad passes lab tests.")
        else:
            for x in PRIORITIES.get(r2["gap"], []):
                st.markdown(f"- {x}")
        non2 = P["women_1524"] * (1 - r2["hygienic"] / 100)
        st.write(f"Indicative target population: about **{non2:,.0f}** women aged 15-24 not using a hygienic method ({P['women_1524']:,.0f} is a PLACEHOLDER population; replace it in the sidebar).")
        st.altair_chart(alt.Chart(pd.DataFrame({"gap": ["Awareness", "School facilities", "Availability"], "deficit": [r2.aw, r2.fa, r2.av]})).mark_bar(color=RED).encode(
            x=alt.X("deficit:Q", title="Deficit vs state mean, in SD (right = worse)"), y=alt.Y("gap:N", sort=None, title=None)).properties(height=140), width="stretch")

    with tabs[5]:
        st.caption("All values come from the sidebar assumptions. Cost per pad is computed from its parts, so changing fibre price, "
                   "wage or output changes it.")
        cap = capacity(P)
        st.write(f"One shift makes about **{cap:,.0f} pads a month** ({P['speed']:.0f} pads/min x {P['hours']:.0f} h x {P['days']} days).")
        a, b, c3 = st.columns(3)
        pick = a.selectbox("District", list(t["district"]), key="sizepick")
        sg = b.number_input("Schoolgirls (Classes 6-12)", 0, value=1500, step=100)
        cw = c3.number_input("Community women", 0, value=1500, step=100)
        l, rgt = st.columns(2)
        l.markdown(f"**Unit sizing for {pick}**")
        l.table(pd.Series(size_unit(P, sg, cw), name="Result").astype(str))
        users = sg + cw
        shifts, items, total = cost_model(P, users * P["pads_cycle"])
        rgt.markdown(f"**Cost per pad: Rs {total:.2f}**")
        rgt.altair_chart(alt.Chart(pd.DataFrame({"item": list(items), "Rs": list(items.values())})).mark_bar().encode(
            x=alt.X("Rs:Q", title="Rs per pad"), y=alt.Y("item:N", sort="-x", title=None), tooltip=["item", alt.Tooltip("Rs:Q", format=".2f")]
        ).properties(height=240), width="stretch")
        per_kg = P["wage"] / P["machine_kg"]
        flag = "above" if per_kg > P["fibre_price"] else "within"
        rgt.info(f"Fibre reality check: one operator at Rs {P['wage']:,.0f}/month on a machine making {P['machine_kg']:.0f} kg/month "
                 f"implies about Rs {per_kg:,.0f}/kg in labour alone, {flag} the Rs {P['fibre_price']:.0f}/kg fibre price. "
                 "If above, buy dry fibre from existing units at a quoted price instead of running your own spoke.")
        st.markdown("**How the cost per pad is calculated, step by step**")
        fm = {"Banana fibre": f"{P['fibre_g']:g} g / 1000 x Rs {P['fibre_price']:.0f} per kg", "Layers + adhesive": "input, Rs per pad", "Packaging": "input, Rs per pad",
              "Labour": f"{shifts} shift(s) x {P['women_shift']} women x Rs {P['wage']:,.0f} / pads per month", "Power, water, rent": f"{shifts} shift(s) x Rs {P['power']:,.0f} / pads per month",
              "Testing + QC": f"Rs {P['qc_year']:,.0f} / 12 months / pads per month", "Delivery": "input, Rs per pad"}
        st.dataframe(pd.DataFrame({"Cost line": list(items), "How it is worked out": [fm[k] for k in items], "Rs per pad": [round(v, 2) for v in items.values()],
                                   "Share": [f"{v / total:.0%}" for v in items.values()]}), hide_index=True, width="stretch")
        pmn = users * P["pads_cycle"]
        st.caption(f"Pads per month = {users:,} users x {P['pads_cycle']} pads = {pmn:,}. Cost per pad = sum of the lines = Rs {total:.2f}. Labour, power and testing are fixed costs spread over output, "
                   "so cost falls as output rises and climbs if the unit runs below capacity.")
        st.markdown("**What-if: change one thing and see the cost per pad (live, from your inputs)**")
        sc = [("Your inputs", P, pmn), ("Fibre price +Rs 50/kg", {**P, "fibre_price": P["fibre_price"] + 50}, pmn), ("Compostable layers at Rs 1.20/pad", {**P, "layers": 1.2}, pmn),
              ("Wage +Rs 5,000/month", {**P, "wage": P["wage"] + 5000}, pmn), ("Fibre 8 g per pad", {**P, "fibre_g": 8.0}, pmn),
              ("Half the output", P, pmn / 2), ("Double the output", P, pmn * 2)]
        rows = []
        for lab, pp, pm_ in sc:
            sh_, _, tt = cost_model(pp, pm_)
            rows.append([lab, f"{pm_:,.0f}", sh_, round(tt, 2), round(tt - total, 2)])
        st.dataframe(pd.DataFrame(rows, columns=["Scenario", "Pads/month", "Shifts", "Cost per pad (Rs)", "Change vs yours (Rs)"]), hide_index=True, width="stretch")
        st.markdown("**District-wide scenario** (needs a real population figure and an uptake assumption)")
        h = float(t.loc[t["district"] == pick, "hygienic"].iloc[0])
        non = P["women_1524"] * (1 - h / 100)
        adopt = non * P["uptake"]
        py = adopt * P["pads_cycle"] * 12
        s2, _, c2 = cost_model(P, py / 12)
        st.write(f"{pick}: {P['women_1524']:,.0f} women aged 15-24 (placeholder) x {100 - h:.1f}% not using a hygienic method = "
                 f"{non:,.0f}; at {P['uptake']:.0%} uptake that is {adopt:,.0f} users, {py:,.0f} pads a year, {s2} shift(s) of capacity "
                 f"(about {s2 / 2:.1f} two-shift units), at about Rs {c2:.2f} a pad.")

    with tabs[6]:
        st.markdown("**Metrics we will measure in the pilot.** This is a template: it stays empty until the pilot produces data. "
                    "Nothing here is a result.")
        st.dataframe(METRICS, hide_index=True, width="stretch")
        up = st.file_uploader("Load a monitoring CSV (columns: " + ", ".join(MON_COLS) + ")", type="csv")
        demo = st.toggle("Show SYNTHETIC demo data (layout only, not real)")
        if "mon" not in st.session_state:
            st.session_state["mon"] = pd.DataFrame(columns=MON_COLS).astype(float)
        if up is not None:
            st.session_state["mon"] = pd.read_csv(up).reindex(columns=MON_COLS)
        mon = demo_monitoring() if demo else st.data_editor(st.session_state["mon"], num_rows="dynamic", width="stretch", key="moned")
        if not demo:
            st.session_state["mon"] = mon
        else:
            st.warning("SYNTHETIC DEMO DATA: made up to show the layout. Not pilot results.")
        mon = mon.dropna(subset=["month"]) if len(mon) else mon
        if len(mon):
            last = mon.sort_values("month").iloc[-1]
            gate = P["gate_pct"] * cap
            g1, g2, g3 = st.columns(3)
            g1.metric("Cost per pad vs gate (<= Rs 3.5)", "n/a" if pd.isna(last.cost_per_pad) else f"Rs {last.cost_per_pad:.2f}",
                      None if pd.isna(last.cost_per_pad) else ("pass" if last.cost_per_pad <= 3.5 else "fail"), delta_color="off")
            g2.metric(f"Pads issued vs gate ({gate:,.0f})", "n/a" if pd.isna(last.pads_issued) else f"{last.pads_issued:,.0f}",
                      None if pd.isna(last.pads_issued) else ("pass" if last.pads_issued >= gate else "below"), delta_color="off")
            g3.metric("Batch pass rate (gate: 100%)", "n/a" if pd.isna(last.batch_pass_pct) else f"{last.batch_pass_pct:.0f}%",
                      None if pd.isna(last.batch_pass_pct) else ("pass" if last.batch_pass_pct >= 100 else "fail"), delta_color="off")
            m = mon.set_index("month").sort_index()
            for title, cols in [("Girls' attendance %", ["girls_attendance_pct"]), ("Pads issued and demand met %", ["pads_issued", "demand_met_pct"]),
                                ("Audit score and bins + route %", ["audit_score_avg", "schools_bin_route_pct"]), ("Cost per pad (Rs)", ["cost_per_pad"]),
                                ("Women's work", ["women_employed", "sessions_held", "volunteers_trained"])]:
                st.markdown(f"**{title}**")
                st.line_chart(m[cols])
        st.download_button("Download monitoring CSV", st.session_state["mon"].to_csv(index=False), "sakhi_monitoring.csv", "text/csv")

    with tabs[7]:
        mk = pd.DataFrame([
            ["NFHS-5 outcome", "Women 15-24 using a hygienic method (%)", "Public (IIPS district fact sheets)", "Checks the index; sets Availability gap"],
            ["NFHS-5 driver", "Women with 10+ years of schooling (%)", "Public", "Awareness gap, driver score"],
            ["NFHS-5 driver", "Women who are literate (%)", "Public", "Awareness gap, driver score"],
            ["NFHS-5 driver", "Population in households with improved sanitation (%)", "Public", "School-facilities gap, driver score"],
            ["NFHS-4 trend", "Hygienic use in NFHS-4 (%)", "Public", "Change since NFHS-4"],
            ["Derived", "Driver score, rank, severity quartile, z-score gaps, main gap, close-call flag", "Computed", "Triage"],
            ["Optional input", "Jan Aushadhi Kendras per district", "PMBI list (not loaded)", "Reach gap"],
            ["Optional input", "School audit score /10 (ten-point checklist)", "Teacher + student lead", "Adds to the facilities gap if below 6"],
            ["Optional input", "Stock-out reports", "SAKHI log / CPGRAMS", "Supply feedback"],
            ["Supply check", "Banana area (ha) for shortlisted districts", "State horticulture data (not loaded)", "Pilot-site rule"],
            ["Sizing assumptions", "Pads per cycle, fibre g/pad and price, layers, packaging, power, delivery, QC, machine speed, hours, days, "
                                   "demand gate, fibre kg/ha, machine kg, used-pad g, women per shift, wage, population, uptake", "Concept note (assumptions)", "Unit and cost model"],
            ["Pilot measures", "Attendance, pads issued, stock-outs, audit, bins + route, batch pass, cost per pad, demand met, jobs, wages, reach", "Collected in the pilot", "Monitoring tab"],
        ], columns=["Type", "Marker", "Source", "Used for"])
        st.dataframe(mk, hide_index=True, width="stretch")
        st.markdown("""**Limits.** Gaps are relative to other districts in the same state, and a district can be flagged even when it is fine in
absolute terms. Schooling and literacy are almost the same signal, and about four in ten districts in Bihar have a close call between their top two
gaps, so treat the main gap as a way to sequence work, not a diagnosis. Mapping indicators to gaps is an assumption, not a validated model.
The data describe women aged 15-24, not school-going girls.""")


if __name__ == "__main__":
    main()