# GeoVault AI — Final Geological & Geospatial Synthetic Dataset

Version: FINAL v1.0
Status: Prototype-ready synthetic demonstration corpus
Mines: GEVRA, KUSMUNDA, DIPKA, NIGAHI, DUDHICHUA

## Important provenance statement

This package is **synthetic demonstration data**. Mine-specific geometries, borehole intervals, lithology, geological units, survey points, faults/contacts, geotechnical zones, DEMs, seam-thickness surfaces and derived spatial values are not official CMPDI/CIL records and must not be presented as official measurements.

Public web research was used only for high-level project/context references. Public context and synthetic content are separated in `Source_Map` and `PUBLIC_REFERENCE_SOURCES.md`.

## Recommended files for the prototype

1. `GeoVault_Geospatial_All_Mines_FINAL.gpkg`
   - **Primary spatial file for the developer.**
   - One GeoPackage contains all mines and all spatial layers.
   - Recommended first choice for Python/GeoPandas/QGIS/PostGIS loading.

2. `GeoVault_Geological_Master_FINAL.xlsx`
   - Human-readable master tables.
   - Includes production linkage, boreholes, 600 detailed borehole intervals, seams, observations, events, geological units, survey points, QA cases and catalogs.

3. `mines/<MINE_CODE>/`
   - Per-mine GeoPackage-compatible folders.
   - Per-mine Excel workbook.
   - Shapefile and GeoJSON versions of all new layers.

4. `dxf/`
   - 2 synthetic geological cross-sections per mine.
   - DXF files are real CAD files and can be opened in compatible CAD software.

5. `raster/`
   - 1 synthetic DEM and 1 synthetic coal-thickness surface per mine.
   - GeoTIFF, EPSG:4326.

6. `maps/`
   - 5 mine map PNG previews.
   - `GeoVault_Geological_Atlas_FINAL.pdf` for quick visual inspection.

7. `QA_Test_Cases`
   - 150 geospatial/geological test questions for validating the prototype.

## Dataset contents

- 5 mines
- 30 mine-year operational records linked to the earlier GeoVault dataset
- 60 baseline boreholes
- 600 detailed borehole lithology intervals
- 21 coal-seam records
- 30 mapped geological units
- 125 synthetic survey/control points
- 15 geological contacts
- 60 borehole traces
- 20 geotechnical interpretation zones
- 30 land-use polygons
- 10 spatial geological/operational event points
- 21 coal-seam belt polygons
- 10 DXF cross-sections
- 5 synthetic DEM rasters
- 5 synthetic coal-thickness surfaces
- 150 QA test cases
- SHP + GeoJSON + GPKG representations

## Main spatial layer families

### Existing baseline
mine_boundary, coal_seams, boreholes, faults, benches, haul_roads, drainage, overburden_dumps, infrastructure

### Final geological additions
borehole_intervals, geological_units, geological_contacts, borehole_traces, survey_points, geological_events_spatial, geotechnical_zones, landuse, coal_seam_belts

## Suggested prototype ingestion order

1. GeoPackage
2. Excel tables
3. DXF
4. GeoTIFF
5. Optional individual SHP/GeoJSON files

The developer should treat `GeoVault_Geospatial_All_Mines_FINAL.gpkg` as the canonical spatial delivery format and the individual SHP/GeoJSON/DXF files as compatibility/demo inputs.

## Python quick start

```python
import geopandas as gpd

gpkg = "GeoVault_Geospatial_All_Mines_FINAL.gpkg"

gdf = gpd.read_file(gpkg, layer="GEVRA_boreholes")
print(gdf.head())

units = gpd.read_file(gpkg, layer="GEVRA_geological_units")
print(units[["Unit_Name", "Unit_Type"]])
```

List all layers:

```python
import fiona
print(fiona.listlayers(gpkg))
```

Read detailed borehole intervals:

```python
intervals = gpd.read_file(gpkg, layer="GEVRA_borehole_intervals")
```

## Spatial reasoning examples

- Boreholes within a buffer of a fault
- Boreholes intersecting a mine boundary
- Boreholes associated with a coal seam
- Geological units intersecting a mine working
- Infrastructure nearest to a bench/pit feature
- Area of mine boundary
- Length of haul roads
- RL/elevation range from survey points
- Production + geological event cross-year joins

## Coordinate reference system

Spatial vector data uses EPSG:4326 / WGS 84 for simple prototype portability. The synthetic DEMs and GeoTIFF surfaces use EPSG:4326 as well. For metric distance/area analysis, the developer should reproject to an appropriate projected CRS before calculating authoritative-looking distances or areas.

## Relationship to earlier GeoVault data

The `Production_Link` table intentionally uses the same five mines and six financial years as the earlier synthetic operational dataset so the prototype can demonstrate cross-domain retrieval:

Operational Excel/PDF
    +
Geological/GIS/CAD
    +
Authorization scope
    ->
GeoVault evidence-backed answer

## Do not claim

Do not call synthetic geometry:
- official CMPDI map
- official CIL mine plan
- surveyed DGPS boundary
- official borehole log
- official reserve/resource estimate
- official geological section
- official engineering design


## Operational ID mapping

The earlier operational corpus used `GV001`–`GV005`; the final geospatial corpus uses stable mine IDs such as `M-GEVRA`. The exact mapping is included in `Mine_ID_Mapping`:

- GV001 → M-GEVRA
- GV002 → M-KUSMUNDA
- GV003 → M-DIPKA
- GV004 → M-NIGAHI
- GV005 → M-DUDHICHUA

`Production_Link` is copied from the earlier operational master on the common mine/year records so the production, OB, stripping-ratio, safety/environment and geological-observation fields remain aligned.
