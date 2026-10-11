"""FloodTrack Streamlit dashboard. Run from project root: streamlit run dashboard/app.py"""
from pathlib import Path
import sys

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from floodtrack.core import read_json  # noqa: E402
from floodtrack.reporting import answer_question  # noqa: E402

st.set_page_config(
    page_title="FloodTrack | Satellite Evidence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1500px;}
.ft-hero {padding: 1.4rem 1.6rem; border: 1px solid #203c57; border-radius: 18px;
  background: linear-gradient(120deg, #0b2139 0%, #163858 65%, #113b45 100%); color: #f4fbff;
  margin-bottom: 1.3rem;}
.ft-title {font-size: 2.15rem; font-weight: 750; letter-spacing: -.035em; margin: 0;}
.ft-sub {margin: .35rem 0 0; font-size: 1rem; color: #d7e5ed;}
.ft-note {padding: .7rem 1rem; border-left: 3px solid #51bbd1; background: rgba(81,187,209,.08); border-radius: 3px;}
[data-testid="stMetric"] {border: 1px solid rgba(111,157,190,.28); border-radius: 12px; padding: .8rem;}
</style>
<div class="ft-hero">
  <p class="ft-title">🌊 FloodTrack</p>
  <p class="ft-sub">Satellite evidence · Candidate hazards · Road access screening</p>
</div>
""", unsafe_allow_html=True)

runs_dir = ROOT / "outputs"
runs = sorted((p for p in runs_dir.iterdir() if p.is_dir() and
               (p / "run_manifest.json").exists()), key=lambda p: p.name) if runs_dir.exists() else []
if not runs:
    st.info("No completed runs yet. From the project root, run `python scripts/run_pipeline.py --config config/smoke_test.yaml`.")
    st.stop()

with st.sidebar:
    st.header("Study selector")
    run = st.selectbox("Completed analysis", runs, format_func=lambda p: p.name)
    st.caption("Changing a run loads previously generated local outputs; it does not download new satellite scenes.")
    st.divider()
    st.markdown("**Interpretation**")
    st.caption("Candidate exposures ≠ confirmed damage. Scenario-based connectivity ≠ observed road closure.")
    st.divider()
    st.caption("Multimodal AI Hackathon 2026 · Track B")

manifest = read_json(run / "run_manifest.json")
metrics = read_json(run / "raster_metrics.json")
impact = read_json(run / "impact_metrics.json")
mode = (manifest.get("config") or {}).get("source_mode", "unknown")
synthetic = mode == "synthetic"
case = manifest.get("config", {})
st.subheader(run.name.replace("_", " "))
if synthetic:
    st.error("SYNTHETIC SOFTWARE TEST — these measurements do not describe actual Nepal flood conditions.", icon="🧪")
else:
    st.warning("RESEARCH SCREENING — not field-verified flood, building damage, or observed road closures.", icon="⚠️")

st.caption(f"Event date: {case.get('case_event_date', 'unavailable')} · Data mode: {mode} · "
           f"Detector: {metrics.get('detector', 'unknown')}")

c1, c2, c3, c4, c5 = st.columns(5)
values = [
    ("Candidate flood area", f"{metrics.get('area_km2', 0):,.4f} km²"),
    ("Buildings exposed*", impact.get("buildings_exposed_count", 0)),
    ("Bridges exposed*", impact.get("bridges_exposed_count", 0)),
    ("Roads flagged*", f"{impact.get('blocked_road_km', 0):,.3f} km"),
    ("Possible cut-offs*", impact.get("settlements_likely_cut_off", 0)),
]
for col, (label, value) in zip([c1, c2, c3, c4, c5], values):
    col.metric(label, value)
st.caption("* Values depend on the primary flood candidate mask and network assumptions; they are NOT confirmed disaster losses.")
if metrics.get("pixel_count", 0) == 0:
    st.info("The selected main detector found no flood pixels in this AOI. This does not establish that the event caused no damage. Compare the independent radar-change and AI diagnostics separately.")

t_map, t_evidence, t_access, t_reports, t_provenance = st.tabs(
    ["🗺️ Map", "🛰️ Satellite evidence", "🛣️ Access screening", "📄 Reports & Q&A", "🧾 Provenance"]
)

with t_map:
    st.markdown("#### Flood / exposure map")
    map_path = run / "dashboard_map.html"
    if map_path.exists():
        components.html(map_path.read_text(encoding="utf-8"), height=650, scrolling=True)
    else:
        st.warning("No generated map found in this run.")
    st.caption("Layers depict derived hazard/exposure candidates and OSM features; open the map legend to toggle them.")

with t_evidence:
    st.markdown("#### Satellite and model diagnostics")
    candidates = [
        ("Before/after Sentinel-1 and radar-change screening",
         [run / "final_submission/figures/satellite_and_screening.png",
          ROOT / "docs/images/satellite_before_after.png"],
         "Radar change candidates are NOT verified landslide, flooding, or infrastructure damage."),
        ("Water-model probability diagnostic",
         [run / "final_submission/figures/water_model_diagnostic.png",
          ROOT / "docs/images/water_probability_diagnostic.png"],
         "AI water probabilities are exploratory diagnostics, not the primary threshold-mask output."),
        ("AI pre/post probability comparison",
         [run / "ai_results/syapru_ai_comparison.png",
          ROOT / "docs/images/ai_water_probability_change.png"],
         "An increase in model score is not a ground-truth water or damage label."),
    ]
    if run.name != "Syapru_Besi_AOI01":
        st.info("The sample gallery belongs to Syapru Besi, not this selected run. Only run-specific evidence will be shown.")
    found = False
    for heading, paths, desc in candidates:
        # Never display one AOI's figures as another AOI's evidence.
        if run.name != "Syapru_Besi_AOI01":
            paths = [p for p in paths if str(p).startswith(str(run) + "/")]
        file = next((p for p in paths if p.exists()), None)
        if file is not None:
            found = True
            st.markdown(f"**{heading}**")
            st.image(str(file), use_container_width=True)
            st.caption(desc)
    if not found:
        st.info("No saved diagnostic PNGs for this run. Export comparison figures from its satellite/model processing first.")

with t_access:
    st.markdown("#### Scenario-based settlement connectivity")
    a, b, c = st.columns(3)
    a.metric("Possibly disconnected", impact.get("settlements_likely_cut_off", 0))
    b.metric("Connected in simulation", impact.get("settlements_still_connected", 0))
    c.metric("Unknown / insufficient data", impact.get("settlements_unknown", 0))
    st.caption(f"Road-network anchor: {impact.get('anchor_type', 'not available')}. "
               "Graph connectivity uses assumed closure of intersecting edges, not field evidence.")
    for title, key in [("Potential disconnections", "cut_off"), ("Unknown classifications", "unknown"),
                       ("Connected in simulation", "connected")]:
        with st.expander(f"{title} ({len(impact.get(key, []))})", expanded=key == "cut_off"):
            rows = impact.get(key, [])
            st.dataframe(rows, use_container_width=True, hide_index=True) if rows else st.caption("None listed for this run.")
    st.caption(impact.get("warning", ""))

with t_reports:
    st.markdown("#### Ask a map-grounded question")
    question = st.text_input("For example: How many bridges are exposed? Which settlements are possibly cut off?", key="question")
    if question:
        st.write(answer_question(run, question))
    st.divider()
    st.markdown("#### Export situation reports and GIS outputs")
    items = [
        ("English report (.md)", "situation_report_en.md", "text/markdown"),
        ("Nepali report (.md)", "situation_report_ne.md", "text/markdown"),
        ("One-page report (.pdf)", "situation_report_en_one_page.pdf", "application/pdf"),
        ("Candidate flood polygons (.geojson)", "flood_extent.geojson", "application/geo+json"),
        ("Exposure features (.geojson)", "impacts.geojson", "application/geo+json"),
    ]
    for label, filename, mime in items:
        p = run / filename
        if p.exists():
            st.download_button(label, data=p.read_bytes(), file_name=f"{run.name}_{filename}", mime=mime)

with t_provenance:
    st.markdown("#### What was used?")
    st.json(manifest.get("satellite", {}))
    st.markdown("#### Run configuration")
    st.json(case)
    st.markdown("#### Confidence and caveats")
    st.caption(metrics.get("warning", ""))
    st.caption(impact.get("warning", ""))
    st.caption("Independent Nepal validation and post-hoc EMSR927 comparison require additional documented evaluation.")

st.divider()
st.caption("Contains modified Copernicus Sentinel data 2026. © OpenStreetMap contributors. "
           "DEM credit and dataset citations are recorded in the project documentation. Educational prototype only.")
