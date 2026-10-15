import geopandas as gpd
from shapely.geometry import LineString

from scripts import ingest_nhd_flowlines


def test_from_file_reader_matches_the_mapserver_shape(tmp_path):
    # Mirrors the staged NHDPlus HR HU4 geodatabase: FGDB-style field names,
    # NHDPlusID stored as a double, 3D lines in NAD83, and reaches from more
    # than one HUC8 in the same layer.
    gdb = tmp_path / "NHDPLUS_H_1210_HU4_GDB.gdb"
    gpd.GeoDataFrame(
        {
            "NHDPlusID": [55000100012345.0, 55000100067890.0],
            "ReachCode": ["12100201000123", "12100202000456"],
            "GNIS_Name": ["Guadalupe River", "Other Creek"],
        },
        geometry=[
            LineString([(-99.4, 30.0, 500.0), (-99.3, 30.05, 495.0)]),
            LineString([(-98.9, 29.8, 400.0), (-98.8, 29.85, 398.0)]),
        ],
        crs="EPSG:4269",
    ).to_file(gdb, layer="NHDFlowline", driver="OpenFileGDB")

    gdf = ingest_nhd_flowlines.read_flowlines_file(str(gdb))

    assert gdf["reachcode"].tolist() == ["12100201000123"]
    assert gdf[ingest_nhd_flowlines.ID_FIELD].tolist() == [55000100012345]
    assert str(gdf[ingest_nhd_flowlines.ID_FIELD].iloc[0]) == "55000100012345"
    assert "gnis_name" in gdf.columns
    assert not gdf.geometry.has_z.any()
    assert gdf.crs.to_epsg() == 4326
