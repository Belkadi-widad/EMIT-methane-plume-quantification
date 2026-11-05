import xarray as xr
import cdsapi
import os
from datetime import timedelta
from dateutil.parser import parse as parse_datetime 
import requests  # type: ignore
import numpy as np



################ download GEOS_FP ##################


WIND_DATA_BASE_URL_TPL = "https://portal.nccs.nasa.gov/datashare/gmao/geos-fp/das/Y{:04}/M{:02}/D{:02}"
WIND_ENTRY_NAME_TPL = "GEOS.fp.asm.{}.{:04}{:02}{:02}_{:02}00.V01.nc4"
WIND_PRODUCT = "inst3_2d_asm_Nx"

def download_wind_data_from_GEOS_FP(sensing_time_str: str) -> xr.Dataset | None:
    """Download wind data from GEOS_FP for a given date."""
    sensing_time = parse_datetime(sensing_time_str)

    base_url = WIND_DATA_BASE_URL_TPL.format(sensing_time.year, sensing_time.month, sensing_time.day)
    entry_path = WIND_ENTRY_NAME_TPL.format(
        WIND_PRODUCT,
        sensing_time.year,
        sensing_time.month,
        sensing_time.day,
        sensing_time.hour,
    )

    tmp_file = f"wind/geos_fp_data_{entry_path}"  # Temporary file location

    if  os.path.exists(tmp_file):
        # Open the NetCDF file using xarray
        ds = xr.open_dataset(tmp_file)
        # os.remove(tmp_file)
        return ds
    else:

        
        url = f"{base_url}/{entry_path}"  # URL for the GEOS-FP data file
        print(f"{url=}")
        
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            # Save the file to the temporary location
            with open(tmp_file, "wb") as f:
                f.write(response.content)

            # Open the NetCDF file using xarray
            ds = xr.open_dataset(tmp_file)
            # os.remove(tmp_file)
            return ds

        except Exception as e:
            print(f"Failed to download wind data. Reason: {e}")
            return None


##################### era5 ########################""

def get_area(aoi_tuple):
    """
       aoi tuple of format : (minlon, minlat, maxlon, maxlat)
    """

    minlon, minlat, maxlon, maxlat = aoi_tuple
    return [maxlat, minlon, minlat, maxlon]


def download_cds_data(dataset_name, request, output_file_name, zipped  =False, data_format ='netcdf' ):

    c = cdsapi.Client()    

    # If zipped requested (CDS mainly zips GRIB multiple files)
    if zipped and data_format == 'grib':
        request['format'] = 'grib'

    if not os.path.exists(output_file_name):
        # Retrieve data
        c.retrieve(
            dataset_name,
            request,
            output_file_name
        )

        print(f"✅ Download complete: {output_file_name}")

    # Open the NetCDF file using xarray
    ds = xr.open_dataset(output_file_name)

    return ds



def download_wind_data_from_ERA5(variables,
    start_date,
    end_date,
    times,
    area,
    output_dir,
    data_format='netcdf',
    zipped=False):

    """
    ERA5 Download CDS API ingestion function.
    
    Parameters:
    - dataset_name: str, e.g. 'reanalysis-era5-single-levels'
    - variables: list of variable names
    - start_date, end_date: 'YYYY-MM-DD' strings
    - times: list of 'HH:MM' times (e.g. ['00:00','06:00','12:00','18:00'])
    - area: [N, W, S, E]
    - output_dir: path to save files
    - data_format: 'netcdf' or 'grib'
    - zipped: if True, downloads zipped multiple files (mainly for GRIB)
    """

    dataset_name = "reanalysis-era5-land"
    dataset_name = "reanalysis-era5-single-levels"
    product_type = "reanalysis"

    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate list of years, months, days within date range
    # s_date = datetime.strptime(start_date, '%Y-%m-%d')
    # e_date = datetime.strptime(end_date, '%Y-%m-%d')
    delta = end_date - start_date

    dates = [(start_date + timedelta(days=i)) for i in range(delta.days + 1)]
    years = sorted(list(set([d.strftime('%Y') for d in dates])))
    months = sorted(list(set([d.strftime('%m') for d in dates])))
    days = sorted(list(set([d.strftime('%d') for d in dates])))

    # Define output file name
    file_ext = 'nc' if data_format == 'netcdf' else 'grib'
    zip_suffix = '.zip' if zipped else ''
    
    output_file = os.path.join(
        output_dir,
        f"{dataset_name}_{start_date}_to_{end_date}_{area}.{file_ext}{zip_suffix}"
    )

    # Build request
    request = {
        'product_type': product_type,
        'variable': variables,
        'year': years,
        'month': months,
        'day': days,
        'time': times,
        'format': data_format,
        'area': area,  # [N, W, S, E]
    }

    return download_cds_data(dataset_name= dataset_name, request=request,  data_format=data_format, zipped=zipped, 
                      output_file_name = output_file )

################ ecmwf wind data #################""


# Install if needed: pip install ecmwf-opendata
from ecmwf.opendata import Client
import xarray as xr
import os



def download_wind_data_from_ecmwf(date, variables = ["10u", "10v"], step = 0,  time = 0 , grid = "0.1/0.1" , out_dir = "wind"  ):
    # Create output directory
    
    os.makedirs(out_dir, exist_ok=True)

    # Initialize ECMWF Open Data client (default is the latest HRES cycle)
    client = Client(source="ecmwf")

    # Download both parameters
    # for param in variables:
    target_file = os.path.join(out_dir, f"wind_{date}{time}.grib2")
    print(f"Downloading {variables} to {target_file}...")
    # result = client.retrieve(
    #         stream="oper",          # operational HRES
    #         #  infer_stream_keyword = True,
    #         type="fc",              # forecast
    #         # levtype="sfc",          # surface fields
    #         param="10u",            # variable (10u or 10v)
    #         date=date,              # date
    #         time=time,              # run time
    #         # step=step,              # forecast step
    #         target=target_file      # save path
    #     )
    result = client.retrieve(
    date="2023-08-19 00:00:00",
    time=0,
    step=12,
    stream="enfo",
    type="cf",
    levtype="pl",
    levelist=200,
    param=['u','v'],
    model="aifs-ens",
    target=target_file
    )
    

    print("Download complete.", result.datetime)

    # Optional: open with xarray + cfgrib
    ds_wind = xr.open_dataset(os.path.join(out_dir, f"wind_{date}{time}.grib2"), engine="cfgrib")
    # ds_v10 = xr.open_dataset(os.path.join(out_dir, f"10v_{date}{time}.grib2"), engine="cfgrib")

    # # Combine into one dataset
    # ds_combined = xr.merge([ds_u10, ds_v10])

    # # Save to a new NetCDF file
    # ds_combined.to_netcdf(os.path.join(out_dir, f"wind_{date}{time}.nc"))


    return ds_wind



def download_wind_data(sensing_date , bbox, source="GEOS_FP", output_dir = "wind"):

    if source == "GEOS_FP":
        return download_wind_data_from_GEOS_FP(sensing_date)

    elif source == "ERA5":
        sensing_time = parse_datetime(sensing_date)
        area = get_area(bbox)
        variables = ['10m_u_component_of_wind', '10m_v_component_of_wind']
        times = ['13:00']

        return  download_wind_data_from_ERA5( variables = variables, start_date= sensing_time, 
                                               end_date = sensing_time,
                            times= times, area= area, output_dir = output_dir, data_format='netcdf', zipped=False)
        
    else:
        raise ValueError(f"Unsupported wind-data source: {source}")


# TODO: find better solution than 0.5 for error
WIND_ERROR = 0.5

def get_wind_speed_for_plume(
    wind_ds: xr.Dataset,
    source_ds: str,
    plume_source_lat: float,
    plume_source_lon: float,
) -> tuple[float, float, float, float, float]:
    """Get the wind vector for the plume source location and calculate the effective wind speeds."""
    
    u_wind_component, v_wind_component = get_wind_vectors_from_wind_tile(wind_ds, plume_source_lat, plume_source_lon, source_ds)

    wind_speed = calc_effective_wind_speed(u_wind_component, v_wind_component)
    wind_direction = calc_wind_direction(u_wind_component, v_wind_component)

    # Calculate the wind error margin
    wind_low, wind_high = calc_wind_error(wind_speed, wind_error=WIND_ERROR)

    u_eff, u_eff_high, u_eff_low = calc_u_eff(wind_speed, wind_low, wind_high)

    return u_eff, u_eff_high, u_eff_low, wind_direction, u_wind_component

def get_wind_vectors_from_wind_tile(wind_ds: xr.Dataset, plume_lat: float, plume_lon: float, source_ds = "GEOS_FP"  ) -> tuple[float, float]:
    """Extract the U and V components from the wind dataset for the specific lat and lon."""

    if source_ds == "GEOS_FP":
        u10_varname, v10_varname = "U10M", "V10M"
        lat_name, lon_name = "lat", "lon"
    elif source_ds == "ERA5":
        u10_varname, v10_varname = "u10", "v10"
        lat_name, lon_name = "latitude", "longitude"
    elif source_ds == "ECMWF":
        u10_varname, v10_varname = "10u", "10v"
        lat_name, lon_name = "latitude", "longitude"
    else:
        raise ValueError(f"Unsupported wind dataset source: {source_ds}")

    u_wind_component = wind_ds[u10_varname].sel(
        {lat_name: plume_lat, lon_name: plume_lon}, method="nearest"
    ).values.item()
    v_wind_component = wind_ds[v10_varname].sel(
        {lat_name: plume_lat, lon_name: plume_lon}, method="nearest"
    ).values.item()

    return u_wind_component, v_wind_component


def calc_effective_wind_speed(u10m: float, v10m: float) -> float:
    """
    Compute the total wind speed in m/s from the zonal (u) and meridional (v) components at 10 m height.

    Calculated as the magnitude of the 2D wind vector: sqrt(u10m^2 + v10m^2).

    Parameters
    ----------
    u10m : float
        Zonal wind component at 10 m, in m/s. Positive values indicate eastward flow.
    v10m : float
        Meridional wind component at 10 m, in m/s. Positive values indicate northward flow.

    Returns
    -------
    float
        The wind speed at 10 m height, in m/s.
    """
    return np.sqrt(np.square(u10m) + np.square(v10m))



def calc_u_eff(wind_speed: float, wind_low: float, wind_high: float) -> tuple[float, float, float]:
    """
    Calculate effective wind speed and its uncertainty bounds using Varon et al. (2021) fitted parameters.

    The effective wind speed, u_eff, is modeled as:
        u_eff = alpha * ln(wind_speed + epsilon) + beta
    where alpha=0.33 and beta=0.45 are empirically derived for Sentinel 2 based on LES Simulations. A minimum
    effective wind speed of 0.01 m/s is enforced. This function also calculates the upper and lower effective
    wind speed by applying the same formula to `wind_high` and `wind_low`, respectively.

    Parameters
    ----------
    wind_speed : float
        Central estimate of wind speed in m/s.
    wind_low : float
        Lower bound of wind speed in m/s.
    wind_high : float
        Upper bound of wind speed in m/s.

    Returns
    -------
        tuple[float, float, float]: Effective wind speed, upper bound, and lower bound in m/s

    References
    ----------
        Varon 2021: https://amt.copernicus.org/articles/14/2771/2021/
        Discussion on gitlab: https://git.orbio.earth/orbio/orbio/-/issues/869
    """
    # Model parameters from Varon 2021
    alpha, beta = 0.33, 0.45

    # Small constant to avoid log(0)
    epsilon = 1e-16

    # Calculate effective wind speeds
    u_eff = max(alpha * np.log(wind_speed + epsilon) + beta, 0.01)
    u_eff_low = max(alpha * np.log(wind_low + epsilon) + beta, 0.009)
    u_eff_high = max(alpha * np.log(wind_high + epsilon) + beta, 0.011)

    return u_eff, u_eff_high, u_eff_low


def calc_wind_direction(u10m: float, v10m: float) -> float:
    """
    Compute wind direction in degrees from the zonal (u) and meridional (v) wind components at 10 m height.

    Parameters
    ----------
    u10m : float
        Zonal wind component at 10 m, in m/s.
    v10m : float
        Meridional wind component at 10 m, in m/s.

    Returns
    -------
    float
        Wind direction in degrees, measured from north.
    """
    return float(np.degrees(np.arctan2(u10m, v10m)))


def calc_wind_error(wind_speed: float, wind_error: float) -> tuple[float, float]:
    """
    Calculate lower and upper bounds of the wind speed given a fractional error.

    Parameters
    ----------
    wind_speed : float
        Central estimate of wind speed in m/s.
    wind_error : float
        Fractional error (e.g., 0.1 for ±10% error).

    Returns
    -------
    wind_low : float
        Wind speed lower bound in m/s (wind_speed * (1 - wind_error)).
    wind_high : float
        Wind speed upper bound in m/s (wind_speed * (1 + wind_error)).
    """
    wind_low: float = wind_speed * (1 - wind_error)
    wind_high: float = wind_speed * (1 + wind_error)
    return wind_low, wind_high
