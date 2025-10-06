"""
Testes Unitários para PriceTrack AI
Foco em serviços de IA e validações
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from core.ai_services import GeminiService, AIServiceError
from core.models import ProductCreate, ProductUpdate, AlertCreate
from core.utils import validate_price, validate_product_name, ValidationError
from core.database import DatabaseManager
from core.logger import get_logger, setup_logging, log_user_action

# Configurar logging para testes
logger = get_logger(__name__)
setup_logging()


class TestGeminiService:
    """Testes para o serviço Gemini"""
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock de resposta do Gemini"""
        mock_response = Mock()
        mock_response.text = json.dumps([
            {
                "name": "iPhone 15 Pro Max",
                "price": 2999.90,
                "store": "Apple Store",
                "score": 0.95,
                "description": "Smartphone premium",
                "availability": "Em estoque"
            }
        ])
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 150
        return mock_response
    
    @pytest.fixture
    def gemini_service(self):
        """Instância do serviço Gemini para testes"""
        with patch('core.ai_services.genai.configure'):
            with patch('core.ai_services.genai.GenerativeModel'):
                service = GeminiService()
                return service
    
    def test_search_products_success(self, gemini_service, mock_gemini_response):
        """Testa busca de produtos com sucesso"""
        logger.info("Iniciando teste de busca de produtos com sucesso")
        log_user_action(logger, "test_execution", "Teste de busca de produtos")
        with patch.object(gemini_service, '_make_api_call', return_value=mock_gemini_response):
            result = gemini_service.search_products_with_gemini("iPhone 15")
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["name"] == "iPhone 15 Pro Max"
            assert result[0]["price"] == 2999.90
            assert result[0]["score"] == 0.95
            logger.info("Teste de busca de produtos concluído com sucesso")
    
    def test_search_products_json_error(self, gemini_service):
        """Testa busca de produtos com erro de JSON"""
        mock_response = Mock()
        mock_response.text = "Resposta inválida sem JSON"
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.search_products_with_gemini("iPhone 15")
            
            # Deve retornar fallback
            assert isinstance(result, list)
            assert len(result) == 1
            assert "iPhone 15" in result[0]["name"]
    
    def test_generate_tags_success(self, gemini_service):
        """Testa geração de tags com sucesso"""
        mock_response = Mock()
        mock_response.text = "smartphone, apple, ios, premium, 256gb"
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.generate_tags_for_product("iPhone 15")
            
            assert isinstance(result, str)
            assert "smartphone" in result
            assert "apple" in result
    
    def test_generate_summary_success(self, gemini_service):
        """Testa geração de resumo com sucesso"""
        mock_response = Mock()
        mock_response.text = "iPhone 15 é um smartphone premium da Apple..."
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.generate_product_summary("iPhone 15")
            
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_analyze_reviews_success(self, gemini_service):
        """Testa análise de reviews com sucesso"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "summary": "Produto bem avaliado",
            "pros": ["Qualidade", "Design"],
            "cons": ["Preço alto"],
            "score_sentimento": 0.7,
            "total_reviews": 150
        })
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.summarize_reviews("iPhone 15")
            
            assert isinstance(result, dict)
            assert "summary" in result
            assert "score_sentimento" in result
            assert result["score_sentimento"] == 0.7
    
    def test_analyze_offer_quality(self, gemini_service):
        """Testa análise de qualidade de oferta"""
        price_history = [
            {"date": "2024-01-01", "price": 3000.0},
            {"date": "2024-01-02", "price": 2900.0}
        ]
        current_price = 2800.0
        
        mock_response = Mock()
        mock_response.text = json.dumps({
            "nota": 8.5,
            "justificativa": "Boa oferta",
            "recomendacao": "COMPRAR_AGORA",
            "previsao": "Preço pode subir",
            "dias_para_mudanca": 5,
            "confianca": 0.8
        })
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.analyze_offer_quality(price_history, current_price)
            
            assert isinstance(result, dict)
            assert "nota" in result
            assert "recomendacao" in result
            assert result["nota"] == 8.5
    
    def test_compare_products_success(self, gemini_service):
        """Testa comparação de produtos com sucesso"""
        product_names = ["iPhone 15", "Samsung Galaxy S24"]
        user_focus = "melhor custo-benefício"
        
        mock_response = Mock()
        mock_response.text = "## Comparação Detalhada\n\n### Especificações..."
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.compare_products(product_names, user_focus)
            
            assert isinstance(result, str)
            assert "Comparação" in result
    
    def test_suggest_alert_threshold(self, gemini_service):
        """Testa sugestão de threshold de alerta"""
        mock_response = Mock()
        mock_response.text = "299.90"
        
        with patch.object(gemini_service, '_make_api_call', return_value=mock_response):
            result = gemini_service.suggest_alert_threshold("iPhone 15", 3000.0)
            
            assert isinstance(result, float)
            assert result == 299.90
    
    def test_api_call_retry_logic(self, gemini_service):
        """Testa lógica de retry em chamadas de API"""
        with patch.object(gemini_service, '_make_api_call', side_effect=AIServiceError("API Error")):
            with pytest.raises(AIServiceError):
                gemini_service.search_products_with_gemini("test")


class TestValidationUtils:
    """Testes para funções de validação"""
    
    def test_validate_price_valid(self):
        """Testa validação de preço válido"""
        assert validate_price("299.90") == 299.90
        assert validate_price(299.90) == 299.90
        assert validate_price("299,90") == 299.90
    
    def test_validate_price_invalid(self):
        """Testa validação de preço inválido"""
        with pytest.raises(ValidationError):
            validate_price("abc")
        
        with pytest.raises(ValidationError):
            validate_price(-100)
        
        with pytest.raises(ValidationError):
            validate_price(0)
    
    def test_validate_product_name_valid(self):
        """Testa validação de nome de produto válido"""
        assert validate_product_name("iPhone 15 Pro Max") == "iPhone 15 Pro Max"
        assert validate_product_name("  iPhone 15  ") == "iPhone 15"
    
    def test_validate_product_name_invalid(self):
        """Testa validação de nome de produto inválido"""
        with pytest.raises(ValidationError):
            validate_product_name("")
        
        with pytest.raises(ValidationError):
            validate_product_name("A")
        
        with pytest.raises(ValidationError):
            validate_product_name("x" * 300)


class TestPydanticModels:
    """Testes para modelos Pydantic"""
    
    def test_product_create_valid(self):
        """Testa criação de produto válido"""
        product_data = ProductCreate(
            product_name="iPhone 15",
            tags="smartphone, apple",
            alert_threshold=2500.0,
            user_rating=5
        )
        
        assert product_data.product_name == "iPhone 15"
        assert product_data.tags == "smartphone, apple"
        assert product_data.alert_threshold == 2500.0
        assert product_data.user_rating == 5
    
    def test_product_create_invalid_name(self):
        """Testa criação de produto com nome inválido"""
        with pytest.raises(ValueError):
            ProductCreate(product_name="")
    
    def test_product_create_invalid_rating(self):
        """Testa criação de produto com rating inválido"""
        with pytest.raises(ValueError):
            ProductCreate(
                product_name="iPhone 15",
                user_rating=6  # Rating deve ser 1-5
            )
    
    def test_alert_create_valid(self):
        """Testa criação de alerta válido"""
        alert_data = AlertCreate(
            product_id=1,
            threshold_price=2500.0
        )
        
        assert alert_data.product_id == 1
        assert alert_data.threshold_price == 2500.0
    
    def test_alert_create_invalid_threshold(self):
        """Testa criação de alerta com threshold inválido"""
        with pytest.raises(ValueError):
            AlertCreate(
                product_id=1,
                threshold_price=0  # Threshold deve ser > 0
            )


class TestDatabaseManager:
    """Testes para operações de banco de dados"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock da sessão do banco"""
        return Mock()
    
    @pytest.fixture
    def db_manager(self, mock_db_session):
        """Instância do DatabaseManager para testes"""
        return DatabaseManager(mock_db_session)
    
    def test_create_product_success(self, db_manager):
        """Testa criação de produto com sucesso"""
        product_data = ProductCreate(
            product_name="iPhone 15",
            tags="smartphone, apple"
        )
        
        # Mock do produto criado
        mock_product = Mock()
        mock_product.id = 1
        mock_product.product_name = "iPhone 15"
        
        # Mock das operações de banco
        db_manager.db.add = Mock()
        db_manager.db.commit = Mock()
        db_manager.db.refresh = Mock()
        
        with patch('core.database.Product', return_value=mock_product):
            result = db_manager.create_product(product_data)
            
            assert result.id == 1
            assert result.product_name == "iPhone 15"
            db_manager.db.add.assert_called_once()
            db_manager.db.commit.assert_called_once()
    
    def test_get_product_success(self, db_manager):
        """Testa busca de produto com sucesso"""
        mock_product = Mock()
        mock_product.id = 1
        mock_product.product_name = "iPhone 15"
        
        db_manager.db.query.return_value.filter.return_value.first.return_value = mock_product
        
        result = db_manager.get_product(1)
        
        assert result.id == 1
        assert result.product_name == "iPhone 15"
    
    def test_get_product_not_found(self, db_manager):
        """Testa busca de produto não encontrado"""
        db_manager.db.query.return_value.filter.return_value.first.return_value = None
        
        result = db_manager.get_product(999)
        
        assert result is None


class TestLogging:
    """Testes para sistema de logging"""
    
    def test_get_logger(self):
        """Testa obtenção de logger"""
        logger = get_logger("test_module")
        
        assert logger.name == "pricetrack_ai.test_module"
        assert logger.level >= 0
    
    @patch('core.logger.logging.getLogger')
    def test_log_api_call_success(self, mock_get_logger):
        """Testa log de chamada de API bem-sucedida"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        from core.logger import log_api_call
        
        log_api_call(mock_logger, "test_function", 150, True)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "test_function" in call_args
        assert "150" in call_args


# Fixtures globais para pytest
@pytest.fixture(scope="session")
def test_data():
    """Dados de teste para toda a sessão"""
    return {
        "sample_product": {
            "name": "iPhone 15 Pro Max",
            "price": 2999.90,
            "store": "Apple Store",
            "score": 0.95
        },
        "sample_tags": "smartphone, apple, ios, premium, 256gb",
        "sample_summary": "iPhone 15 Pro Max é um smartphone premium..."
    }


# Configuração do pytest
def pytest_configure(config):
    """Configuração do pytest"""
    config.addinivalue_line(
        "markers", "slow: marca testes que demoram para executar"
    )
    config.addinivalue_line(
        "markers", "integration: marca testes de integração"
    )


# Executar testes específicos
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
