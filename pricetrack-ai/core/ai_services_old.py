"""
Serviços de Inteligência Artificial para PriceTrack AI
Integração completa com Google Gemini 1.5 Pro
"""

import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from core.logger import get_logger, log_api_call
from typing import List, Dict, Any, Optional
import json
import time
import numpy as np
from datetime import datetime

logger = get_logger(__name__)


class AIServiceError(Exception):
    """Exceção customizada para erros de IA"""
    pass


class GeminiService:
    """Serviço principal para integração com Google Gemini"""
    
    def __init__(self):
        self.model = None
        self.chat_history = {}
        self._initialize_model()
    
    def _initialize_model(self):
        """Inicializa o modelo Gemini com configurações otimizadas"""
        try:
            # Configurar API key
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY não encontrada nos secrets, usando modo desenvolvimento")
                api_key = "dev-key-placeholder"
            
            genai.configure(api_key=api_key)
            
            # Configurações de geração otimizadas
            generation_config = {
                'temperature': 0.3,  # Baixa temperatura para factualidade
                'top_p': 0.8,        # Diversidade controlada
                'max_output_tokens': 1024,  # Controle de custo
                'top_k': 40
            }
            
            # Safety settings para bloquear conteúdo sensível
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Inicializar modelo
            self.model = genai.GenerativeModel(
                'gemini-1.5-pro',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info("Modelo Gemini 1.5 Pro inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo Gemini: {str(e)}")
            raise AIServiceError(f"Falha na inicialização do modelo: {str(e)}")
    
    def _make_api_call(self, prompt: str, stream: bool = False, use_chat: bool = False, chat_id: str = None) -> Any:
        """Faz chamada para API Gemini com retry logic"""
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                if use_chat and chat_id:
                    # Usar chat com histórico
                    if chat_id not in self.chat_history:
                        self.chat_history[chat_id] = self.model.start_chat(history=[])
                    
                    chat = self.chat_history[chat_id]
                    response = chat.send_message(prompt)
                else:
                    # Chamada direta
                    response = self.model.generate_content(prompt, stream=stream)
                
                # Log de sucesso
                tokens_used = getattr(response, 'usage_metadata', None)
                if tokens_used:
                    log_api_call(logger, "gemini_api_call", tokens_used.total_token_count, True)
                else:
                    log_api_call(logger, "gemini_api_call", success=True)
                
                return response
                
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou: {str(e)}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                else:
                    log_api_call(logger, "gemini_api_call", success=False)
                    raise AIServiceError(f"Falha após {max_retries} tentativas: {str(e)}")
    
    @st.cache_data(ttl=1800)  # Cache por 30 minutos
    def search_products_with_gemini(self, product_name: str) -> List[Dict[str, Any]]:
        """
        Simula busca de produtos em e-commerces usando IA
        Retorna ofertas estruturadas com scores de relevância
        """
        try:
            prompt = f"""
            Você é Artemis, uma consultora de e-commerce sênior, precisa, imparcial e focada em valor real para o consumidor brasileiro.
            
            Simule uma busca por "{product_name}" em principais e-commerces brasileiros (Mercado Livre, Amazon, Magazine Luiza, Casas Bahia, etc.).
            
            Retorne APENAS um JSON válido com até 5 ofertas encontradas no seguinte formato:
            [
                {{
                    "name": "Nome completo do produto",
                    "price": 299.90,
                    "store": "Nome da loja",
                    "score": 0.85,
                    "description": "Descrição breve do produto",
                    "availability": "Em estoque"
                }}
            ]
            
            Critérios para score de relevância (0-1):
            - 0.9-1.0: Produto exato, marca conhecida, preço competitivo
            - 0.7-0.8: Produto similar, boa qualidade, preço razoável  
            - 0.5-0.6: Produto relacionado, qualidade média
            - 0.3-0.4: Produto genérico ou com limitações
            - 0.0-0.2: Produto irrelevante ou de baixa qualidade
            
            Seja realista com preços brasileiros e disponibilidade.
            """
            
            response = self._make_api_call(prompt)
            result_text = response.text.strip()
            
            # Tentar extrair JSON da resposta
            try:
                # Remover markdown se presente
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                products = json.loads(result_text)
                
                # Validar estrutura
                if not isinstance(products, list):
                    raise ValueError("Resposta não é uma lista")
                
                logger.info(f"Busca por '{product_name}' retornou {len(products)} produtos")
                return products
                
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON da resposta: {str(e)}")
                # Fallback: retornar resultado estruturado manualmente
                return [{
                    "name": product_name,
                    "price": 199.90,
                    "store": "Loja Exemplo",
                    "score": 0.7,
                    "description": "Produto encontrado via IA",
                    "availability": "Em estoque"
                }]
                
        except Exception as e:
            logger.error(f"Erro na busca de produtos '{product_name}': {str(e)}")
            raise AIServiceError(f"Falha na busca de produtos: {str(e)}")
    
    @st.cache_data(ttl=3600)  # Cache por 1 hora
    def generate_tags_for_product(self, product_name: str) -> str:
        """
        Gera tags relevantes para o produto usando IA
        Retorna até 7 tags únicas separadas por vírgula
        """
        try:
            prompt = f"""
            Você é Artemis, uma especialista em categorização de produtos.
            
            Gere até 7 tags relevantes para o produto "{product_name}".
            
            Tags devem ser:
            - Curtas (1-2 palavras)
            - Em português
            - Específicas e úteis para filtros
            - Sem duplicatas
            
            Retorne APENAS as tags separadas por vírgula, sem numeração ou formatação adicional.
            
            Exemplo de resposta: eletrônicos, smartphone, android, 128gb, dual-sim
            """
            
            response = self._make_api_call(prompt)
            tags = response.text.strip()
            
            # Limpar e validar tags
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            tags_list = list(dict.fromkeys(tags_list))  # Remove duplicatas mantendo ordem
            tags_list = tags_list[:7]  # Limitar a 7 tags
            
            result = ', '.join(tags_list)
            logger.info(f"Tags geradas para '{product_name}': {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao gerar tags para '{product_name}': {str(e)}")
            return "produto, geral"
    
    @st.cache_data(ttl=1800)
    def generate_product_summary(self, product_name: str) -> str:
        """
        Gera resumo inteligente do produto
        Usa temperatura baixa para consistência
        """
        try:
            prompt = f"""
            Você é Artemis, uma consultora de e-commerce especializada em análise de produtos.
            
            Crie um resumo conciso e informativo sobre "{product_name}" incluindo:
            
            1. **Categoria e Tipo**: Que tipo de produto é
            2. **Principais Características**: 3-4 pontos principais
            3. **Público-Alvo**: Para quem é indicado
            4. **Considerações de Compra**: Pontos importantes na decisão
            
            Use linguagem clara e objetiva, focada em ajudar o consumidor a tomar decisões informadas.
            Máximo 200 palavras.
            """
            
            response = self._make_api_call(prompt)
            summary = response.text.strip()
            
            logger.info(f"Resumo gerado para '{product_name}'")
            return summary
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo para '{product_name}': {str(e)}")
            return f"Resumo não disponível para {product_name}."
    
    @st.cache_data(ttl=1800)
    def summarize_reviews(self, product_name: str) -> Dict[str, Any]:
        """
        Simula análise de reviews com score de sentimento
        Retorna resumo e score numérico (-1 a 1)
        """
        try:
            prompt = f"""
            Você é Artemis, especialista em análise de sentimento de reviews de produtos.
            
            Simule uma análise de reviews para "{product_name}" baseada em conhecimento geral do mercado.
            
            Retorne APENAS um JSON válido no formato:
            {{
                "summary": "Resumo das principais opiniões dos consumidores",
                "pros": ["Ponto positivo 1", "Ponto positivo 2", "Ponto positivo 3"],
                "cons": ["Ponto negativo 1", "Ponto negativo 2"],
                "score_sentimento": 0.7,
                "total_reviews": 150
            }}
            
            Score de sentimento (-1 a 1):
            - 0.7 a 1.0: Muito positivo
            - 0.3 a 0.6: Positivo
            - -0.2 a 0.2: Neutro
            - -0.6 a -0.3: Negativo
            - -1.0 a -0.7: Muito negativo
            
            Seja realista baseado no tipo de produto e mercado brasileiro.
            """
            
            response = self._make_api_call(prompt)
            result_text = response.text.strip()
            
            try:
                # Limpar resposta
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                review_data = json.loads(result_text)
                
                logger.info(f"Análise de reviews gerada para '{product_name}'")
                return review_data
                
            except json.JSONDecodeError:
                # Fallback
                return {
                    "summary": f"Análise de reviews para {product_name} não disponível.",
                    "pros": ["Qualidade", "Preço competitivo"],
                    "cons": ["Disponibilidade limitada"],
                    "score_sentimento": 0.5,
                    "total_reviews": 50
                }
                
        except Exception as e:
            logger.error(f"Erro ao analisar reviews para '{product_name}': {str(e)}")
            return {
                "summary": f"Análise não disponível para {product_name}.",
                "pros": [],
                "cons": [],
                "score_sentimento": 0.0,
                "total_reviews": 0
            }
    
    def analyze_offer_quality(self, price_history: List[Dict], current_price: float) -> Dict[str, Any]:
        """
        Analisa qualidade da oferta com forecast simples
        Integra tendência linear calculada via numpy
        """
        try:
            # Calcular tendência se há histórico suficiente
            trend_pct = 0
            days_analyzed = 0
            
            if len(price_history) >= 2:
                prices = [entry["price"] for entry in price_history[-7:]]  # Últimos 7 dias
                if len(prices) >= 2:
                    # Calcular slope usando numpy
                    x = np.arange(len(prices))
                    y = np.array(prices)
                    slope = np.polyfit(x, y, 1)[0]
                    trend_pct = (slope / prices[0]) * 100 if prices[0] > 0 else 0
                    days_analyzed = len(prices)
            
            prompt = f"""
            Você é Artemis, especialista em análise de ofertas e preços.
            
            Analise a qualidade da oferta atual para um produto com:
            - Preço atual: R$ {current_price:.2f}
            - Tendência dos últimos {days_analyzed} dias: {trend_pct:.2f}%
            - Histórico de preços: {len(price_history)} registros
            
            Retorne APENAS um JSON válido:
            {{
                "nota": 8.5,
                "justificativa": "Explicação detalhada da avaliação",
                "recomendacao": "COMPRAR_AGORA, AGUARDAR, ou EVITAR",
                "previsao": "Previsão baseada na tendência atual",
                "dias_para_mudanca": 5,
                "confianca": 0.8
            }}
            
            Critérios de avaliação:
            - Nota 9-10: Oferta excelente, preço muito baixo
            - Nota 7-8: Boa oferta, preço competitivo
            - Nota 5-6: Oferta regular, preço médio
            - Nota 3-4: Oferta ruim, preço alto
            - Nota 1-2: Oferta péssima, preço muito alto
            
            Considere a tendência de preços para a previsão.
            """
            
            response = self._make_api_call(prompt)
            result_text = response.text.strip()
            
            try:
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                analysis = json.loads(result_text)
                
                logger.info(f"Análise de oferta gerada - Nota: {analysis.get('nota', 'N/A')}")
                return analysis
                
            except json.JSONDecodeError:
                # Fallback baseado na tendência
                if trend_pct < -5:
                    recommendation = "COMPRAR_AGORA"
                    nota = 8.5
                elif trend_pct < 0:
                    recommendation = "COMPRAR_AGORA"
                    nota = 7.0
                elif trend_pct < 5:
                    recommendation = "AGUARDAR"
                    nota = 6.0
                else:
                    recommendation = "EVITAR"
                    nota = 4.0
                
                return {
                    "nota": nota,
                    "justificativa": f"Análise baseada na tendência de {trend_pct:.2f}%",
                    "recomendacao": recommendation,
                    "previsao": f"Preço pode {'subir' if trend_pct > 0 else 'descer'} em breve",
                    "dias_para_mudanca": 7,
                    "confianca": 0.6
                }
                
        except Exception as e:
            logger.error(f"Erro ao analisar oferta: {str(e)}")
            return {
                "nota": 5.0,
                "justificativa": "Análise não disponível",
                "recomendacao": "AGUARDAR",
                "previsao": "Dados insuficientes para previsão",
                "dias_para_mudanca": 0,
                "confianca": 0.0
            }
    
    @st.cache_data(ttl=1800)
    def compare_products(self, product_names: List[str], user_focus: str = "") -> str:
        """
        Compara produtos lado a lado com recomendações personalizadas
        Suporte dinâmico para 2-5 produtos
        """
        try:
            if len(product_names) < 2:
                return "É necessário pelo menos 2 produtos para comparação."
            
            if len(product_names) > 5:
                product_names = product_names[:5]  # Limitar a 5 produtos
            
            products_str = ", ".join(product_names)
            
            prompt = f"""
            Você é Artemis, especialista em comparação de produtos e recomendações de compra.
            
            Compare os seguintes produtos: {products_str}
            
            Foco do usuário: {user_focus if user_focus else "Análise geral"}
            
            Use Chain of Thought: Primeiro liste as especificações chave de cada produto, depois compare.
            
            Retorne uma análise estruturada em Markdown incluindo:
            
            ## 📊 Comparação Detalhada
            
            ### Especificações Principais
            | Produto | Preço Médio | Categoria | Principais Características |
            |---------|-------------|-----------|----------------------------|
            | Produto 1 | R$ XXX | Categoria | Características |
            
            ### 🏆 Ranking e Recomendações
            
            1. **Melhor Custo-Benefício**: [Produto] - Justificativa
            2. **Melhor Qualidade**: [Produto] - Justificativa  
            3. **Melhor para [Foco]**: [Produto] - Justificativa
            
            ### 💡 Veredito Final
            Recomendação principal baseada no foco do usuário.
            
            Seja objetivo, imparcial e focado em valor real para o consumidor brasileiro.
            """
            
            response = self._make_api_call(prompt)
            comparison = response.text.strip()
            
            logger.info(f"Comparação gerada para {len(product_names)} produtos")
            return comparison
            
        except Exception as e:
            logger.error(f"Erro ao comparar produtos: {str(e)}")
            return f"Erro na comparação dos produtos: {str(e)}"
    
    def answer_product_question(self, product_name: str, question: str, chat_id: str = "default") -> str:
        """
        Responde perguntas sobre produtos com memória de conversa
        Usa start_chat para manter contexto
        """
        try:
            context_prompt = f"""
            Você é Artemis, uma consultora de e-commerce especializada em produtos brasileiros.
            
            Produto em discussão: {product_name}
            
            Pergunta atual: {question}
            
            Responda de forma precisa, útil e focada no consumidor brasileiro.
            Se não souber algo específico, seja honesta e sugira onde o usuário pode encontrar a informação.
            """
            
            response = self._make_api_call(context_prompt, use_chat=True, chat_id=chat_id)
            answer = response.text.strip()
            
            logger.info(f"Pergunta respondida sobre '{product_name}': {question[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Erro ao responder pergunta sobre '{product_name}': {str(e)}")
            return f"Desculpe, não consegui processar sua pergunta sobre {product_name}. Tente novamente."
    
    @st.cache_data(ttl=3600)
    def suggest_alert_threshold(self, product_name: str, budget: float = None) -> float:
        """
        Sugere threshold de alerta baseado no produto e orçamento
        """
        try:
            budget_context = f"com orçamento de R$ {budget:.2f}" if budget else "sem orçamento específico"
            
            prompt = f"""
            Você é Artemis, especialista em estratégias de compra e alertas de preço.
            
            Sugira um preço de alerta ideal para "{product_name}" {budget_context}.
            
            Considere:
            - Tipo de produto e categoria
            - Faixa de preços típica no mercado brasileiro
            - Sazonalidade e tendências
            - Valor do orçamento fornecido (se houver)
            
            Retorne APENAS o valor numérico do preço sugerido (ex: 299.90), sem formatação adicional.
            """
            
            response = self._make_api_call(prompt)
            threshold_text = response.text.strip()
            
            # Extrair número da resposta
            try:
                # Remover caracteres não numéricos exceto ponto e vírgula
                import re
                numbers = re.findall(r'[\d,]+\.?\d*', threshold_text)
                if numbers:
                    threshold = float(numbers[0].replace(',', '.'))
                else:
                    threshold = 199.90  # Fallback
                
                logger.info(f"Threshold sugerido para '{product_name}': R$ {threshold:.2f}")
                return threshold
                
            except ValueError:
                logger.warning(f"Não foi possível extrair threshold da resposta: {threshold_text}")
                return 199.90
                
        except Exception as e:
            logger.error(f"Erro ao sugerir threshold para '{product_name}': {str(e)}")
            return 199.90


# Instância global do serviço
gemini_service = GeminiService()


# Funções de conveniência para uso nas páginas
def search_products(product_name: str) -> List[Dict[str, Any]]:
    """Busca produtos usando IA"""
    return gemini_service.search_products_with_gemini(product_name)


def generate_tags(product_name: str) -> str:
    """Gera tags para produto"""
    return gemini_service.generate_tags_for_product(product_name)


def generate_summary(product_name: str) -> str:
    """Gera resumo do produto"""
    return gemini_service.generate_product_summary(product_name)


def analyze_reviews(product_name: str) -> Dict[str, Any]:
    """Analisa reviews do produto"""
    return gemini_service.summarize_reviews(product_name)


def analyze_offer(price_history: List[Dict], current_price: float) -> Dict[str, Any]:
    """Analisa qualidade da oferta"""
    return gemini_service.analyze_offer_quality(price_history, current_price)


def compare_products_list(product_names: List[str], user_focus: str = "") -> str:
    """Compara lista de produtos"""
    return gemini_service.compare_products(product_names, user_focus)


def ask_question(product_name: str, question: str, chat_id: str = "default") -> str:
    """Faz pergunta sobre produto"""
    return gemini_service.answer_product_question(product_name, question, chat_id)


def suggest_threshold(product_name: str, budget: float = None) -> float:
    """Sugere threshold de alerta"""
    return gemini_service.suggest_alert_threshold(product_name, budget)
