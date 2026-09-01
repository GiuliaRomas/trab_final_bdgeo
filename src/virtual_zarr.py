"""
Virtualização de GeoTIFF/COG usando VirtualiZarr + VirtualTIFF.

Fluxo:

    COG remoto
        ↓
    AiohttpStore
        ↓
    ObjectStoreRegistry
        ↓
    VirtualTIFF
        ↓
    VirtualiZarr
        ↓
    xarray.Dataset virtual

Os pixels não são baixados integralmente.
O VirtualTIFF cria referências aos intervalos de bytes
do TIFF original.
"""

import xarray as xr

from obspec_utils.registry import ObjectStoreRegistry
from obspec_utils.aiohttp import AiohttpStore

from virtualizarr import open_virtual_dataset
from virtual_tiff import VirtualTIFF


def criar_registry_http(
    href: str,
):
    """
    Cria um ObjectStoreRegistry para o domínio do arquivo.

    Parameters
    ----------
    href : str
        URL HTTPS do GeoTIFF.

    Returns
    -------
    tuple
        (registry, store_base_url)
    """

    from urllib.parse import urlparse

    parsed = urlparse(href)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    store = AiohttpStore(base_url)

    registry = ObjectStoreRegistry({base_url: store})

    return registry, base_url


def abrir_cena_virtual(
    href: str,
    ifd: int = 0,
    loadable_variables=None,
):
    """
    Abre um GeoTIFF/COG remoto como Dataset virtual.

    Parameters
    ----------
    href : str
        URL HTTPS do GeoTIFF.

    ifd : int
        IFD do TIFF que será virtualizado.
        Para um TIFF simples de uma banda, usamos 0.

    loadable_variables : iterable, optional
        Variáveis que devem ser carregadas normalmente.
        Por padrão, nenhuma variável de dados é materializada.

    Returns
    -------
    xarray.Dataset
        Dataset virtual.
    """

    registry, _ = criar_registry_http(href)

    parser = VirtualTIFF(ifd=ifd)

    ds = open_virtual_dataset(url=href, registry=registry, parser=parser, loadable_variables=loadable_variables)

    return ds


def resumir_dataset(
    ds: xr.Dataset,
) -> dict:
    """
    Resume a estrutura do Dataset virtual.
    """

    resumo = {
        "dims": dict(ds.sizes),
        "data_vars": list(ds.data_vars),
        "coords": list(ds.coords),
    }

    variaveis = {}

    for nome, da in ds.data_vars.items():
        variaveis[nome] = {
            "dims": da.dims,
            "shape": da.shape,
            "dtype": str(da.dtype),
            "chunks": da.chunks,
        }

    resumo["variaveis"] = variaveis

    return resumo


def validar_dataset_virtual(
    ds: xr.Dataset,
) -> None:
    """
    Valida a estrutura básica do Dataset virtual.
    """

    if not isinstance(ds, xr.Dataset):
        raise TypeError("O objeto retornado não é um xarray.Dataset.")

    if not ds.data_vars:
        raise ValueError("O dataset virtual não possui variáveis.")

    print("Dataset virtual válido.")
    print()
    print(ds)
