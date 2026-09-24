from pathlib import Path
import geopandas as gpd
import fiona

GPKG = Path("GeoVault_Geospatial_All_Mines_FINAL.gpkg")

def list_layers():
    return fiona.listlayers(GPKG)

def load_layer(mine_code: str, layer: str):
    return gpd.read_file(GPKG, layer=f"{mine_code.upper()}_{layer}")

if __name__ == "__main__":
    print("Available layers:")
    for name in list_layers():
        print(" -", name)

    print("\nExample:")
    print(load_layer("GEVRA", "boreholes").head())
