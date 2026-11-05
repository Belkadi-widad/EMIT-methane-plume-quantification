# EMIT methane plume quantification

Tools for exploring methane plume products from NASA's Earth Surface Mineral Dust Source Investigation (EMIT), Carbon Mapper, and meteorological reanalysis data.

The project loads EMIT and Carbon Mapper plume products, extracts plume metadata, retrieves wind fields, and estimates emissions using the integrated methane enhancement (IME) approach.

## What is included

- `emit_data.py` — pairs EMIT plume GeoTIFFs with their metadata and returns the raster, geometry, metadata, and source path.
- `quantification_utils.py` — converts methane retrievals and calculates plume area, length, IME, and emission rate.
- `wind_data.py` — downloads or opens GEOS-FP and ERA5 wind data and calculates effective wind speed.
- `carbonmapper.py` — queries Carbon Mapper's catalog and STAC API.
- `emit_quantification.ipynb` — an end-to-end exploratory workflow.

## Quick start

### 1. Create an environment

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

Some optional download paths also require `ecmwf-opendata`, `cfgrib`, and a configured Copernicus CDS API account.

### 3. Use the modules

```python
from emit_data import get_plumes_data_metadata
from quantification_utils import calc_Q_IME, calc_L_IME

plumes = get_plumes_data_metadata("path/to/EMITL2BCH4PLM", date="20230216")
plume = next(iter(plumes.values()))
area, length, ime = calc_L_IME(plume["data"])
emissions_kg_per_hour = calc_Q_IME(
    u_eff=1.0,
    L=length,
    IME=ime,
)
```

The notebook contains the full workflow, including wind-data retrieval and comparisons with Carbon Mapper products.

## Data and credentials

Large remote-sensing rasters and downloaded meteorological files are intentionally excluded from version control by `.gitignore`. Keep local datasets outside the repository when possible and do not commit API keys, passwords, or tokens.

Carbon Mapper requests require an account. Pass credentials at runtime (for example through environment variables or a secret manager); never hard-code them in source files.

## Scientific notes

The current analysis compares retrieval, segmentation, and quantification differences between EMIT and Carbon Mapper products. The conversion constants and effective-wind model should be treated as analysis assumptions and validated against the product documentation before publishing scientific conclusions.

## Status

This is an exploratory research project. Contributions that improve reproducibility, validation, tests, or documentation are welcome.
