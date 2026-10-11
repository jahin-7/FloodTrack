# Source links, permissions, reproducibility and required attribution

## Primary rules (user-provided Track B brief)

- Allowed as model inputs: Sentinel-1, Sentinel-2, Copernicus DEM, historical **pre-event** OSM, and the brief-listed training datasets.
- NOT allowed as inference/training inputs: Copernicus EMSR927/EMS, UNOSAT or other published damage maps; post-event OSM edits.
- EMSR927 may be consulted **only after** prediction freeze for evaluation.
- Event case study: 26 August 2026, northern Nepal Bhote Koshi–Trishuli corridor (per brief).
- Deliverables: interactive map, one-page situation report, GitHub README, ≤6-page technical report, 3-minute video, attributions, reference-only comparison.

## Free Copernicus Data Space services (current official documentation)

- Free registration: https://dataspace.copernicus.eu/
- Free-tier quotas (monthly processing units / request limits): https://documentation.dataspace.copernicus.eu/Quotas.html
- STAC API: https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- STAC search endpoint used: `https://stac.dataspace.copernicus.eu/v1/search`
- Sentinel Hub OAuth client creation: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html
- Sentinel Hub processing API: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html
- S1 GRD data and terrain correction: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html
- Sentinel Hub Process S1 examples: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S1GRD.html
- Copernicus DEM processing: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/DEM.html
- **Processing API outputs are processed and orthorectified rasters, NOT raw SAFE.** This approach avoids the need to download and preprocess multi-GB GRD scenes locally. A small area consumes part of the free CDSE quota.
- CDSE metadata may change over time; inspect live STAC response if scene matching fails.

## Historical OSM

- https://api.ohsome.org/v1/elements/geometry
- https://docs.ohsome.org/ohsome-api/development/endpoints.html
- https://www.openstreetmap.org/copyright
- Example snapshot `2026-07-27`, **strictly before** 26 Aug 2026. Do not substitute current OSM.

## Permitted training sources

- Kuro Siwo (recommended): https://github.com/Orion-AI-Lab/KuroSiwo — cite **Bountos et al., 2024**. Inspect actual imagery formats, classes and license before adaptation/redistribution.
- Sen1Floods11 (optional): https://github.com/cloudtostreet/Sen1Floods11 — cite **Bonafilia et al., CVPR Workshops 2020**. Verify licensing and training-label schema.
- Training adapter expects paired **pre and post VV dB** GeoTIFFs and a compatible label GeoTIFF for each site; raw source archives are **not** automatically converted.

## Reference only (never predictor/training/tuning input)

- Official EMS activation: https://mapping.emergency.copernicus.eu/
- Comparison script accepts validation polygons **after method freeze**, placed only under `data/reference_validation/`.
- Distinguish extent, damage grading and affected-area categories; don't compute class IoU if semantics differ.

## Required exact competition attributions (as given in Track B brief)

> Contains modified Copernicus Sentinel data 2026.
>
> Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
>
> © OpenStreetMap contributors.

Also cite whichever training dataset is actually used. If official reference maps are displayed, credit **European Union, Copernicus Emergency Management Service data** and mark them validation-only.
