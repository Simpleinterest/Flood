"""Load USGS NHD flowlines for HUC8 12100201 (matching docs/README.md's HAND
HUC8) into the `river_network` table.

Usage:
    python -m scripts.ingest_nhd_flowlines
    python -m scripts.ingest_nhd_flowlines --from-file <NHDPLUS_H_1210_HU4_GDB.gdb>

`--from-file` reads the NHDFlowline layer from USGS's staged NHDPlus HR HU4
geodatabase instead of querying the MapServer, for when the hydro.nationalmap.gov
query service is down (it returns CloudFront 504s even for count-only queries).
Download: https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/Beta/GDB/NHDPLUS_H_1210_HU4_GDB.zip
"""
import argparse
import sys

import geopandas as gpd
import shapely

from lib.db import get_engine
from lib.geo import boundary_polygon, load_kerr_county_boundary, reproject_to_4326
from lib.langchain_tools import ArcGISFeatureServerTool
from lib.upsert import upsert_geodataframe

# USGS National Map / NHDPlus HR MapServer, NHDFlowline layer (id 3).
NHD_FLOWLINE_FEATURE_SERVER_URL = (
    "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query"
)

HUC8 = "12100201"
SOURCE = "nhd"
# This MapServer's fields are all lower-case (verified against layer 3's /query?f=json
# field list on 2026-09-06), unlike the FGDB-style "NHDPlusID"/"REACHCODE" naming used
# in NHDPlus HR documentation and file exports.
ID_FIELD = "nhdplusid"


def fetch_flowlines(boundary_geojson: dict) -> gpd.GeoDataFrame:
    where = f"reachcode LIKE '{HUC8}%'"
    data = ArcGISFeatureServerTool().invoke(
        {"url": NHD_FLOWLINE_FEATURE_SERVER_URL, "boundary_geojson": boundary_geojson, "where": where}
    )
    gdf = gpd.GeoDataFrame.from_features(data.get("features", []), crs="EPSG:4326")
    return reproject_to_4326(gdf)


def read_flowlines_file(path: str) -> gpd.GeoDataFrame:
    """Read the same NHDPlus HR flowlines from a staged HU4 geodatabase.

    The geodatabase uses FGDB-style field names ("NHDPlusID", "ReachCode") and
    stores NHDPlusID as a double, so names are lower-cased and the id is cast to
    an integer to match the MapServer path's `nhdplusid` values. Geometries are
    measured 3D lines; Z is dropped since the MapServer path returns 2D GeoJSON.
    """
    gdf = gpd.read_file(path, layer="NHDFlowline", where=f"ReachCode LIKE '{HUC8}%'")
    gdf.columns = [c if c == "geometry" else c.lower() for c in gdf.columns]
    gdf = gdf.set_geometry("geometry")
    gdf[ID_FIELD] = gdf[ID_FIELD].astype("int64")
    gdf["geometry"] = shapely.force_2d(gdf.geometry.values)
    return reproject_to_4326(gdf)


def clip_to_boundary(gdf: gpd.GeoDataFrame, boundary) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    return gdf[gdf.intersects(boundary)].copy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--from-file",
        help="NHDPlus HR HU4 geodatabase to read instead of querying the MapServer",
    )
    args = parser.parse_args(argv)

    boundary_gdf = load_kerr_county_boundary()
    boundary_geojson = boundary_gdf.geometry.iloc[0].__geo_interface__
    boundary_geom = boundary_polygon()

    if args.from_file:
        gdf = read_flowlines_file(args.from_file)
    else:
        gdf = fetch_flowlines(boundary_geojson)
    gdf = clip_to_boundary(gdf, boundary_geom)

    if ID_FIELD not in gdf.columns:
        print(f"Expected id field '{ID_FIELD}' not present in NHD response", file=sys.stderr)
        return 1

    count = upsert_geodataframe(
        engine=get_engine(),
        gdf=gdf,
        table="river_network",
        layer="river",
        source=SOURCE,
        id_field=ID_FIELD,
    )
    print(f"Upserted {count} rows into river_network")
    return 0


if __name__ == "__main__":
    sys.exit(main())
