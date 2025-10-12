"""
Operações de Banco de Dados para PriceTrack AI
CRUD completo com SQLAlchemy e logging robusto
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from core.models import Product, Alert, ProductCreate, ProductUpdate, AlertCreate, AppSetting
from core.logger import get_logger, log_database_operation
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = get_logger(__name__)


class DatabaseManager:
    """Gerenciador de operações de banco de dados"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== OPERAÇÕES DE PRODUTO ==========
    
    def create_product(self, product_data: ProductCreate) -> Product:
        """Cria um novo produto"""
        try:
            db_product = Product(
                product_name=product_data.product_name,
                tags=product_data.tags,
                alert_threshold=product_data.alert_threshold,
                user_rating=product_data.user_rating,
                price_history=[]
            )
            
            self.db.add(db_product)
            self.db.commit()
            self.db.refresh(db_product)
            
            logger.info(f"Produto criado com sucesso: ID {db_product.id}, Nome: {db_product.product_name}")
            log_database_operation(logger, "INSERT", "products", True, db_product.id)
            return db_product
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar produto '{product_data.product_name}': {str(e)}")
            log_database_operation(logger, "INSERT", "products", False)
            raise
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """Busca produto por ID"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if product:
                logger.info(f"Produto encontrado: ID {product_id}")
            else:
                logger.warning(f"Produto não encontrado: ID {product_id}")
            return product
        except Exception as e:
            logger.error(f"Erro ao buscar produto ID {product_id}: {str(e)}")
            raise
    
    def get_product_by_name(self, product_name: str) -> Optional[Product]:
        """Busca produto por nome"""
        try:
            product = self.db.query(Product).filter(Product.product_name == product_name).first()
            if product:
                logger.info(f"Produto encontrado por nome: {product_name}")
            else:
                logger.warning(f"Produto não encontrado por nome: {product_name}")
            return product
        except Exception as e:
            logger.error(f"Erro ao buscar produto por nome '{product_name}': {str(e)}")
            raise
    
    def get_all_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Lista todos os produtos com paginação"""
        try:
            products = self.db.query(Product).offset(offset).limit(limit).all()
            logger.info(f"Listados {len(products)} produtos (offset: {offset}, limit: {limit})")
            return products
        except Exception as e:
            logger.error(f"Erro ao listar produtos: {str(e)}")
            raise
    
    def search_products(self, query: str) -> List[Product]:
        """Busca produtos por nome ou tags"""
        try:
            products = self.db.query(Product).filter(
                or_(
                    Product.product_name.ilike(f"%{query}%"),
                    Product.tags.ilike(f"%{query}%")
                )
            ).all()
            
            logger.info(f"Busca por '{query}' retornou {len(products)} produtos")
            return products
        except Exception as e:
            logger.error(f"Erro na busca por '{query}': {str(e)}")
            raise
    
    def get_products_by_tags(self, tags_filter: List[str]) -> List[Product]:
        """Busca produtos por tags específicas"""
        try:
            if not tags_filter:
                return []
            
            # Construir filtros OR para cada tag
            filters = []
            for tag in tags_filter:
                filters.append(Product.tags.ilike(f"%{tag.strip()}%"))
            
            products = self.db.query(Product).filter(or_(*filters)).all()
            logger.info(f"Busca por tags {tags_filter} retornou {len(products)} produtos")
            return products
        except Exception as e:
            logger.error(f"Erro na busca por tags {tags_filter}: {str(e)}")
            raise
    
    def update_product(self, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """Atualiza produto existente"""
        try:
            product = self.get_product(product_id)
            if not product:
                return None
            
            # Atualizar apenas campos fornecidos
            if product_data.product_name is not None:
                product.product_name = product_data.product_name
            if product_data.tags is not None:
                product.tags = product_data.tags
            if product_data.alert_threshold is not None:
                product.alert_threshold = product_data.alert_threshold
            if product_data.user_rating is not None:
                product.user_rating = product_data.user_rating
            
            product.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(product)
            
            logger.info(f"Produto atualizado: ID {product_id}")
            return product
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar produto ID {product_id}: {str(e)}")
            raise
    
    def delete_product(self, product_id: int) -> bool:
        """Remove produto"""
        try:
            product = self.get_product(product_id)
            if not product:
                return False
            
            self.db.delete(product)
            self.db.commit()
            
            logger.info(f"Produto removido: ID {product_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover produto ID {product_id}: {str(e)}")
            raise
    
    # ========== OPERAÇÕES DE HISTÓRICO DE PREÇOS ==========
    
    def update_price_history(self, product_id: int, new_price: float) -> bool:
        """Atualiza histórico de preços do produto"""
        try:
            product = self.get_product(product_id)
            if not product:
                return False
            
            # Obter histórico atual
            price_history = product.price_history or []
            
            # Adicionar nova entrada
            today = datetime.now().strftime('%Y-%m-%d')
            new_entry = {
                "date": today,
                "price": float(new_price)
            }
            
            # Verificar se já existe entrada para hoje
            existing_entry = None
            for entry in price_history:
                if entry.get("date") == today:
                    existing_entry = entry
                    break
            
            if existing_entry:
                # Atualizar entrada existente
                existing_entry["price"] = float(new_price)
                logger.info(f"Preço atualizado para hoje: R$ {new_price}")
            else:
                # Adicionar nova entrada
                price_history.append(new_entry)
                logger.info(f"Novo preço adicionado: R$ {new_price}")
            
            # Limpar histórico antigo (manter apenas últimos 30 dias)
            cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            price_history = [
                entry for entry in price_history 
                if entry.get("date", "") >= cutoff_date
            ]
            
            # Ordenar por data
            price_history.sort(key=lambda x: x.get("date", ""))
            
            # Atualizar produto
            product.price_history = price_history
            product.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(product)
            
            logger.info(f"Histórico de preços atualizado para produto ID {product_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar histórico de preços produto ID {product_id}: {str(e)}")
            raise
    
    def get_price_trend(self, product_id: int, days: int = 7) -> Dict[str, Any]:
        """Calcula tendência de preços dos últimos dias"""
        try:
            product = self.get_product(product_id)
            if not product or not product.price_history:
                return {"trend": 0, "percentage": 0, "days_analyzed": 0}
            
            # Filtrar últimos N dias
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            recent_prices = [
                entry for entry in product.price_history 
                if entry.get("date", "") >= cutoff_date
            ]
            
            if len(recent_prices) < 2:
                return {"trend": 0, "percentage": 0, "days_analyzed": len(recent_prices)}
            
            # Calcular tendência
            first_price = recent_prices[0]["price"]
            last_price = recent_prices[-1]["price"]
            
            trend = last_price - first_price
            percentage = (trend / first_price) * 100 if first_price > 0 else 0
            
            result = {
                "trend": trend,
                "percentage": percentage,
                "days_analyzed": len(recent_prices),
                "first_price": first_price,
                "last_price": last_price
            }
            
            logger.info(f"Tendência calculada para produto ID {product_id}: {percentage:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao calcular tendência produto ID {product_id}: {str(e)}")
            return {"trend": 0, "percentage": 0, "days_analyzed": 0}
    
    # ========== OPERAÇÕES DE ALERTAS ==========
    
    def create_alert(self, alert_data: AlertCreate) -> Alert:
        """Cria novo alerta"""
        try:
            # Verificar se produto existe
            product = self.get_product(alert_data.product_id)
            if not product:
                raise ValueError(f"Produto ID {alert_data.product_id} não encontrado")
            
            # Verificar se já existe alerta ativo para este produto
            existing_alert = self.db.query(Alert).filter(
                and_(
                    Alert.product_id == alert_data.product_id,
                    Alert.is_active == 1
                )
            ).first()
            
            if existing_alert:
                # Atualizar alerta existente
                existing_alert.threshold_price = alert_data.threshold_price
                self.db.commit()
                self.db.refresh(existing_alert)
                
                logger.info(f"Alerta atualizado para produto ID {alert_data.product_id}")
                return existing_alert
            else:
                # Criar novo alerta
                db_alert = Alert(
                    product_id=alert_data.product_id,
                    threshold_price=alert_data.threshold_price,
                    is_active=1
                )
                
                self.db.add(db_alert)
                self.db.commit()
                self.db.refresh(db_alert)
                
                logger.info(f"Alerta criado: ID {db_alert.id} para produto ID {alert_data.product_id}")
                return db_alert
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar alerta para produto ID {alert_data.product_id}: {str(e)}")
            raise
    
    def get_active_alerts(self) -> List[Alert]:
        """Lista alertas ativos"""
        try:
            alerts = self.db.query(Alert).filter(Alert.is_active == 1).all()
            logger.info(f"Encontrados {len(alerts)} alertas ativos")
            return alerts
        except Exception as e:
            logger.error(f"Erro ao buscar alertas ativos: {str(e)}")
            raise
    
    def deactivate_alert(self, alert_id: int) -> bool:
        """Desativa alerta"""
        try:
            alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            alert.is_active = 0
            self.db.commit()
            
            logger.info(f"Alerta desativado: ID {alert_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao desativar alerta ID {alert_id}: {str(e)}")
            raise
    
    def check_price_alerts(self) -> List[Dict[str, Any]]:
        """Verifica alertas de preço que devem ser disparados"""
        try:
            triggered_alerts = []
            active_alerts = self.get_active_alerts()
            
            for alert in active_alerts:
                product = self.get_product(alert.product_id)
                if not product or not product.price_history:
                    continue
                
                # Obter preço mais recente
                latest_price_entry = max(
                    product.price_history, 
                    key=lambda x: x.get("date", "")
                )
                current_price = latest_price_entry["price"]
                
                # Verificar se preço está abaixo do threshold
                if current_price <= alert.threshold_price:
                    triggered_alerts.append({
                        "alert_id": alert.id,
                        "product_id": product.id,
                        "product_name": product.product_name,
                        "current_price": current_price,
                        "threshold_price": alert.threshold_price,
                        "savings": alert.threshold_price - current_price
                    })
                    
                    # Marcar alerta como disparado
                    alert.triggered_at = datetime.utcnow()
            
            if triggered_alerts:
                self.db.commit()
                logger.info(f"{len(triggered_alerts)} alertas disparados")
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Erro ao verificar alertas: {str(e)}")
            raise
    
    # ========== ESTATÍSTICAS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais do sistema"""
        try:
            total_products = self.db.query(Product).count()
            active_alerts = self.db.query(Alert).filter(Alert.is_active == 1).count()
            
            # Produtos com histórico de preços
            products_with_history = self.db.query(Product).filter(
                Product.price_history.isnot(None)
            ).count()
            
            # Produtos com tags
            products_with_tags = self.db.query(Product).filter(
                Product.tags.isnot(None),
                Product.tags != ""
            ).count()
            
            stats = {
                "total_products": total_products,
                "active_alerts": active_alerts,
                "products_with_history": products_with_history,
                "products_with_tags": products_with_tags,
                "coverage_percentage": (products_with_history / total_products * 100) if total_products > 0 else 0
            }
            
            logger.info(f"Estatísticas calculadas: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
            return {
                "total_products": 0,
                "active_alerts": 0,
                "products_with_history": 0,
                "products_with_tags": 0,
                "coverage_percentage": 0
            }

    # ========== APP SETTINGS (key-value) ==========
    def get_setting(self, key: str) -> Optional[str]:
        """Obtém valor de configuração por chave."""
        try:
            setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            return setting.value if setting else None
        except Exception as e:
            logger.error(f"Erro ao obter setting '{key}': {str(e)}")
            raise

    def set_setting(self, key: str, value: Optional[str]) -> None:
        """Define ou atualiza uma configuração (salva None como vazio)."""
        try:
            setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            if setting:
                setting.value = value
            else:
                setting = AppSetting(key=key, value=value)
                self.db.add(setting)
            self.db.commit()
            logger.info(f"Setting salvo: {key}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao salvar setting '{key}': {str(e)}")
            raise

    def delete_setting(self, key: str) -> None:
        """Remove uma configuração pela chave."""
        try:
            setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            if setting:
                self.db.delete(setting)
                self.db.commit()
                logger.info(f"Setting removido: {key}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover setting '{key}': {str(e)}")
            raise


# Context manager para transações
class DatabaseTransaction:
    """Context manager para operações de banco de dados"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def __enter__(self):
        return DatabaseManager(self.db)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.db.rollback()
            logger.error(f"Transação revertida devido a erro: {exc_val}")
        else:
            self.db.commit()
            logger.info("Transação commitada com sucesso")
