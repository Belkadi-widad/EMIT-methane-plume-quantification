"""Small client helpers for the Carbon Mapper API and STAC catalog."""

import time

import pandas as pd
import requests
from pystac_client import Client

BASE_URL = "https://api.carbonmapper.org/api/v1"


class CarbonMapperAuth:
    """Manage Carbon Mapper access and refresh tokens."""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.expiry_time = 0.0

    def get_token_pair(self):
        response = requests.post(
            f"{BASE_URL}/token/pair",
            json={"email": self.email, "password": self.password},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access"]
        self.refresh_token = data["refresh"]
        self.expiry_time = time.time() + 3600
        return self.access_token

    def refresh_access_token(self):
        if not self.refresh_token:
            raise ValueError("No refresh token available. Call get_token_pair first.")
        response = requests.post(
            f"{BASE_URL}/token/refresh",
            json={"refresh": self.refresh_token},
            timeout=30,
        )
        response.raise_for_status()
        self.access_token = response.json()["access"]
        self.expiry_time = time.time() + 3600
        return self.access_token

    def get_valid_access_token(self):
        if self.access_token and time.time() < self.expiry_time:
            return self.access_token
        if self.refresh_token:
            return self.refresh_access_token()
        return self.get_token_pair()

    def authorized_get(self, endpoint: str, **kwargs):
        token = self.get_valid_access_token()
        response = requests.get(
            f"{BASE_URL}/{endpoint.lstrip('/')}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()


def get_carbonmapper_plumes(
    auth: CarbonMapperAuth,
    start_date: str,
    end_date: str,
    bbox: list[float],
    limit: int = 1000,
) -> list[dict]:
    """Retrieve annotated EMIT methane plumes for a time range and bounding box."""
    params = {
        "datetime": f"{start_date}/{end_date}",
        "plume_gas": "CH4",
        "instrument": "emi",
        "sectors": "1B2",
        "bbox": bbox,
        "limit": limit,
        "offset": 0,
        "sort": "emissions_desc",
    }
    plumes = []
    while True:
        token = auth.get_valid_access_token()
        response = requests.get(
            f"{BASE_URL}/catalog/plumes/annotated",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        features = response.json().get("items", [])
        plumes.extend(features)
        if len(features) < limit:
            return plumes
        params["offset"] += limit


def get_IME_data(
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
    bbox: list[float] = [5.027957, 30.72952, 7.027957, 32.72952],
) -> pd.DataFrame:
    """Retrieve Carbon Mapper IME records as a DataFrame."""
    catalog = Client.open(f"{BASE_URL}/stac")
    search = catalog.search(
        collections=["l3a-ime-ch4"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
    )
    records = []
    for item in search.item_collection():
        properties = item.properties
        records.append(
            {
                "cm_date": properties["datetime"][:10],
                "cm_coords": (
                    properties.get("cm:plume_latitude"),
                    properties.get("cm:plume_longitude"),
                ),
                "cm_ime": properties.get("cm:ime"),
                "cm_id": item.id,
            }
        )
    return pd.DataFrame(records)


def get_l2b_data():
    """Return Carbon Mapper L2B methane STAC items for the example date."""
    catalog = Client.open(f"{BASE_URL}/stac")
    search = catalog.search(datetime="2023-03-05", collections=["l2b-ch4"])
    return list(search.items())
