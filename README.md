# SAKHI: a district decision tool for menstrual health, safe disposal and local pad supply

[**Open the live app**](https://sakhi1234.streamlit.app/) · Built for the Seva First Innovation Challenge 2026 (Theme 3, Swasth & Samavesh Bharat)

SAKHI helps a district officer, NGO or CSR team answer three questions, in order, for every district in a state:

1. **Where** is menstrual health weakest?
2. **What** is the biggest gap there: awareness, school facilities, or availability of pads?
3. **What** should be done first, and how much would a local pad supply unit cost?

It turns public NFHS-5 district data into a ranked list with a recommended response for each district, and it links that list to a cost model for a small banana-fibre pad unit.

> **Status.** This is a planning prototype. The survey figures are real public data. The cost, yield and population figures are **planning assumptions** that you can edit in the sidebar, and they are not quotes. No pad has been built or tested, and no pilot has been run.

---

## Why this exists

Menstrual health gaps are uneven. In NFHS-5 (2019-21), about 78% of women aged 15-24 in India use a hygienic method of protection, but the figure is 59% in Bihar, the lowest state, and it varies a lot between districts within a state. Programmes usually hand out one thing everywhere, such as pads or a talk. SAKHI helps decide where to work first, and which of three problems to tackle there.

## What you can do in the app

Pick a state in the sidebar. Every tab recalculates for that state.

| Tab | What it shows |
|---|---|
| **Home** | What SAKHI does, how it helps, and what each tab means. |
| **Rank and triage** | All districts ranked by vulnerability, with severity band, main gap, recommended response and indicators. Filter, search and download as CSV. |
| **Pilot site** | Shortlists the most vulnerable districts, then checks banana supply to choose a pilot district. |
| **Indicator plots** | How the indicators relate to each other and how far each district has moved since NFHS-4. |
| **Intervention planner** | Pick one district and see its weak spots, recommended response, target population and next steps. |
| **Unit and cost model** | Pads, shifts, fibre, banana hectares, jobs and cost per pad, line by line, with a live what-if table. |
| **Pilot monitoring** | An empty template for pilot results with go/no-go gates. Demo data is marked synthetic. |
| **Markers and method** | Every indicator, its source, how it is used, and the limits of the method. |

## How the ranking works

**Data (measured).** Four NFHS-5 district indicators, all from the public IIPS district fact sheets:

| Role | Indicator |
|---|---|
| Outcome (kept out of the score, used to check it) | Women aged 15-24 using a hygienic method of menstrual protection (%) |
| Driver | Women with 10 or more years of schooling (%) |
| Driver | Women who are literate (%) |
| Driver | Population living in households with an improved sanitation facility (%) |

The NFHS-4 value of the outcome is also used to show change since 2015-16.

**Steps (calculated).**

1. **Driver score.** The mean of the three driver indicators. Lower means more vulnerable. Districts are ranked on this score.
2. **Severity.** The district's quartile within its own state: Critical, High, Moderate or Lower.
3. **Main gap.** Each district gets three deficit scores, measured as z-scores against the other districts in the state:
   - *Awareness*: low schooling and low literacy
   - *School facilities*: low sanitation (a school audit score below 6 out of 10 adds to this)
   - *Availability*: low hygienic-method use
   
   The largest deficit names the main gap. If no deficit is large enough, the district is marked "No standout gap". If a Critical district has two or more large deficits, it is marked "Full bundle". A "close call" flag appears when the top two gaps are nearly equal.
4. **Response.** Each gap maps to a response: a volunteer programme (awareness), the five-module school package (facilities), a banana-fibre supply chain (availability), or a combined bundle.
5. **Validation.** The app reports the Spearman rank correlation between the driver score and the hygienic-use outcome. This checks whether the score tracks the outcome. It is a check, not proof that the response will work.

**Cost model.** Cost per pad is built from its parts: banana fibre, layers and adhesive, packaging, labour, power and rent, testing and delivery. Fixed costs are spread over output, so changing the fibre price, wage, machine speed or number of shifts changes the answer. All inputs are in the sidebar under **Planning assumptions (editable)**.

## Data

- **File:** `data/NFHS-5-Districts.csv`, a public district-level extract of the NFHS-5 fact sheets (source: [github.com/pratapvardhan/NFHS-5](https://github.com/pratapvardhan/NFHS-5)). The app loads the local copy first and falls back to downloading it if the file is missing.
- **Coverage:** 21 states and Union Territories, which is NFHS-5 **phase 1** only (about 340 districts). Phase 2 states such as Uttar Pradesh, Madhya Pradesh, Rajasthan, Tamil Nadu and Odisha are **not** in this file and would need another source.
- **Bihar:** all 38 districts. Bihar state averages used in the app (hygienic use 58.8%, schooling 28.8%, literacy 57.8%, sanitation 49.4%) come from the IIPS NFHS-5 Bihar compendium. Other states use the mean of their districts.
- **Spot check:** five Bihar districts (Araria, Arwal, Aurangabad, Banka, Begusarai) were compared with the IIPS Bihar compendium, and all four indicators matched. The other districts have not been checked. Verify any district you plan to cite against its IIPS fact sheet.
- **Primary source:** IIPS and ICF, *National Family Health Survey (NFHS-5), State and District Fact Sheets* ([rchiips.org/nfhs](http://rchiips.org/nfhs)). Cite this, not the extract.

## Limits you should know about

- **Women aged 15-24, not school-going girls.** The data show where need is likely highest. They do not measure school absenteeism.
- **Gaps are relative.** A district can be flagged even when it does well in absolute terms, because it is compared with other districts in the same state.
- **Schooling and literacy are almost the same signal.** About four in ten Bihar districts have a close call between their top two gaps. Use the main gap to sequence work. It is not a diagnosis.
- **The mapping from indicators to gaps is an assumption.** It is not a validated predictive model, and the thresholds are preliminary.
- **The data are historical.** NFHS-5 fieldwork ran in 2019-21. NFHS-6 district data were not used.
- **Banana districts are not data in the app.** The "press-reported" banana districts for Bihar (Vaishali, Katihar, Kishanganj, Purnia) come from news reports. Confirm banana area with the state Horticulture Department before relying on them.
- **Placeholders.** The women-aged-15-24 population per district and the uptake rate are placeholders and scenario values, not data.
- **Banana-fibre pads are unproven here.** No pad has been made or tested by this project. Any real unit needs testing under the Indian standard for sanitary napkins (IS 5405), compostability testing if compostable claims are made, and the certification route confirmed with BIS.

## Run it on your computer

Requires Python 3.9 or newer.

```bash
git clone https://github.com/Navya1028/sakhi.git
cd sakhi
pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub, with `app.py`, `requirements.txt`, `data/` and `.streamlit/` at the top level.
2. On [share.streamlit.io](https://share.streamlit.io), choose **New app**, select the repository and branch, and set the main file to `app.py`.
3. Deploy. Every `git push` rebuilds the app automatically.

**Troubleshooting.** If the app shows `ModuleNotFoundError`, a package is missing from `requirements.txt`. The error on the page is redacted, so open **Manage app** and read the logs. The `scipy` error seen earlier is fixed in this version: the Spearman correlation is computed from ranks and no longer needs `scipy` at all, although `scipy` is still listed.

## Repository layout

```
sakhi/
├── app.py                      # the whole Streamlit app
├── requirements.txt            # streamlit, pandas, numpy, scipy, altair
├── data/
│   └── NFHS-5-Districts.csv    # public NFHS-5 district indicators
├── .streamlit/
│   └── config.toml             # light theme
└── README.md
```

## Extending it

- **Add a state:** if the state is in the CSV, it appears in the sidebar automatically. For a phase 2 state, add its district rows in the same format (`State, State-Code, District, Indicator, NFHS-5, NFHS-4`) and make sure indicator names begin with the same numbers as in the CSV (9, 14, 15 and 19), since the app finds them by number.
- **Add state averages:** edit `STATE_AVG` in `app.py` with figures from the IIPS state fact sheet.
- **Add banana districts:** edit `PRESS_BANANA` in `app.py`, or replace it with horticulture department data.
- **Use real pilot data:** upload a CSV in the **Pilot monitoring** tab using the column names shown there.

## Colour and labelling

The app keeps three kinds of numbers apart on screen: **Measured** (NFHS-5 survey values), **Calculated** (scores, ranks, gaps) and **Assumption** (costs, yields, population, banana districts). Nothing is filled in silently.

## Credits and licence

- Data: International Institute for Population Sciences (IIPS) and ICF, NFHS-5 (2019-21); district extract by [pratapvardhan/NFHS-5](https://github.com/pratapvardhan/NFHS-5).
- Built with [Streamlit](https://streamlit.io), [pandas](https://pandas.pydata.org) and [Altair](https://altair-viz.github.io).
- Team and mentor: [add names here].
- Licence: [add a licence, for example MIT for the code]. NFHS data stay under the terms set by IIPS.
