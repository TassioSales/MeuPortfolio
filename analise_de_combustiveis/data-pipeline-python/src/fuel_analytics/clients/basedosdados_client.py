from __future__ import annotations

import polars as pl

from fuel_analytics.logging import logger

# Microdados ANP via BasedosDados BigQuery
# Agrega no BigQuery — traz apenas médias semanais por estado/produto (~50K linhas)
# em vez de microdados brutos (~5M linhas). Custo de query idêntico, sem download pesado.
_AGGREGATED_QUERY = """
SELECT
    dados.sigla_uf                                        AS state,
    dados.produto                                         AS product,
    dados.bandeira_revenda                                AS brand,
    DATE_TRUNC(dados.data_coleta, WEEK)                   AS date,
    ROUND(AVG(dados.preco_venda), 4)                      AS price,
    ROUND(AVG(dados.preco_compra), 4)                     AS price_buy,
    ROUND(MIN(dados.preco_venda), 4)                      AS price_min,
    ROUND(MAX(dados.preco_venda), 4)                      AS price_max,
    ROUND(STDDEV(dados.preco_venda), 4)                   AS price_std,
    COUNT(*)                                              AS sample_count
FROM `basedosdados.br_anp_precos_combustiveis.microdados` AS dados
{where_clause}
  AND dados.preco_venda IS NOT NULL
  AND dados.preco_venda > 0
GROUP BY state, product, brand, date
ORDER BY date DESC, state, product
"""


def build_query(
    *,
    years: list[int] | None = None,
    states: list[str] | None = None,
    limit: int = 5_000_000,  # mantido por compatibilidade, não usado na query agregada
) -> str:
    filters: list[str] = []
    if years:
        yr_list = ", ".join(str(y) for y in years)
        filters.append(f"EXTRACT(YEAR FROM dados.data_coleta) IN ({yr_list})")
    if states:
        st_list = ", ".join(f"'{s}'" for s in states)
        filters.append(f"dados.sigla_uf IN ({st_list})")

    # A query já tem WHERE implícito (preco_venda IS NOT NULL), então sempre há filtro
    where_clause = "WHERE " + " AND ".join(filters) if filters else "WHERE TRUE"
    return _AGGREGATED_QUERY.format(where_clause=where_clause)


def _pandas_to_polars(df: "pd.DataFrame") -> pl.DataFrame:  # type: ignore[name-defined]
    return pl.from_pandas(df)


def fetch_with_basedosdados(billing_project_id: str, query: str) -> pl.DataFrame:
    """Query via a biblioteca basedosdados (bd.read_sql)."""
    try:
        import basedosdados as bd  # type: ignore[import]
        logger.info("Consultando BasedosDados (billing={})", billing_project_id)
        pandas_df = bd.read_sql(query=query, billing_project_id=billing_project_id)
        frame = _pandas_to_polars(pandas_df)
        logger.info("BasedosDados retornou {} linhas", frame.height)
        return frame
    except ImportError:
        logger.warning("basedosdados nao instalado; usando google-cloud-bigquery diretamente")
        return fetch_with_bigquery(billing_project_id, query)


def fetch_with_bigquery(billing_project_id: str, query: str) -> pl.DataFrame:
    """Query direto via google-cloud-bigquery (sem wrapper BasedosDados)."""
    from google.cloud import bigquery  # type: ignore[import]
    client = bigquery.Client(project=billing_project_id)
    logger.info("Consultando BigQuery diretamente (project={})", billing_project_id)
    result = client.query(query).to_dataframe()
    frame = _pandas_to_polars(result)
    logger.info("BigQuery retornou {} linhas", frame.height)
    return frame


def ingest_basedosdados(
    billing_project_id: str,
    *,
    years: list[int] | None = None,
    states: list[str] | None = None,
    limit: int = 5_000_000,
) -> pl.DataFrame:
    """
    Carrega microdados ANP via BasedosDados (BigQuery).

    Retorna DataFrame compativel com normalize_frame() — mesma estrutura
    de colunas dos CSVs ANP apos renomeacao.

    Colunas extras preservadas no resultado:
      neighborhood, zip_code, address, cnpj, establishment
      (uteis para analise por bandeira, bairro e posto individual)

    Requer uma das opcoes:
      pip install basedosdados           # usa bd.read_sql (recomendado)
      pip install google-cloud-bigquery  # acesso direto ao BigQuery

    Autenticacao GCP:
      gcloud auth application-default login
      # ou: GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
    """
    query = build_query(years=years, states=states, limit=limit)
    logger.info(
        "Iniciando ingest BasedosDados: anos={} estados={} limite={}",
        years, states, limit,
    )
    frame = fetch_with_basedosdados(billing_project_id, query)
    logger.info(
        "Ingest BasedosDados concluido: {} linhas, colunas: {}",
        frame.height,
        frame.columns,
    )
    return frame
