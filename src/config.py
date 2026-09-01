from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

STAC_URL = "https://data.inpe.br/bdc/stac/v1/"

COLECOES_RECOMENDADAS = {
    "S2-16D-2": "Sentinel-2/MSI — composto de 16 dias",
}


VARIAVEIS_PRIORITARIAS_POR_COLECAO = {
    "S2-16D-2": (
        "B01",
        "B02",
        "B03",
        "B04",
        "B05",
        "B06",
        "B07",
        "B08",
        "B8A",
        "B09",
        "B11",
        "B12",
        "EVI",
        "NBR",
        "NDVI",
        "SCL",
        "CLEAROB",
    ),
}


COLECAO_PADRAO = "S2-16D-2"

DATA_DIR = ROOT / "data"

INDEX_DIR = DATA_DIR / "geoparquet"
MANIFEST_DIR = DATA_DIR / "manifests"

INDEX_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


GEOPARQUET_PATH = INDEX_DIR
ICECHUNK_PATH = DATA_DIR / "icechunk"

ICECHUNK_PATH.mkdir(parents=True, exist_ok=True)

CRS_CONSULTA = "EPSG:4326"
DIMENSAO_TEMPORAL = "time"
BANDAS_PADRAO = ("B02", "B03", "B04", "B08",)
RAIO_CONSULTA = None
RESOLUCAO_RASTER = 10

CHUNK_X = 512
CHUNK_Y = 512
