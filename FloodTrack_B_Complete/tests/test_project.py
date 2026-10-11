import os,sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from floodtrack.core import load_config
from floodtrack.reporting import answer_question
from floodtrack.pipeline import run

def test_snapshot_leakage(tmp_path):
    p=tmp_path/'bad.yaml'
    p.write_text('name: bad\nsource_mode: synthetic\ncase_event_date: 2026-08-26\n'
                 'osm_snapshot: 2026-08-28\nbbox: [85.1,28.1,85.15,28.15]\n')
    with pytest.raises(ValueError,match='before the event'):
        load_config(p)

def test_reject_reference_in_config(tmp_path):
    p=tmp_path/'bad.yaml'
    p.write_text('name: EMSR927\nsource_mode: real\ncase_event_date: 2026-08-26\n'
                 'osm_snapshot: 2026-07-27\nbbox: [85.1,28.1,85.15,28.15]\n')
    with pytest.raises(ValueError,match='Reference'):
        load_config(p)

def test_smoke_pipeline(tmp_path):
    config=load_config(ROOT/'config/smoke_test.yaml')
    out=run(config,tmp_path)
    for name in ('flood_mask.tif','flood_extent.geojson','impacts.geojson',
             'impact_metrics.json','dashboard_map.html','situation_report_en.md','situation_report_ne.md'):
        assert (out/name).exists(),name
    assert 'SYNTHETIC' in (out/'situation_report_en.md').read_text()
    assert 'unverified' in answer_question(out,'How many bridges?').lower()
