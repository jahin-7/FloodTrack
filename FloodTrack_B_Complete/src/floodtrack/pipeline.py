"""CLI-reusable run, with a strict distinction between synthetic and real evidence."""
from pathlib import Path
import sys
from .core import ensure_dir,save_json,validate_input_tree,read_json
from .mapping import segment,estimate_impacts
from .reporting import situation_report,export_one_page_pdf
from .visualization import make_map


def run(config,root):
    root=Path(root).resolve(); out=ensure_dir(root/'outputs'/config['name'])
    raw=ensure_dir(root/'data'/'raw'/config['name'])
    osm=ensure_dir(root/'data'/'osm')/f"{config['name']}_historical.geojson"
    validate_input_tree(root/'data'/'raw')
    validate_input_tree(root/'data'/'osm')
    if config['source_mode']=='synthetic':
        from .synthetic import create_synthetic
        create_synthetic(config,raw,osm)
        sat={'source':'synthetic test fixtures','same_orbit_verified':'N/A: synthetic',
              'pre_utc':'synthetic', 'post_utc':'synthetic'}
    elif config['source_mode']=='staged':
        if not (raw/'s1_pair.tif').exists() or not osm.exists() or not (raw/'satellite_provenance.json').exists():
            raise FileNotFoundError('Staged mode expects data/raw/<name>/s1_pair.tif, satellite_provenance.json and data/osm/<name>_historical.geojson')
        sat=read_json(raw/'satellite_provenance.json')
        if sat.get('same_orbit_verified') is not True:
            raise RuntimeError('Staged Sentinel-1 provenance does not certify the same relative orbit and pass')
    else:
        from .acquisition import acquire_satellite,download_osm_snapshot
        sat=acquire_satellite(config,raw)
        if str(config['osm_snapshot']) == '2026-08-01':
            from .geofabrik import acquire as acquire_geofabrik
            osm_meta=acquire_geofabrik(config,osm)
        else:
            osm_meta=download_osm_snapshot(config,osm)
        save_json(out/'osm_provenance.json',osm_meta)
    flood,ras=segment(raw,out,config)
    imp=estimate_impacts(osm,flood,out)
    situation_report(out,config,sat)
    export_one_page_pdf(out,config)
    make_map(out,config)
    save_json(out/'run_manifest.json',{'config':config,'satellite':sat,
        'important':'synthetic is NOT an authentic case-study result' if config['source_mode']=='synthetic'
                    else 'Estimates from satellite/OSM, not ground truth',
        'outputs':['flood_mask.tif','flood_extent.geojson','raster_metrics.json',
                   'impact_metrics.json','impacts.geojson','situation_report_en.md',
                   'situation_report_ne.md','situation_report_en_one_page.pdf','dashboard_map.html']})
    print(f"Complete ({config['source_mode']}): {out}")
    print(f"Flood area km2={ras['area_km2']}; exposed buildings={imp['buildings_exposed_count']}; "
          f"potential cut-offs={imp['settlements_likely_cut_off']}; uncertain={imp['settlements_unknown']}")
    return out
