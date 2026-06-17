"""Unit tests for DatabaseManager."""

import os
import pytest

from bot.database.manager import DatabaseManager


@pytest.fixture
def db(tmp_path) -> DatabaseManager:
    """Create a fresh DatabaseManager pointing at a temp file."""
    db_file = str(tmp_path / "test_bot.db")
    manager = DatabaseManager(db_path=db_file)
    manager.setup()
    return manager


# ---------------------------------------------------------------------------
# Gastos
# ---------------------------------------------------------------------------

def test_adicionar_gasto(db: DatabaseManager) -> None:
    """Adding an expense should return a valid integer ID."""
    novo_id = db.adicionar_gasto(user_id=1, descricao="Almoço", valor=25.50, categoria="alimentação")
    assert isinstance(novo_id, int)
    assert novo_id > 0


def test_listar_gastos_empty(db: DatabaseManager) -> None:
    """Listing expenses for a user with no data should return an empty list."""
    result = db.listar_gastos(user_id=999)
    assert result == []


def test_listar_gastos_com_dados(db: DatabaseManager) -> None:
    """After adding expenses they should all appear in the listing."""
    db.adicionar_gasto(1, "Almoço", 25.50, "alimentação")
    db.adicionar_gasto(1, "Uber", 18.00, "transporte")
    db.adicionar_gasto(1, "Netflix", 45.90, "assinatura")

    gastos = db.listar_gastos(user_id=1)
    assert len(gastos) == 3

    descricoes = {g["descricao"] for g in gastos}
    assert "Almoço" in descricoes
    assert "Uber" in descricoes
    assert "Netflix" in descricoes


def test_listar_gastos_isolado_por_usuario(db: DatabaseManager) -> None:
    """Expenses from one user should not appear for another user."""
    db.adicionar_gasto(1, "Almoço", 25.50)
    db.adicionar_gasto(2, "Jantar", 40.00)

    gastos_user1 = db.listar_gastos(user_id=1)
    assert len(gastos_user1) == 1
    assert gastos_user1[0]["descricao"] == "Almoço"


def test_listar_gastos_com_filtro_mes(db: DatabaseManager) -> None:
    """Month filter should only return expenses for that month."""
    import sqlite3

    # Insert a gasto with a fixed date in the past
    conn = sqlite3.connect(db.db_path)
    conn.execute(
        "INSERT INTO gastos (user_id, descricao, valor, categoria, data) VALUES (1, 'Antigo', 100.0, 'outros', '2020-06-15')"
    )
    conn.commit()
    conn.close()

    # Add a current expense via the normal method (will use today's date)
    db.adicionar_gasto(1, "Atual", 50.0)

    gastos_2020 = db.listar_gastos(user_id=1, mes="2020-06")
    assert len(gastos_2020) == 1
    assert gastos_2020[0]["descricao"] == "Antigo"


def test_total_gastos(db: DatabaseManager) -> None:
    """Total should sum all expenses for the user."""
    db.adicionar_gasto(1, "Item A", 10.00)
    db.adicionar_gasto(1, "Item B", 20.50)
    db.adicionar_gasto(1, "Item C", 5.75)

    total = db.total_gastos(user_id=1)
    assert abs(total - 36.25) < 0.001


def test_total_gastos_sem_dados(db: DatabaseManager) -> None:
    """Total for a user with no expenses should be 0.0."""
    total = db.total_gastos(user_id=999)
    assert total == 0.0


# ---------------------------------------------------------------------------
# Notas
# ---------------------------------------------------------------------------

def test_adicionar_nota(db: DatabaseManager) -> None:
    """Adding a note should return a valid integer ID."""
    novo_id = db.adicionar_nota(user_id=1, texto="Comprar leite amanhã")
    assert isinstance(novo_id, int)
    assert novo_id > 0


def test_listar_notas_empty(db: DatabaseManager) -> None:
    """Listing notes for a user with none should return an empty list."""
    result = db.listar_notas(user_id=999)
    assert result == []


def test_listar_notas(db: DatabaseManager) -> None:
    """Added notes should all appear in the listing with correct text."""
    db.adicionar_nota(1, "Nota um")
    db.adicionar_nota(1, "Nota dois")
    db.adicionar_nota(1, "Nota três")

    notas = db.listar_notas(user_id=1)
    assert len(notas) == 3

    textos = {n["texto"] for n in notas}
    assert "Nota um" in textos
    assert "Nota dois" in textos
    assert "Nota três" in textos


def test_apagar_nota(db: DatabaseManager) -> None:
    """Deleting a note by ID should remove it and return True."""
    novo_id = db.adicionar_nota(1, "Para apagar")
    resultado = db.apagar_nota(user_id=1, nota_id=novo_id)
    assert resultado is True

    notas = db.listar_notas(user_id=1)
    assert all(n["id"] != novo_id for n in notas)


def test_apagar_nota_inexistente(db: DatabaseManager) -> None:
    """Attempting to delete a non-existent note should return False."""
    resultado = db.apagar_nota(user_id=1, nota_id=9999)
    assert resultado is False


def test_apagar_nota_outro_usuario(db: DatabaseManager) -> None:
    """A user should not be able to delete another user's note."""
    novo_id = db.adicionar_nota(user_id=1, texto="Nota do user 1")
    resultado = db.apagar_nota(user_id=2, nota_id=novo_id)
    assert resultado is False

    # Note should still exist for user 1
    notas = db.listar_notas(user_id=1)
    assert any(n["id"] == novo_id for n in notas)
