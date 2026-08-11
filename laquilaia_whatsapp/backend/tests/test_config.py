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


def test_origens_permitidas_sao_origens_de_verdade():
    """
    `localhost` e `127.0.0.1` soltos não são origens.

    O middleware trazia essas duas na lista fixa, e elas nunca casavam: o
    navegador manda sempre `esquema://host:porta`. Na prática só o
    `frontend_url` valia, e abrir o painel por 127.0.0.1 dava CORS no login.
    A variável `ALLOWED_ORIGINS`, documentada no `.env.example`, não era lida
    por ninguém.
    """
    from app.config import Settings

    s = Settings(
        allowed_origins="http://localhost:3000,http://127.0.0.1:3000",
        frontend_url="http://localhost:3000",
    )

    assert s.origens_permitidas == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert all("://" in origem for origem in s.origens_permitidas)


def test_frontend_url_entra_mesmo_fora_da_lista():
    """Quem muda só o FRONTEND_URL não pode perder o próprio painel."""
    from app.config import Settings

    s = Settings(
        allowed_origins="http://localhost:3000",
        frontend_url="https://painel.exemplo.com",
    )

    assert "https://painel.exemplo.com" in s.origens_permitidas
