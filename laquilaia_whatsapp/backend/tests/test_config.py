"""Testes do carregamento de configuração."""

def test_env_com_variaveis_de_outros_servicos_nao_derruba_o_boot(tmp_path, monkeypatch):
    """
    O `.env` é compartilhado com o compose e com o frontend.

    Ele traz DB_USER, DB_PORT, NEXT_PUBLIC_API_URL e outras que não são deste
    Settings. O padrão do pydantic-settings v2 é recusar o desconhecido, e o
    backend morria no boot com dez erros de `extra_forbidden` — mas só quando
    o processo enxergava o arquivo, o que depende do diretório de onde se sobe
    o uvicorn. Daí ter passado despercebido.
    """
    env = tmp_path / ".env"
    env.write_text(
        "SECRET_KEY=abc\n"
        "DB_USER=laquilaia\n"
        "DB_PORT=5432\n"
        "NEXT_PUBLIC_API_URL=http://localhost:8000\n"
        "ALLOWED_ORIGINS=http://localhost:3000\n"
        "ENVIRONMENT=development\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    from app.config import Settings

    s = Settings()
    assert s.secret_key == "abc"
    assert not hasattr(s, "db_user")
