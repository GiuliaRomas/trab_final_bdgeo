"""
Construção e consulta do índice GeoParquet a partir de itens STAC.

Fluxo:

    Itens STAC
        ↓
    GeoDataFrame
        ↓
    GeoParquet
        ↓
    HREFs dos assets
        ↓
    VirtualTIFF / VirtualiZarr

O GeoParquet funciona como índice dos dados.
"""

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from config import (COLECAO_PADRAO, INDEX_DIR, VARIAVEIS_PRIORITARIAS_POR_COLECAO,)

def itens_para_geodataframe(itens: Iterable, variaveis: Iterable[str] | None = None,) -> gpd.GeoDataFrame:
    """
    Converte itens STAC em GeoDataFrame.
    Cada linha representa um item/cena STAC.
    """
    registros = []

    for item in itens:
        collection_id = item.collection_id or COLECAO_PADRAO

        if variaveis is None:
            variaveis_item = VARIAVEIS_PRIORITARIAS_POR_COLECAO.get(collection_id, ())
        else:
            variaveis_item = tuple(variaveis)

        registro = {
            "item_id": item.id,
            "collection": collection_id,
            "datetime": item.datetime,
            "bbox": item.bbox,
            "geometry": (shape(item.geometry) if item.geometry is not None else None),
        }

        for chave, valor in item.properties.items():
            if chave not in registro:
                registro[chave] = valor

        for variavel in variaveis_item:
            asset = item.assets.get(variavel)

            registro[f"{variavel}_href"] = asset.href if asset is not None else None

        registros.append(registro)

    if not registros:
        return gpd.GeoDataFrame(columns=["item_id", "collection", "datetime", "geometry"], geometry="geometry", crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(registros, geometry="geometry", crs="EPSG:4326")

    if "datetime" in gdf.columns:
        gdf["datetime"] = pd.to_datetime(gdf["datetime"], utc=True)

        gdf = gdf.sort_values("datetime").reset_index(drop=True)

    return gdf


def salvar_geoparquet(gdf: gpd.GeoDataFrame, caminho: str | Path,) -> Path:
    """
    Salva o índice GeoDataFrame em GeoParquet.
    """
    caminho = Path(caminho)

    if caminho.suffix.lower() != ".parquet":
        raise ValueError("O caminho do GeoParquet deve terminar em '.parquet'.")

    caminho.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(caminho, index=False)

    return caminho


def ler_geoparquet(colecao: str = COLECAO_PADRAO, diretorio: str | Path = INDEX_DIR,) -> gpd.GeoDataFrame:
    """
    Lê o GeoParquet de uma coleção.
    """
    caminho = Path(diretorio) / f"{colecao}.parquet"

    if not caminho.exists():
        raise FileNotFoundError(f"GeoParquet não encontrado para a coleção '{colecao}': {caminho}")

    gdf = gpd.read_parquet(caminho)

    if "datetime" in gdf.columns:
        gdf["datetime"] = pd.to_datetime(gdf["datetime"], utc=True)

    return gdf


def filtrar_por_geometria(gdf: gpd.GeoDataFrame, geometria,) -> gpd.GeoDataFrame:
    """
    Retorna os itens que intersectam uma geometria.

    A geometria deve estar em um sistema compatível
    com o CRS do GeoDataFrame.
    """
    if gdf.empty:
        return gdf.copy()

    if geometria is None:
        return gdf.copy()

    consulta = gpd.GeoDataFrame(geometry=[geometria], crs=gdf.crs)

    if consulta.crs != gdf.crs:
        consulta = consulta.to_crs(gdf.crs)

    resultado = gpd.sjoin(gdf, consulta, predicate="intersects", how="inner")

    colunas_remover = [coluna for coluna in resultado.columns if coluna.startswith("index_")]

    return resultado.drop(columns=colunas_remover, errors="ignore").reset_index(drop=True)


def filtrar_por_periodo(gdf: gpd.GeoDataFrame, data_inicio=None, data_fim=None,) -> gpd.GeoDataFrame:
    """
    Filtra os itens por intervalo temporal.
    """
    if "datetime" not in gdf.columns:
        raise ValueError("O GeoParquet não possui a coluna 'datetime'.")

    resultado = gdf.copy()

    resultado["datetime"] = pd.to_datetime(resultado["datetime"], utc=True)

    if data_inicio is not None:
        inicio = pd.to_datetime(data_inicio, utc=True)

        resultado = resultado[resultado["datetime"] >= inicio]

    if data_fim is not None:
        fim = pd.to_datetime(data_fim, utc=True)

        resultado = resultado[resultado["datetime"] <= fim]

    return resultado.sort_values("datetime").reset_index(drop=True)


def consultar_geoparquet(gdf: gpd.GeoDataFrame, geometria=None, data_inicio=None, data_fim=None,) -> gpd.GeoDataFrame:
    """
    Executa uma consulta espacial e/ou temporal
    sobre o índice GeoParquet.
    """
    resultado = gdf

    if geometria is not None:
        resultado = filtrar_por_geometria(resultado, geometria)

    if data_inicio is not None or data_fim is not None:
        resultado = filtrar_por_periodo(resultado, data_inicio=data_inicio, data_fim=data_fim)

    return resultado.reset_index(drop=True)
