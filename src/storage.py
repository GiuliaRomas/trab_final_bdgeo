"""
Persistência de cubos virtuais usando Icechunk.

Fluxo:

    COG remoto
        ↓
    VirtualTIFF
        ↓
    ManifestArray
        ↓
    Xarray Dataset
        ↓
    Icechunk
        ↓
    consultas sob demanda

Os pixels dos COGs não são copiados para o Icechunk.
O Icechunk armazena a estrutura do dataset e as referências
aos objetos remotos.
"""

from pathlib import Path

import icechunk


BDC_DATA_URL = "https://data.inpe.br/bdc/data/"


def criar_configuracao_icechunk():
    """
    Cria a configuração do Icechunk e registra o container
    virtual correspondente aos dados do BDC.
    """

    http_store = icechunk.http_store()

    container = icechunk.virtual.VirtualChunkContainer(url_prefix=BDC_DATA_URL, store=http_store, name="bdc-http")

    config = icechunk.RepositoryConfig.default()

    config.set_virtual_chunk_container(container)

    return config


def criar_repositorio(caminho: str | Path,):
    """
    Cria um novo repositório Icechunk configurado para
    acessar os COGs remotos do BDC.
    """
    caminho = Path(caminho)

    caminho.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("CRIANDO REPOSITÓRIO ICECHUNK")
    print("=" * 60)

    print()
    print(f"Repositório: {caminho}")

    print()
    print(f"Container virtual: {BDC_DATA_URL}")

    storage = icechunk.local_filesystem_storage(str(caminho))

    config = criar_configuracao_icechunk()

    repo = icechunk.Repository.create(storage=storage, config=config, authorize_virtual_chunk_access={BDC_DATA_URL: icechunk.Credentials.HttpAccess()})

    print()
    print("[Sucesso] Repositório criado.")

    return repo


def salvar_dataset_virtual(ds, repo, mensagem: str = "Cubo Sentinel-2 virtual",):
    """
    Persiste um Dataset VirtualiZarr em Icechunk.
    """
    print()
    print("=" * 60)
    print("GRAVANDO CUBO VIRTUAL NO ICECHUNK")
    print("=" * 60)

    print()
    print(f"Variáveis: {list(ds.data_vars)}")

    print(f"Dimensões: {dict(ds.sizes)}")

    print(f"Referências virtuais: {ds.vz.nrefs()}")

    print(f"Tamanho lógico: {ds.vz.nbytes:,} bytes")

    session = repo.writable_session("main")

    print()
    print("Escrevendo referências virtuais...")

    ds.vz.to_icechunk(session.store, mode="w")

    print("[Sucesso] Referências gravadas.")

    print()
    print("Realizando commit...")

    commit_id = session.commit(mensagem)

    print()
    print(f"[Sucesso] Commit: {commit_id}")

    return commit_id


def abrir_repositorio(caminho: str | Path,):
    """
    Abre um repositório Icechunk existente.
    """

    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(f"Repositório não encontrado: {caminho}")

    storage = icechunk.local_filesystem_storage(str(caminho))

    repo = icechunk.Repository.open(storage=storage, authorize_virtual_chunk_access={BDC_DATA_URL: icechunk.Credentials.HttpAccess()})
    print()
    print(f"[Sucesso] Repositório aberto: {caminho}")

    return repo
