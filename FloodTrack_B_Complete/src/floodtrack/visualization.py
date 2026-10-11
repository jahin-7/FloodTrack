from pathlib import Path
import folium
from .core import read_json

COLORS={'exposed_building':'#ed8936','exposed_bridge':'#d53f8c',
        'blocked_road_candidate':'#d62828','cut_off_candidate':'#b91c1c',
        'unknown':'#718096','connected':'#2f855a'}

def make_map(run,cfg):
    run=Path(run)
    xmin,ymin,xmax,ymax=cfg['bbox']
    m=folium.Map(location=[(ymin+ymax)/2,(xmin+xmax)/2],zoom_start=13,tiles='CartoDB positron')
    hazard=read_json(run/'flood_extent.geojson')
    folium.GeoJson(hazard,name='Candidate flood extent',style_function=lambda _: {
        'fillColor':'#3182ce','color':'#2b6cb0','fillOpacity':.45,'weight':1}).add_to(m)
    imp=read_json(run/'impacts.geojson')
    for typ in COLORS:
        fs=[f for f in imp['features'] if f['properties'].get('role')==typ]
        for f in fs:f['properties'].setdefault('name','')
        if not fs:continue
        def style(f):
            c=COLORS.get(f['properties'].get('role'),'#888888')
            return {'color':c,'fillColor':c,'fillOpacity':.65,'weight':3}
        layer=folium.FeatureGroup(name=f'{typ} ({len(fs)})',show=(typ!='connected'))
        folium.GeoJson({'type':'FeatureCollection','features':fs},style_function=style,
              tooltip=folium.GeoJsonTooltip(fields=['role','name'], aliases=['Type','Name'])).add_to(layer)
        layer.add_to(m)
    folium.Rectangle(bounds=[[ymin,xmin],[ymax,xmax]],color='#555',fill=False,weight=2).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(str(run/'dashboard_map.html'))
    return str(run/'dashboard_map.html')
