"""Verifiable situation report and grounded Q&A; numbers never written by an LLM."""
from pathlib import Path
from datetime import datetime,timezone
import re
from .core import ATTRIBUTIONS, save_json,read_json


def _facts(run):
    p=Path(run)
    ras=read_json(p/'raster_metrics.json');imp=read_json(p/'impact_metrics.json')
    return ras,imp


def situation_report(run,config,satellite_meta=None):
    ras,imp=_facts(run)
    name=config['name'];event=config['case_event_date']
    state='SYNTHETIC EXAMPLE — NOT REAL FLOOD MEASUREMENTS' if config['source_mode']=='synthetic' else 'RESEARCH PROTOTYPE — NOT FIELD-VERIFIED'
    notes=[]
    if satellite_meta:
        notes.append('S1 pre/post: '+str(satellite_meta.get('pre_utc','unknown'))+' / '+str(satellite_meta.get('post_utc','unknown')))
        notes.append('Same relative orbit: '+str(satellite_meta.get('same_orbit_verified','unknown')))
    en=f'''# FLOODTRACK B — ONE-PAGE SITUATION REPORT

**{state}**  
**Area:** {name}  
**Event date:** {event}  
**Analysis time (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}  
**Data:** Sentinel-1 radar; Sentinel-2 and Copernicus DEM when available; pre-event OSM snapshot {config['osm_snapshot']}.

## Rapid assessment (model estimates, not confirmed field damage)

| Indicator | Estimate |
|---|---:|
| Mapped candidate flood/water extent | {ras['area_km2']:.5f} km² |
| OSM buildings intersecting candidate hazard | {imp['buildings_exposed_count']} |
| OSM bridges intersecting candidate hazard | {imp['bridges_exposed_count']} |
| Mapped road length intersecting candidate hazard | {imp['blocked_road_km']:.4f} km |
| Settlements with predicted loss of mapped access | {imp['settlements_likely_cut_off']} |
| Settlements with insufficient mapping to determine isolation | {imp['settlements_unknown']} |

**Connectivity reference:** {imp['anchor_type']}.  
**Radar pixel coverage:** {ras['valid_radar_fraction']:.1%}.  
**Flood detector:** {ras['detector']}.  
**Optical:** {ras['optical_note']}.  
**DEM:** {ras['slope_note']}.

## Priority review

Predicted road/bridge intersections and settlement cut-off flags need confirmation by responders. This is a triage map, not a certified casualty, damage or passability assessment.

## Limits and decision safeguards

Terrain layover/shadow, cloud-obscured optical images, irregular satellite revisit, partial road mapping, approximate road snapping, bridges passing above flood and AOI boundary truncation can make flags wrong. Satellite scenes cannot forecast a sudden glacier collapse minutes in advance. Debris cannot be reliably distinguished from water with this baseline. Do not infer fatalities or displacement.

**Acquisition notes:** {'; '.join(notes) if notes else 'Demo data are synthetic; no real acquisitions'}.

**Required credits**  
{chr(10).join('  '+s for s in ATTRIBUTIONS)}  
Kuro Siwo (Bountos et al., 2024) **only if its data were used for model training**.  
Educational prototype; not for operational emergency decisions.
'''
    nep=f'''# बाढी अवस्था संक्षिप्त प्रतिवेदन

**{state}**

क्षेत्र: {name} | घटना मिति: {event}

उपग्रहबाट अनुमान गरिएको सम्भावित बाढी क्षेत्रफल: **{ras['area_km2']:.5f} वर्ग किमि**।
खतराको नक्सासँग प्रतिच्छेद हुने OpenStreetMap भवन: **{imp['buildings_exposed_count']}**।
सम्भावित प्रभावित पुल: **{imp['bridges_exposed_count']}**।
सम्भावित प्रभावित सडकको लम्बाइ: **{imp['blocked_road_km']:.4f} किमि**।
सडक सम्पर्क विच्छेद भएको हुन सक्ने बस्ती: **{imp['settlements_likely_cut_off']}**।
पर्याप्त जानकारी नभएका बस्ती: **{imp['settlements_unknown']}**।

**सावधानी:** यी सङ्ख्या नक्साबाट गणना गरिएका अनुमान हुन्, प्रमाणित क्षतिको विवरण होइनन्।
दुर्गम भू-भाग, अपूर्ण सडक नक्सा र उपग्रह चित्रबीचको समय अन्तरका कारण त्रुटि हुन सक्छ।
मैदानबाट पुष्टि आवश्यक छ।
'''
    (Path(run)/'situation_report_en.md').write_text(en,encoding='utf-8')
    (Path(run)/'situation_report_ne.md').write_text(nep,encoding='utf-8')
    return en,nep


def answer_question(run,question):
    """Closed-book question answering: only computed fields are available; no fabricated values."""
    ras,imp=_facts(run)
    q=question.lower()
    warning='' 
    manifest=Path(run)/'run_manifest.json'
    if manifest.exists() and read_json(manifest).get('config',{}).get('source_mode')=='synthetic':
        warning='SYNTHETIC SOFTWARE TEST — NOT REAL FLOOD DATA. '
    if re.search(r'cut.?off|isolat|disconnect|अलग|सम्पर्क',q):
        return warning+f"{imp['settlements_likely_cut_off']} settlements are predicted cut off; {imp['settlements_unknown']} have insufficient map evidence. These are unverified model estimates."
    if re.search(r'bridge|पुल',q):
        return warning+f"{imp['bridges_exposed_count']} mapped bridge features intersect candidate hazard; damage is unverified."
    if re.search(r'building|home|house|घर|भवन',q):
        return warning+f"{imp['buildings_exposed_count']} mapped buildings intersect candidate hazard; this is exposure, not confirmed damage."
    if re.search(r'road|सडक',q):
        return warning+f"{imp['blocked_road_km']:.4f} km of mapped road segments intersect candidate hazard; passability not verified."
    if re.search(r'flood|area|extent|बाढी|क्षेत्र',q):
        return warning+f"Candidate flood extent is {ras['area_km2']:.5f} km². This is a satellite-derived screening estimate."
    return warning+'This prototype cannot answer that from the permitted map-derived metrics. Ask about flood extent, mapped roads, buildings, bridges or isolation flags.'


def export_one_page_pdf(run, config):
    """One-page PDF artifact for brief (uses reportlab; English only; never invents metrics)."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    ras,imp=_facts(run)
    dest=Path(run)/'situation_report_en_one_page.pdf'
    c=canvas.Canvas(str(dest),pagesize=A4)
    W,H=A4;x=45;y=H-43
    def ln(s,font='Helvetica',size=9,leading=13):
        nonlocal y
        c.setFont(font,size)
        for row in simpleSplit(str(s),font,size,W-90):
            c.drawString(x,y,row);y-=leading
    ln('FLOODTRACK B | SATELLITE SITUATION REPORT','Helvetica-Bold',15,22)
    status=('SYNTHETIC SOFTWARE TEST - NOT A REAL DISASTER RESULT' if config['source_mode']=='synthetic'
            else 'RESEARCH ESTIMATES ONLY - NOT FIELD VERIFIED')
    ln(status,'Helvetica-Bold',9,16)
    ln('Area: '+config['name']+' | event date: '+str(config['case_event_date']))
    ln('Pre-event OSM snapshot: '+str(config['osm_snapshot']))
    y-=10
    ln('MAP-DERIVED SCREENING INDICATORS','Helvetica-Bold',11,18)
    for title,value in [
        ('Candidate water/flood extent',f"{ras['area_km2']:.5f} sq km"),
        ('Buildings intersecting candidate hazard',str(imp['buildings_exposed_count'])),
        ('Bridges intersecting candidate hazard',str(imp['bridges_exposed_count'])),
        ('Roads intersecting candidate hazard',f"{imp['blocked_road_km']:.4f} km"),
        ('Possibly cut-off settlements',str(imp['settlements_likely_cut_off'])),
        ('Insufficient mapping to classify',str(imp['settlements_unknown'])),
        ('Radar valid pixel coverage',f"{ras['valid_radar_fraction']:.1%}")]:
        ln(title+': '+value,'Helvetica',9,16)
    y-=10
    ln('EVIDENCE / METHODS','Helvetica-Bold',11,17)
    ln('Detector: '+ras['detector'],size=8,leading=12)
    ln('Optional optical: '+ras['optical_note'],size=8,leading=12)
    ln('DEM: '+ras['slope_note'],size=8,leading=12)
    ln('Road access anchor: '+imp['anchor_type'],size=8,leading=12)
    y-=9
    ln('PRIORITIES AND LIMITATIONS','Helvetica-Bold',11,17)
    for s in [
      'Review bridge/road intersections and possible disconnected settlements with local responders.',
      'Exposure is NOT proof of destroyed buildings or impassable roads. Connectivity depends on OSM completeness.',
      'Clouds, radar shadow/layover, steep terrain, map omissions and AOI-edge truncation cause uncertainty.',
      'Satellite revisit cannot provide minute-ahead glacier-collapse warnings; debris not independently validated.',
      'For educational research only. Do not use for emergency deployment without validation.']:
      ln('- '+s,size=8,leading=12)
    y-=9
    ln('DATA CREDITS (from contest brief)','Helvetica-Bold',8,12)
    for s in ATTRIBUTIONS: ln(s,size=6.6,leading=9)
    if config.get('ai_model_path'):
      ln('Model citation required: permitted source training data, e.g., Bountos et al. (2024).',size=6.6,leading=9)
    if y<37:raise RuntimeError('PDF overflow: one-page format requires shortening text')
    c.showPage();c.save()
    return dest
