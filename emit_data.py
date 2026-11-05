import os
import glob
from pathlib import Path

import rasterio
import json


def get_plumes_data_metadata(base_dir, date=None, version=None):
    """
    Get EMIT CH4PLM plume complexes (TIFF + JSON) for a certain date.
    
    Parameters:
        base_dir (str): Directory containing CH4PLM files
        date (str, optional): Date in format YYYYMMDD to filter (default: None = all dates)
        version (str, optional): Version string like '001' (default: None = all versions)
    """
    # Build pattern for TIFF files
    tiff_pattern = os.path.join(base_dir, "EMIT_L2B_CH4PLM_*.tif")
    json_pattern = os.path.join(base_dir, "EMIT_L2B_CH4PLMMETA_*.json")
    
    tiff_files = glob.glob(tiff_pattern)
    json_files = glob.glob(json_pattern)

    # Apply filters
    if date:
        tiff_files = [f for f in tiff_files if f"_{date}" in f]
        json_files = [f for f in json_files if f"_{date}" in f]
    if version:
        tiff_files = [f for f in tiff_files if f"_{version}_" in f]
        json_files = [f for f in json_files if f"_{version}_" in f]

    # Group files by plume identifier (last 6 digits before extension)
    plumes = {}
    for tiff in tiff_files:
        plume_id = os.path.basename(tiff).split("_")[-1].replace(".tif", "")
        plumes.setdefault(plume_id, {})["tif"] = tiff
    for js in json_files:
        plume_id = os.path.basename(js).split("_")[-1].replace(".json", "")
        plumes.setdefault(plume_id, {})["json"] = js

    plumes_results = {}
    for plume_id, files in plumes.items():
        if "tif" not in files or "json" not in files:
            continue
        # Load raster
        with rasterio.open(files["tif"]) as src:
            img = src.read(1)

        # Load JSON metadata
        with open(files["json"], "r", encoding="utf-8") as f:
            metadata = json.load(f)

        feature = metadata["features"][0]
        plumes_results[plume_id] = {
            "data": img,
            "metadata": feature.get("properties", {}),
            "geometry": feature.get("geometry", {}),
            "tif_path": str(Path(files["tif"])),
        }
       
    return plumes_results
