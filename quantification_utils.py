"""Methane plume quantification functions. from Orbio"""

import numpy as np
import rasterio
from shapely.geometry import MultiPoint
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.transform import Affine

def ppm_m_to_mol_per_m2_v0(ppm_m, air_number_density=41.6):
    """
    Convert methane concentration from ppm·m to mol/m².
    
    Parameters
    ----------
    ppm_m : float or array
        Methane column enhancement in ppm·m.
    air_number_density : float, optional
        Number density of air in mol/m³ (default ~41.6 mol/m³ at 1 atm, 25°C).
    
    Returns
    -------
    mol_per_m2 : float or array
        Methane column amount in mol/m².
    """
    return ppm_m * 1e-6 * air_number_density


def ppm_m_to_mol_per_m2(ppm_m, molar_mass=16.043, molar_volume=0.0224):
    """
    Convert methane concentration-pathlength (ppm·m) to column density (mol/m²).

    Parameters
    ----------
    ppm_m : float or array
        Methane enhancement in ppm·m (concentration-pathlength).
    molar_mass : float, optional
        Molar mass of CH4 in g/mol (default: 16.043 g/mol).
    molar_volume : float, optional
        Molar volume at STP in m³/mol (default: 0.0224 m³/mol).

    Returns
    -------
    mol_per_m2 : float or array
        Methane column density in mol/m².
    """

    # Conversion factor from ppm·m to g/m² (from paper https://arxiv.org/pdf/2107.05578)
    k = (molar_mass / molar_volume) * 1e-6  # g per (ppm·m²)
    # Mass column (g/m²)
    mass_per_area = ppm_m * k 

    # Convert g/m² to mol/m²
    mol_per_m2 = mass_per_area / molar_mass  

    return mol_per_m2

def coords_in_meters(coords):
    values = np.asarray(coords, dtype=float)
    return bool(np.max(np.abs(values)) > 1000)

def reproject_coords(coords, origin, from_epsg="EPSG:4326", to_epsg=None):
    """
    Reproject coordinates from lat/lon to meters (e.g., UTM).
    If to_epsg is None, automatically pick UTM zone from origin.
    """

    lon0, lat0 = origin
    
    # Auto-select UTM zone if not provided
    if to_epsg is None:
        utm_zone = int((lon0 + 180) // 6) + 1
        hemi = "326" if lat0 >= 0 else "327"  # 326 = north, 327 = south
        to_epsg = f"EPSG:{hemi}{utm_zone:02d}"

    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)

    if not coords_in_meters(coords):
        xs, ys = transformer.transform(*zip(*coords))
        coords_meters = list(zip(xs, ys))
    else: 
        coords_meters =  coords
    if lon0< 1000:
        x0, y0 = transformer.transform(lon0, lat0)
        origin_meters = (x0, y0)
    else: 
        origin_meters = origin

    return coords_meters, origin_meters, to_epsg


def calculate_L(plume_coords, origin, max_radius=2500):
    """
    Calculate plume length L based on convex hull.
    
    Parameters
    ----------
    plume_coords : array-like
        List or array of (x, y) coordinates (in meters) of plume pixels.
    origin : tuple
        (x0, y0) coordinates of plume origin (in meters).
    max_radius : float
        Maximum allowed radial extent (default=2500 m).
        
    Returns
    -------
    float
        Plume length L (meters).
    """
    plume_coords, origin, _ = reproject_coords(plume_coords, origin=origin)

    # Make sure inputs are numpy arrays
    plume_coords = np.array(plume_coords)
    origin = np.array(origin)

    # Build convex hull
    hull = MultiPoint(plume_coords).convex_hull

    # Extract hull boundary points
    hull_coords = np.array(hull.exterior.coords)

    # Compute distances from origin to hull vertices
    dists = np.linalg.norm(hull_coords - origin, axis=1)

    # Apply max and radial constraint
    L = min(dists.max(), max_radius)
    return L



def calc_L_IME(
    data: np.ndarray,
    plumes_coords=None,
    origin=None,
    spatial_res_m: float = 60.0,
) -> tuple[float, float, float]:
    """
    Calculate plume area, effective plume size (L), and integrated methane enhancement (IME).

    Parameters
    ----------
    data : np.ndarray
        2D array of methane retrieval values in mol/m².
    spatial_res_m : float
        Side length of each pixel in meters. Default is 60.0 m for EMIT.

    Returns
    -------
    area : float
        Total area of plume pixels in m².
    L : float
        Effective plume size in meters, defined as sqrt(area).
    IME : float
        Integrated Methane Enhancement in moles (summed retrieval * pixel area).
    """
    # Area of pixel
    # FIXME: Default value for the spatial resolution is 60.0 m, which is specific to EMIT.
    pixel_area: float = spatial_res_m * spatial_res_m

    # Calculate area of plume pixels in m² (non-zero pixels)
    area: float = np.count_nonzero(data > 0) * pixel_area

    # Effective plume size (L)
    L: float = np.sqrt(area)
    # calculate L as in carbonMapper 
    
    # L = calculate_L(plumes_coords, origin, max_radius=2500)
    # print('L from carbon mapper', L)

    # Integrated Methane Enhancement (IME)
    IME: float = np.sum(data[data > 0]) * pixel_area

    return area, L, IME


def calc_Q_IME(u_eff: float, L: float, IME: float) -> float:
    """
    Estimate the methane emission rate (Q) from effective wind speed (u_eff), effective plume size (L), and IME.

    This function implements:
    Q = (u_eff / L) x IME x 57.75286,
    where 57.75286 is the conversion factor from mol/s to kg/hr for CH₄, given:
        1 mol CH₄/s = 16.04246 g/s ≈ 0.01604 kg/s = 57.75 kg/hr.

    Parameters
    ----------
    u_eff : float
        Effective wind speed in m/s.
    L : float
        Effective plume size in meters.
    IME : float
        Integrated Methane Enhancement in moles.

    Returns
    -------
    float
        Methane emission rate, in kg/hr.
    """
    if L <= 0:
        raise ValueError("L must be greater than zero.")
    return (u_eff / L) * IME * 57.7528


def get_plume_source_location_v2(
    plume_retrieval: np.ndarray, source_crs: CRS, source_transform: Affine
) -> tuple[float, float]:
    """
    Calculate the latitude and longitude coordinates of the maximum methane retrieval pixel.

    This function:
    1. Identifies the pixel with the maximum value in `plume_retrieval`.
    2. Converts that pixel's row/column indices to real-world coordinates in `source_crs`.
    3. Transforms those coordinates into geographic coordinates (EPSG:4326).

    Parameters
    ----------
    plume_retrieval : np.ndarray
        A 2D array of methane retrieval or enhancement data. Must have two dimensions.
    source_crs : rasterio.crs.CRS
        The coordinate reference system of the `plume_retrieval`.
    source_transform : rasterio.transform.Affine
        The affine transform for converting the `plume_retrieval` array indices to real-world coordinates.

    Returns
    -------
    latitude : float
        Latitude.
    longitude : float
        Longitude.
    """
    assert len(plume_retrieval.shape) == 2, "Plume retrieval must have 2 dimesions for source location calculation"  # noqa: PLR2004 (magic-number-comparison)

    # Calculate the grid coordinates of the maximum retrieval pixel
    source_index = np.unravel_index(plume_retrieval.argmax(), plume_retrieval.shape)

    # Convert the grid (array) coordinates to real world coordinates in the source CRS
    transformer = rasterio.transform.AffineTransformer(source_transform)
    source_x_coord, source_y_coord = transformer.xy(source_index[0], source_index[1])

    # Transform real world coordinates in source CRS to latitude and longitude in CRS: 4326
    coordinate_transformer = Transformer.from_crs(
        source_crs, "EPSG:4326", always_xy=True
    )
    longitude, latitude = coordinate_transformer.transform(
        source_x_coord, source_y_coord
    )

    return latitude, longitude

