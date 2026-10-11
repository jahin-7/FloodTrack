"""Launch from root: streamlit run dashboard/app.py -- --run outputs/<name>."""
import sys
from pathlib import Path
import streamlit as st
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from floodtrack.core import read_json
from floodtrack.reporting import answer_question
import streamlit.components.v1 as components

st.set_page_config(page_title='FloodTrack B',layout='wide')
st.title('FloodTrack B | Satellite flood and access screening')
root_out=root/'outputs'
runs=[p for p in root_out.iterdir() if p.is_dir() and (p/'run_manifest.json').exists()]
if not runs:
    st.info('First run: python scripts/run_pipeline.py --config config/smoke_test.yaml')
    st.stop()
select=st.selectbox('Completed run',runs,format_func=lambda p:p.name)
manifest=read_json(select/'run_manifest.json')
if manifest['config']['source_mode']=='synthetic':
    st.error('SYNTHETIC TEST — not measured real-world flood damage')
else:st.warning('Research screening only. Not a field-verified disaster response product.')
ras=read_json(select/'raster_metrics.json');imp=read_json(select/'impact_metrics.json')
cs=st.columns(5)
for c,(label,val) in zip(cs,[('Flood area km²',ras['area_km2']),('Buildings exposed',imp['buildings_exposed_count']),
      ('Bridges exposed',imp['bridges_exposed_count']),('Road km flagged',imp['blocked_road_km']),
      ('Possible cut-offs',imp['settlements_likely_cut_off'])]):c.metric(label,val)
components.html((select/'dashboard_map.html').read_text(encoding='utf-8'),height=650,scrolling=True)
st.subheader('Map-grounded Q&A')
question=st.text_input('Ask about flood extent, roads, buildings, bridges or possible cut-off settlements')
if question:st.write(answer_question(select,question))
st.download_button('Download English situation report',(select/'situation_report_en.md').read_text(encoding='utf-8'),
                   file_name='situation_report_en.md')
st.download_button('Download Nepali situation report',(select/'situation_report_ne.md').read_text(encoding='utf-8'),
                   file_name='situation_report_ne.md')
st.caption('© OpenStreetMap contributors. Contains modified Copernicus Sentinel data 2026. See full credits in report.')
