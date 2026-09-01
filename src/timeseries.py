"""
Construção do cubo temporal virtual Sentinel-2.

Fluxo:

    GeoParquet
        ↓
    HREFs dos COGs
        ↓
    VirtualTIFF
        ↓
    VirtualiZarr
        ↓
    open_virtual_mfdataset
        ↓
    dimensão temporal
        ↓
    Dataset virtual

Os pixels dos COGs não são materializados durante a construção.
"""

from urllib.parse import urlparse

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import xarray as xr

from obspec_utils.aiohttp import AiohttpStore
from obspec_utils.registry import ObjectStoreRegistry
from virtual_tiff import VirtualTIFF
from virtualizarr import open_virtual_mfdataset


def preparar_tabela(
    gdf: gpd.GeoDataFrame,
    asset: str = "B04",
) -> pd.DataFrame:

    coluna = f"{asset}_href"

    if coluna not in gdf.columns:
        raise ValueError(f"Asset '{asset}' não encontrado no GeoParquet.")

    tabela = gdf[["item_id", "datetime", coluna]].dropna(subset=[coluna]).copy()

    tabela["datetime"] = pd.to_datetime(tabela["datetime"], utc=True).dt.tz_localize(None)

    tabela = tabela.sort_values("datetime").reset_index(drop=True)

    if tabela.empty:
        raise ValueError(f"Nenhuma cena disponível para '{asset}'.")

    return tabela


def criar_registry(
    hrefs: list[str],
) -> ObjectStoreRegistry:
    """
    Cria o registry utilizado pelo VirtualiZarr.

    Os HREFs dos COGs são agrupados por domínio para que
    o acesso HTTP seja reutilizado.
    """

    if not hrefs:
        raise ValueError("Nenhum HREF foi fornecido para criar o registry.")

    stores = {}

    for href in hrefs:
        parsed = urlparse(href)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"HREF inválido ou não HTTP(S): {href}")

        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url not in stores:
            stores[base_url] = AiohttpStore(base_url)

    return ObjectStoreRegistry(stores)


def criar_parser() -> VirtualTIFF:
    """
    Cria o parser VirtualTIFF utilizado pelos COGs.

    Os arquivos utilizados possuem a imagem principal no IFD 0.
    """

    return VirtualTIFF(ifd=0)


def construir_cubo_temporal(
    gdf: gpd.GeoDataFrame,
    asset: str = "B04",
) -> xr.Dataset:
    """
    Constrói um cubo temporal virtual para um asset Sentinel-2.

    Os COGs permanecem como referências remotas.
    Os pixels não são materializados durante a construção.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Índice GeoParquet.
    asset : str
        Asset Sentinel-2, por exemplo "B04".

    Returns
    -------
    xarray.Dataset
        Dataset virtual com dimensões:
            time
            y
            x
    """

    tabela = preparar_tabela(gdf, asset=asset)

    hrefs = tabela[f"{asset}_href"].tolist()

    if not hrefs:
        raise ValueError(f"Nenhum HREF disponível para o asset '{asset}'.")

    registry = criar_registry(hrefs)

    parser = criar_parser()

    datasets = open_virtual_mfdataset(urls=hrefs, registry=registry, parser=parser, concat_dim="time", combine="nested")

    datas = pd.to_datetime(tabela["datetime"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")

    if "time" in datasets.dims:
        datasets = datasets.assign_coords(time=datas)
    else:
        datasets = datasets.expand_dims(time=datas)

    if "0" in datasets.data_vars:
        datasets = datasets.rename({"0": asset})

    with rasterio.open(hrefs[0]) as src:
        transform = src.transform
        x = transform.c + (np.arange(src.width) + 0.5) * transform.a
        y = transform.f + (np.arange(src.height) + 0.5) * transform.e
        datasets = datasets.assign_coords(x=x, y=y)
        crs = src.crs.to_wkt() if src.crs else None
        datasets.attrs["crs"] = crs
        datasets[asset].attrs["crs"] = crs

    return datasets


def resumir_cubo(
    ds: xr.Dataset,
) -> None:
    """
    Exibe informações estruturais do cubo virtual.

    A função não acessa os pixels.
    """

    print()
    print("=" * 60)
    print("CUBO TEMPORAL VIRTUAL")
    print("=" * 60)

    print()
    print("Dimensões:")
    print(dict(ds.sizes))

    print()
    print("Variáveis:")
    print(list(ds.data_vars))

    print()
    print("Coordenadas:")
    print(list(ds.coords))

    print()
    print("Arrays:")

    for nome, da in ds.data_vars.items():
        print()
        print(f"  {nome}")
        print(f"    shape  = {da.shape}")
        print(f"    dtype  = {da.dtype}")
        print(f"    tipo   = {type(da.data)}")

    print()
    print("Virtualização:")

    for nome, da in ds.data_vars.items():
        eh_virtual = "ManifestArray" in str(type(da.data))

        print(f"  {nome}: {'ManifestArray' if eh_virtual else type(da.data).__name__}")
