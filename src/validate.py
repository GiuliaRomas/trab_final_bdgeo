"""
Validação dos itens e assets Sentinel-2 antes da virtualização.

Responsabilidades deste módulo:
    - Verificar se os assets esperados existem.
    - Verificar se os assets possuem HREF.
    - Verificar consistência temporal.
    - Verificar consistência espacial.
    - Verificar propriedades dos arquivos raster.
    - Produzir um relatório de validação.
"""

from pathlib import Path
from typing import Iterable, Optional

import geopandas as gpd
import pandas as pd
import rasterio

from config import (BANDAS_PADRAO, VARIAVEIS_PRIORITARIAS_POR_COLECAO,)


def validar_assets(gdf: gpd.GeoDataFrame, variaveis: Optional[Iterable[str]] = None,) -> pd.DataFrame:
    """
    Verifica se os assets desejados existem no GeoParquet.
    """
    if variaveis is None:
        variaveis = BANDAS_PADRAO

    variaveis = list(variaveis)

    registros = []

    for _, row in gdf.iterrows():
        for variavel in variaveis:
            coluna = f"{variavel}_href"

            if coluna not in gdf.columns:
                registros.append({"item_id": row["item_id"], "asset": variavel, "status": "coluna_ausente", "href": None})
                continue

            href = row[coluna]

            if pd.isna(href) or not href:
                status = "asset_ausente"
                href = None
            else:
                status = "ok"

            registros.append({"item_id": row["item_id"], "asset": variavel, "status": status, "href": href})

    return pd.DataFrame(registros)


def validar_hrefs(gdf: gpd.GeoDataFrame, variaveis: Optional[Iterable[str]] = None,) -> pd.DataFrame:
    """
    Verifica se os HREFs dos assets possuem formato válido.
    """
    if variaveis is None:
        variaveis = BANDAS_PADRAO

    registros = []

    for _, row in gdf.iterrows():
        for variavel in variaveis:
            coluna = f"{variavel}_href"

            href = row.get(coluna)

            if pd.isna(href) or not href:
                status = "ausente"
            elif str(href).startswith(("http://", "https://", "s3://")):
                status = "valido"
            else:
                status = "formato_desconhecido"

            registros.append({"item_id": row["item_id"], "asset": variavel, "href": href, "status": status})

    return pd.DataFrame(registros)


def inspecionar_raster(href: str,) -> dict:
    """
    Abre um raster remoto e extrai suas propriedades.
    """
    with rasterio.open(href) as src:
        return {
            "driver": src.driver,
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtype": src.dtypes[0],
            "crs": str(src.crs),
            "transform": src.transform,
            "resolution_x": src.res[0],
            "resolution_y": src.res[1],
            "block_shapes": src.block_shapes,
            "compress": src.compression.value if src.compression is not None else None,
        }


def inspecionar_asset(gdf: gpd.GeoDataFrame, item_id: str, asset: str,) -> dict:
    """
    Inspeciona um asset específico de um item.
    """
    registros = gdf[gdf["item_id"] == item_id]

    if registros.empty:
        raise ValueError(f"Item não encontrado: {item_id}")

    coluna = f"{asset}_href"

    if coluna not in gdf.columns:
        raise ValueError(f"Asset '{asset}' não encontrado no GeoParquet.")

    href = registros.iloc[0][coluna]

    if pd.isna(href) or not href:
        raise ValueError(f"Asset '{asset}' não possui HREF para o item '{item_id}'.")

    metadados = inspecionar_raster(href)

    metadados["item_id"] = item_id
    metadados["asset"] = asset
    metadados["href"] = href

    return metadados


def verificar_consistencia(gdf: gpd.GeoDataFrame, asset: str = BANDAS_PADRAO[0],) -> pd.DataFrame:
    """
    Verifica a consistência espacial e estrutural de um asset
    entre diferentes cenas.
    """
    registros = []

    coluna = f"{asset}_href"

    if coluna not in gdf.columns:
        raise ValueError(f"Asset '{asset}' não encontrado.")

    for _, row in gdf.iterrows():
        href = row[coluna]

        if pd.isna(href) or not href:
            continue

        try:
            metadados = inspecionar_raster(href)

            metadados["item_id"] = row["item_id"]
            metadados["datetime"] = row["datetime"]
            metadados["asset"] = asset

            registros.append(metadados)

        except Exception as exc:
            registros.append({"item_id": row["item_id"], "datetime": row["datetime"], "asset": asset, "erro": str(exc)})

    return pd.DataFrame(registros)


def gerar_relatorio_consistencia(gdf: gpd.GeoDataFrame, asset: str = BANDAS_PADRAO[0],) -> dict:
    """
    Gera um resumo da consistência dos rasters.
    """
    df = verificar_consistencia(gdf, asset=asset)

    if df.empty:
        return {
            "asset": asset,
            "n_itens": 0,
            "consistente": False,
            "motivo": "Nenhum asset disponível.",
        }

    if "erro" in df.columns:
        erros = df["erro"].notna().sum()
    else:
        erros = 0

    campos = [
        "width",
        "height",
        "count",
        "dtype",
        "crs",
        "resolution_x",
        "resolution_y",
        "block_shapes",
        "compress",
    ]

    consistencia = True
    diferenças = {}

    for campo in campos:
        if campo not in df.columns:
            continue

        valores = df[campo].dropna().astype(str).unique()

        if len(valores) > 1:
            consistencia = False
            diferenças[campo] = valores.tolist()

    if erros > 0:
        consistencia = False

    return {
        "asset": asset,
        "n_itens": len(df),
        "n_erros": erros,
        "consistente": consistencia,
        "diferenças": diferenças,
    }
