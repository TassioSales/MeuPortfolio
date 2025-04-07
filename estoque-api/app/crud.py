from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from . import models, schemas
from .models import ProductCategory
from fastapi import HTTPException

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_product_by_sku(db: Session, sku: str):
    return db.query(models.Product).filter(models.Product.sku == sku).first()

def get_product_by_barcode(db: Session, barcode: str):
    return db.query(models.Product).filter(models.Product.barcode == barcode).first()

def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[ProductCategory] = None
):
    query = db.query(models.Product)
    
    if search:
        search = f"%{search}%"
        query = query.filter(
            models.Product.name.ilike(search) |
            models.Product.sku.ilike(search) |
            models.Product.barcode.ilike(search)
        )
    
    if category:
        query = query.filter(models.Product.category == category)
    
    return query.offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product.model_dump().items():
            setattr(db_product, key, value)
        db_product.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product

def add_stock_history(
    db: Session,
    product_id: int,
    quantity_changed: int,
    previous_quantity: int,
    new_quantity: int,
    change_type: str,
    reason: str
) -> models.StockHistory:
    """
    Adiciona um novo registro no histórico de estoque
    
    Args:
        db: Sessão do banco de dados
        product_id: ID do produto
        quantity_changed: Quantidade alterada (positivo para entrada, negativo para saída)
        previous_quantity: Quantidade anterior
        new_quantity: Nova quantidade
        change_type: Tipo de alteração ('entrada' ou 'saída')
        reason: Motivo da alteração
        
    Returns:
        StockHistory: Registro do histórico criado
    """
    history = models.StockHistory(
        product_id=product_id,
        quantity_changed=quantity_changed,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        change_type=change_type,
        reason=reason,
        timestamp=datetime.utcnow()
    )
    
    db.add(history)
    db.commit()
    db.refresh(history)
    return history

def update_product_stock(
    db: Session,
    product_id: int,
    quantity_changed: int,
    reason: str
) -> tuple[models.Product, models.StockHistory]:
    """
    Atualiza o estoque de um produto e registra no histórico
    
    Args:
        db: Sessão do banco de dados
        product_id: ID do produto
        quantity_changed: Quantidade a ser alterada (positivo para entrada, negativo para saída)
        reason: Motivo da alteração
        
    Returns:
        tuple: (Produto atualizado, Registro do histórico)
        
    Raises:
        HTTPException: Se o produto não for encontrado ou se a quantidade resultar em estoque negativo
    """
    try:
        # Busca o produto com lock para atualização
        db_product = db.query(models.Product).with_for_update().filter(
            models.Product.id == product_id
        ).first()
        
        if not db_product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Calcula a nova quantidade
        new_quantity = db_product.quantity + quantity_changed
        if new_quantity < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantidade insuficiente em estoque. Atual: {db_product.quantity}"
            )
        
        # Cria o registro de histórico
        stock_history = models.StockHistory(
            product_id=product_id,
            quantity_changed=quantity_changed,
            previous_quantity=db_product.quantity,
            new_quantity=new_quantity,
            change_type="entrada" if quantity_changed > 0 else "saída",
            reason=reason,
            timestamp=datetime.utcnow()
        )
        
        # Atualiza o produto
        db_product.quantity = new_quantity
        db_product.updated_at = datetime.utcnow()
        
        # Adiciona o histórico
        db.add(stock_history)
        
        # Commit da transação
        try:
            db.commit()
            db.refresh(db_product)
            db.refresh(stock_history)
            return db_product, stock_history
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao salvar alterações: {str(e)}"
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar estoque: {str(e)}"
        )

def get_dashboard_stats(db: Session) -> schemas.DashboardStats:
    """Obtém estatísticas para o dashboard"""
    try:
        # Contagem total de produtos
        total_products = db.query(func.count(models.Product.id)).scalar() or 0

        # Valor total do estoque e preço médio
        total_value = db.query(func.sum(models.Product.price * models.Product.quantity)).scalar() or 0.0
        average_price = db.query(func.avg(models.Product.price)).scalar() or 0.0

        # Contagem de produtos com estoque baixo
        low_stock_count = db.query(func.count(models.Product.id))\
            .filter(models.Product.quantity > 0)\
            .filter(models.Product.quantity <= models.Product.minimum_stock)\
            .scalar() or 0

        # Contagem de produtos sem estoque
        out_of_stock_count = db.query(func.count(models.Product.id))\
            .filter(models.Product.quantity <= 0)\
            .scalar() or 0

        # Produtos por categoria
        products_by_category = {}
        for category in ProductCategory:
            count = db.query(func.count(models.Product.id))\
                .filter(models.Product.category == category)\
                .scalar() or 0
            products_by_category[category.value] = count

        # Movimentações recentes
        recent_movements = []
        movements = db.query(models.StockHistory)\
            .order_by(models.StockHistory.timestamp.desc())\
            .limit(5)\
            .all()

        for movement in movements:
            recent_movements.append({
                "id": movement.id,
                "product_id": movement.product_id,
                "quantity_changed": movement.quantity_changed,
                "change_type": movement.change_type,
                "reason": movement.reason,
                "timestamp": movement.timestamp.isoformat()
            })

        return schemas.DashboardStats(
            total_products=total_products,
            total_value=float(total_value),
            average_price=float(average_price),
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            products_by_category=products_by_category,
            recent_movements=recent_movements
        )
    except Exception as e:
        print(f"Erro ao obter estatísticas do dashboard: {str(e)}")
        return schemas.DashboardStats()

def get_stock_alerts(db: Session) -> List[schemas.StockAlert]:
    """Obtém alertas de estoque baixo ou zerado"""
    alerts = []
    products = db.query(models.Product)\
        .filter(
            (models.Product.quantity <= models.Product.minimum_stock)
        )\
        .all()
    
    for product in products:
        status = "OUT" if product.quantity <= 0 else "LOW"
        alerts.append(
            schemas.StockAlert(
                product_id=product.id,
                product_name=product.name,
                current_quantity=product.quantity,
                minimum_stock=product.minimum_stock,
                status=status
            )
        )
    
    return alerts
