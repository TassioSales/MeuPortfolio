from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import random
import string

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter()

def generate_sku(name: str, category: str) -> str:
    """Gera um SKU único baseado no nome e categoria do produto."""
    # Pega as 3 primeiras letras do nome (ou menos se o nome for menor)
    name_part = name[:3].upper()
    # Pega as 2 primeiras letras da categoria
    category_part = category[:2].upper()
    # Gera 4 números aleatórios
    number_part = ''.join(random.choices(string.digits, k=4))
    return f"{name_part}-{category_part}-{number_part}"

def generate_barcode() -> str:
    """Gera um código de barras EAN-13."""
    # Gera 12 dígitos aleatórios (o 13º será o dígito verificador)
    digits = [random.randint(0, 9) for _ in range(12)]
    
    # Calcula o dígito verificador
    sum_odd = sum(digits[::2])  # Soma dos dígitos em posições ímpares
    sum_even = sum(digits[1::2])  # Soma dos dígitos em posições pares
    total = sum_odd * 3 + sum_even
    check_digit = (10 - (total % 10)) % 10
    
    # Adiciona o dígito verificador ao final
    digits.append(check_digit)
    
    return ''.join(map(str, digits))

@router.get("/products", response_model=List[schemas.Product])
def read_products(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    category: schemas.ProductCategory = None,
    db: Session = Depends(get_db)
):
    products = crud.get_products(db, skip=skip, limit=limit, search=search, category=category)
    return products

@router.get("/products/dashboard", response_model=schemas.DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    """Obtém estatísticas para o dashboard"""
    try:
        return crud.get_dashboard_stats(db)
    except Exception as e:
        print(f"Erro na rota do dashboard: {str(e)}")
        return schemas.DashboardStats()

@router.get("/products/alerts", response_model=List[schemas.StockAlert])
def get_alerts(db: Session = Depends(get_db)):
    """Obtém alertas de estoque baixo ou zerado"""
    return crud.get_stock_alerts(db)

@router.post("/products", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    # Gera SKU e código de barras únicos
    sku = generate_sku(product.name, product.category.value)
    while crud.get_product_by_sku(db, sku):
        sku = generate_sku(product.name, product.category.value)
    
    barcode = generate_barcode()
    while crud.get_product_by_barcode(db, barcode):
        barcode = generate_barcode()
    
    # Cria o produto com os códigos gerados
    product_data = product.model_dump()
    db_product = models.Product(
        **product_data,
        sku=sku,
        barcode=barcode,
        created_at=datetime.utcnow()
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return db_product

@router.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    product_data = product.model_dump()
    for key, value in product_data.items():
        setattr(db_product, key, value)
    
    db_product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    db.delete(db_product)
    db.commit()
    return {"message": "Produto deletado com sucesso"}

@router.post("/products/{product_id}/stock", response_model=schemas.StockUpdateResponse)
async def update_stock(
    product_id: int,
    stock_update: schemas.StockUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza o estoque de um produto
    
    Args:
        product_id: ID do produto
        stock_update: Dados da atualização (quantidade e motivo)
        db: Sessão do banco de dados
        
    Returns:
        StockUpdateResponse: Produto atualizado e registro do histórico
        
    Raises:
        HTTPException: Se houver erro na atualização
    """
    try:
        # Atualiza o estoque e obtém o produto e histórico atualizados
        db_product, stock_history = crud.update_product_stock(
            db=db,
            product_id=product_id,
            quantity_changed=stock_update.quantity,
            reason=stock_update.reason
        )
        
        # Retorna a resposta
        return schemas.StockUpdateResponse(
            product=db_product,
            history=stock_history
        )
        
    except HTTPException as he:
        # Propaga exceções HTTP
        raise he
    except Exception as e:
        # Log do erro para debug
        print(f"Erro ao atualizar estoque: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao atualizar estoque"
        )
