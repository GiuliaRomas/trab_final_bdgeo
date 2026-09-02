"""
Funções para acesso ao catálogo STAC do INPE BDC.

Responsabilidades deste módulo
------------------------------
- Conectar ao catálogo STAC.
- Listar e acessar coleções.
- Consultar itens por área e período.
- Filtrar assets de interesse.
- Extrair informações básicas dos itens.

"""

from datetime import datetime
from typing import Iterable, Optional

from pystac_client import Client

from config import (STAC_URL, COLECAO_PADRAO, VARIAVEIS_PRIORITARIAS_POR_COLECAO,)

def conectar_stac() -> Client:
    """
    Conecta ao catálogo STAC do INPE BDC.
    """
    return Client.open(STAC_URL)


def listar_colecoes(catalogo: Client) -> list[str]:
    """
    Lista os IDs das coleções disponíveis no catálogo.
    """
    return [colecao.id for colecao in catalogo.get_collections()]


def obter_colecao(catalogo: Client, colecao: str = COLECAO_PADRAO,):
    """
    Obtém uma coleção específica.
    """
    return catalogo.get_collection(colecao)


def obter_variaveis_prioritarias(colecao: str = COLECAO_PADRAO,) -> tuple[str, ...]:
    """
    Retorna os assets prioritários configurados para uma coleção.
    """
    try:
        return VARIAVEIS_PRIORITARIAS_POR_COLECAO[colecao]
    except KeyError as exc:
        raise ValueError(f"Coleção '{colecao}' não possui variáveis prioritárias configuradas em config.py.") from exc


def filtrar_assets(item, variaveis: Optional[Iterable[str]] = None,) -> dict:
    """
    Retorna apenas os assets desejados de um item STAC.

    Se variaveis for None, utiliza os assets prioritários
    definidos no config.py para a coleção do item.
    """
    if variaveis is None:
        variaveis = obter_variaveis_prioritarias(item.collection_id)

    variaveis = set(variaveis)

    return {asset_id: asset for asset_id, asset in item.assets.items() if asset_id in variaveis}


def buscar_itens(
catalogo: Client,
    colecao: str = COLECAO_PADRAO,
    bbox: Optional[list[float]] = None,
    intersects: Optional[dict] = None,
    data_inicio: Optional[str | datetime] = None,
    data_fim: Optional[str | datetime] = None,
    max_itens: Optional[int] = None,
):
    """
    Consulta itens STAC por coleção, área e período.
    """
    datetime_interval = _montar_intervalo_datetime(data_inicio, data_fim)
    busca = catalogo.search(collections=[colecao], bbox=bbox, intersects=intersects, datetime=datetime_interval, max_items=max_itens)

    return list(busca.items())


def resumo_item(item) -> dict:
    """
    Extrai informações essenciais de um item STAC.
    """
    return {
        "id": item.id,
        "collection": item.collection_id,
        "datetime": item.datetime,
        "bbox": item.bbox,
        "geometry": item.geometry,
        "assets": list(item.assets.keys()),
    }


def resumo_assets(item) -> list[dict]:
    """
    Retorna informações básicas dos assets de um item.
    """
    return [
        {
            "id": asset_id,
            "href": asset.href,
            "media_type": asset.media_type,
            "title": asset.title,
            "roles": asset.roles,
        }
        for asset_id, asset in item.assets.items()
    ]


def _montar_intervalo_datetime(data_inicio: Optional[str | datetime], data_fim: Optional[str | datetime],) -> Optional[str]:
    """
    Monta o intervalo temporal utilizado pelo STAC API.
    """
    if data_inicio is None and data_fim is None:
        return None

    inicio = ".." if data_inicio is None else _formatar_data(data_inicio)
    fim = ".." if data_fim is None else _formatar_data(data_fim)

    return f"{inicio}/{fim}"


def _formatar_data(data: str | datetime) -> str:
    """
    Converte uma data para ISO 8601.
    """
    if isinstance(data, datetime):
        return data.isoformat()

    return data
