"""
Construção do cubo de dados multivariável Sentinel-2.

Fluxo:

    GeoParquet
        ↓
    Assets prioritários
        ↓
    COGs
        ↓
    VirtualTIFF
        ↓
    ManifestArray
        ↓
    Cubos temporais por variável
        ↓
    Dataset multivariável

Exemplo de saída:

    <xarray.Dataset>
    Dimensions:
        time: 4
        y: 10560
        x: 10560

    Data variables:
        B01
        B02
        B03
        ...
        NDVI
        EVI
        NBR
        SCL
        CLEAROB
"""

import geopandas as gpd
import xarray as xr

from config import VARIAVEIS_PRIORITARIAS_POR_COLECAO
from timeseries import construir_cubo_temporal


def obter_variaveis_prioritarias(collection: str,) -> tuple[str, ...]:
    """
    Retorna os assets prioritários definidos no config.py.
    """

    if collection not in VARIAVEIS_PRIORITARIAS_POR_COLECAO:
        raise ValueError(f"Coleção '{collection}' não está definida em VARIAVEIS_PRIORITARIAS_POR_COLECAO.")

    return VARIAVEIS_PRIORITARIAS_POR_COLECAO[collection]


def verificar_assets(gdf: gpd.GeoDataFrame, assets: tuple[str, ...],) -> dict:
    """
    Verifica quais assets possuem HREFs disponíveis
    no GeoParquet.

    Returns
    -------
    dict
        Dicionário com assets disponíveis e ausentes.
    """

    disponiveis = []
    ausentes = []

    for asset in assets:
        coluna = f"{asset}_href"

        if coluna not in gdf.columns:
            ausentes.append(asset)
            continue

        if gdf[coluna].notna().any():
            disponiveis.append(asset)
        else:
            ausentes.append(asset)

    return {
        "disponiveis": disponiveis,
        "ausentes": ausentes,
    }


def construir_cubo(gdf: gpd.GeoDataFrame, collection: str = "S2-16D-2", assets: tuple[str, ...] | None = None,) -> xr.Dataset:
    """
    Constrói o cubo virtual multivariável.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Índice GeoParquet.

    collection : str
        Nome da coleção Sentinel-2.

    assets : tuple[str, ...], optional
        Assets a serem utilizados.
        Se None, utiliza os definidos no config.py.

    Returns
    -------
    xarray.Dataset
        Cubo temporal multivariável virtual.
    """

    if assets is None:
        assets = obter_variaveis_prioritarias(collection)

    print("=" * 60)
    print("CONSTRUÇÃO DO CUBO MULTIVARIÁVEL")
    print("=" * 60)

    print()
    print(f"Coleção: {collection}")

    print()
    print("Assets solicitados:")

    for asset in assets:
        print(f"  - {asset}")

    status = verificar_assets(gdf, assets)

    print()
    print("Assets disponíveis:")

    for asset in status["disponiveis"]:
        print(f"  [Sucesso] {asset}")

    if status["ausentes"]:
        print()
        print("Assets ausentes:")

        for asset in status["ausentes"]:
            print(f"  ✗ {asset}")

    if not status["disponiveis"]:
        raise ValueError("Nenhum asset disponível.")

    cubos = {}

    for asset in status["disponiveis"]:
        print()
        print("-" * 60)
        print(f"Asset: {asset}")
        print("-" * 60)

        ds_asset = construir_cubo_temporal(gdf, asset=asset)

        cubos[asset] = ds_asset

    primeiro_asset = next(iter(cubos))
    referencia = cubos[primeiro_asset]
    dims_referencia = dict(referencia.sizes)
    tempos_referencia = referencia.time.values if "time" in referencia.coords else None

    print()
    print("=" * 60)
    print("VALIDAÇÃO DOS CUBOS")
    print("=" * 60)

    for asset, ds in cubos.items():
        dims = dict(ds.sizes)

        print()
        print(f"{asset}:")
        print(f"  dimensões = {dims}")

        if dims != dims_referencia:
            raise ValueError(f"O asset '{asset}' possui dimensões diferentes do asset '{primeiro_asset}'.\nEsperado: {dims_referencia}\nObtido: {dims}")

        if "time" in ds.coords:
            tempos = ds.time.values

            if tempos_referencia is not None:
                if len(tempos) != len(tempos_referencia):
                    raise ValueError(f"O asset '{asset}' possui quantidade de datas diferente.")

                for t1, t2 in zip(tempos, tempos_referencia):
                    if t1 != t2:
                        raise ValueError(f"As datas do asset '{asset}' não coincidem com o asset de referência.")

    print()
    print("=" * 60)
    print("COMBINANDO VARIÁVEIS")
    print("=" * 60)

    datasets = list(cubos.values())
    ds_final = xr.merge(datasets, compat="override", join="exact")

    print()
    print("Cubo multivariável criado.")

    print()
    print(ds_final)

    return ds_final


def resumir_cubo(ds: xr.Dataset,) -> None:
    """
    Mostra um resumo do cubo multivariável.
    """
    print()
    print("=" * 60)
    print("RESUMO DO CUBO")
    print("=" * 60)

    print()
    print("Dimensões:")

    for nome, tamanho in ds.sizes.items():
        print(f"  {nome}: {tamanho}")

    print()
    print("Variáveis:")

    for nome, da in ds.data_vars.items():
        print(f"  {nome}:")
        print(f"    shape = {da.shape}")
        print(f"    dtype = {da.dtype}")
        print(f"    tipo  = {type(da.data)}")

        print(f"    array = {da.data}")

    print()

    if "time" in ds.coords:
        print("Período temporal:")

        print(f"  início: {ds.time.values[0]}")

        print(f"  fim:    {ds.time.values[-1]}")
