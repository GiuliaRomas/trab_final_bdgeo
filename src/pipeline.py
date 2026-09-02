"""
Pipeline principal do cubo Sentinel-2.

Fluxo:

    GeoParquet
        ↓
    seleção dos assets
        ↓
    COGs remotos
        ↓
    VirtualTIFF
        ↓
    VirtualiZarr / ManifestArray
        ↓
    cubos temporais
        ↓
    cubo multivariável
"""

import xarray as xr

from config import (COLECOES_RECOMENDADAS, VARIAVEIS_PRIORITARIAS_POR_COLECAO,)
from geoparquet import ler_geoparquet
from cube import construir_cubo


def mostrar_configuracao(collection: str, assets=None,) -> None:
    """
    Exibe a configuração utilizada pelo pipeline.
    """
    if collection not in COLECOES_RECOMENDADAS:
        raise ValueError(f"Coleção '{collection}' não está definida em COLECOES_RECOMENDADAS.")

    assets = tuple(assets) if assets is not None else VARIAVEIS_PRIORITARIAS_POR_COLECAO[collection]

    print("=" * 60)
    print("PIPELINE SENTINEL-2")
    print("=" * 60)

    print()
    print("Coleção:")
    print(f"  {collection}")

    print()
    print("Descrição:")
    print(f"  {COLECOES_RECOMENDADAS[collection]}")

    print()
    print("Assets:")
    for asset in assets:
        print(f"  - {asset}")


def executar_pipeline(collection: str = "S2-16D-2", assets=None,) -> xr.Dataset:
    """
    Executa o pipeline completo.
    """

    if collection not in COLECOES_RECOMENDADAS:
        raise ValueError(f"Coleção '{collection}' não está definida em COLECOES_RECOMENDADAS.")

    mostrar_configuracao(collection=collection, assets=assets)

    print()
    print("=" * 60)
    print("ETAPA 1 — GEOPARQUET")
    print("=" * 60)

    gdf = ler_geoparquet(collection)

    if gdf.empty:
        raise ValueError(f"O GeoParquet da coleção '{collection}' está vazio.")

    print()
    print(f"Registros encontrados: {len(gdf)}")

    print()
    print("=" * 60)
    print("ETAPA 2 — CUBO VIRTUAL")
    print("=" * 60)

    ds = construir_cubo(gdf=gdf, collection=collection, assets=assets)

    print()
    print("=" * 60)
    print("PIPELINE CONCLUÍDO")
    print("=" * 60)

    print()
    print(ds)

    return ds


def validar_cubo(ds: xr.Dataset,) -> dict:
    """
    Valida a estrutura básica do cubo virtual.
    """

    resultado = {
        "dimensoes": dict(ds.sizes),
        "variaveis": list(ds.data_vars),
        "coordenadas": list(ds.coords),
        "virtual": {},
    }

    for nome, da in ds.data_vars.items():
        tipo_array = type(da.data).__name__

        resultado["virtual"][nome] = {
            "tipo": tipo_array,
            "virtual": "ManifestArray" in tipo_array,
        }

    return resultado


def mostrar_validacao(ds: xr.Dataset,) -> None:
    """
    Exibe um resumo da validação do cubo.
    """
    resultado = validar_cubo(ds)

    print()
    print("=" * 60)
    print("VALIDAÇÃO DO CUBO")
    print("=" * 60)

    print()
    print("Dimensões:")
    for nome, tamanho in resultado["dimensoes"].items():
        print(f"  {nome}: {tamanho}")

    print()
    print("Variáveis:")
    for variavel in resultado["variaveis"]:
        info = resultado["virtual"][variavel]

        print(f"  {variavel}: {info['tipo']} (virtual={info['virtual']})")

    print()
    print("Coordenadas:")
    for coordenada in resultado["coordenadas"]:
        print(f"  - {coordenada}")
