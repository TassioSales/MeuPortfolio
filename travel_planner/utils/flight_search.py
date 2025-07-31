"""
Flight Search Module (Enhanced - v3)

This module provides robust flight search functionality using the Amadeus API
with AI-powered analysis from Google Gemini. This version incorporates a highly
intelligent and structured prompt for personalized travel analysis.
"""

import os
import json
import time
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field, field_validator, ValidationError
from dotenv import load_dotenv
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai

# Configure logging
try:
    from loguru import logger
    logger = logger.bind(service='flight_search')
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API Configuration and Validation
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
if not all([GEMINI_API_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET]):
    raise ValueError("Missing critical API keys in .env file.")

# API Endpoints & Constants
AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
AMADEUS_AIRPORT_NAME_URL = "https://test.api.amadeus.com/v1/reference-data/locations"
gemini_cache = TTLCache(maxsize=100, ttl=3600)
airport_cache = TTLCache(maxsize=1000, ttl=86400)
amadeus_semaphore = asyncio.Semaphore(5)

# MELHORIA: Modelos Pydantic atualizados para suportar as novas funcionalidades do prompt
class FlightSearchInput(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: date
    return_date: Optional[date] = None
    passengers: int = Field(1, ge=1, le=9)
    travel_class: str = Field("ECONOMY")
    non_stop: bool = Field(False)
    max_results: int = Field(50, ge=1, le=250)
    preferences: Optional[Dict[str, Any]] = None

    @field_validator('departure_date', 'return_date', mode='before')
    @classmethod
    def validate_dates(cls, v: Any) -> Optional[date]:
        if v is None: return v
        if isinstance(v, str): v = datetime.strptime(v, '%Y-%m-%d').date()
        if isinstance(v, date):
            if v < date.today(): raise ValueError('A data não pode ser no passado.')
            if v > date.today() + timedelta(days=365): raise ValueError('A data não pode ser mais de um ano no futuro.')
            return v
        raise TypeError('Tipo de data inválido.')

    @field_validator('origin', 'destination')
    @classmethod
    def validate_airport_codes(cls, v: str) -> str:
        v = v.upper()
        if not v.isalpha() or len(v) != 3:
            raise ValueError(f'O código de aeroporto {v} deve ser um código IATA válido de 3 letras.')
        return v

class FlightSegment(BaseModel):
    departure_airport: str
    departure_time: str
    arrival_airport: str
    arrival_time: str
    airline_name: Optional[str] = None
    flight_number: str
    duration: str

class FlightOption(BaseModel):
    id: str
    price: float
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date]
    segments: List[FlightSegment]
    total_duration: str
    stop_count: int
    booking_link: Optional[str] = None

# ... (AmadeusClient permanece o mesmo, pois sua lógica de busca e processamento é robusta) ...
class AmadeusClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key, self.api_secret = api_key, api_secret
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.logger = logger.bind(service='amadeus_client')
        self.http_client = httpx.AsyncClient(timeout=20.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get_auth_token(self) -> str:
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        try:
            self.logger.info("Requesting new Amadeus access token")
            response = await self.http_client.post(AMADEUS_TOKEN_URL, data={'client_id': self.api_key, 'client_secret': self.api_secret, 'grant_type': 'client_credentials'}, headers={'Content-Type': 'application/x-www-form-urlencoded'})
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_data.get('expires_in', 1799) - 300)
            self.logger.info("Successfully obtained Amadeus access token")
            return self.access_token
        except httpx.RequestError as e:
            self.logger.error(f"Failed to obtain Amadeus token: {e}")
            raise Exception(f"Failed to authenticate with Amadeus API: {e}") from e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_flights(self, search_input: FlightSearchInput) -> List[FlightOption]:
        token = await self._get_auth_token()
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        params = {
            'originLocationCode': search_input.origin, 'destinationLocationCode': search_input.destination,
            'departureDate': search_input.departure_date.strftime('%Y-%m-%d'),
            'adults': search_input.passengers, 'travelClass': search_input.travel_class,
            'nonStop': str(search_input.non_stop).lower(), 'currencyCode': 'BRL', 'max': 250
        }
        if search_input.return_date:
            params['returnDate'] = search_input.return_date.strftime('%Y-%m-%d')
        
        all_offers, dictionaries = [], {}
        next_url: Optional[str] = AMADEUS_FLIGHT_OFFERS_URL
        try:
            while next_url and len(all_offers) < search_input.max_results:
                self.logger.info(f"Searching flights on URL: {next_url}")
                current_params = params if next_url == AMADEUS_FLIGHT_OFFERS_URL else None
                response = await self.http_client.get(next_url, headers=headers, params=current_params)
                response.raise_for_status()
                data = response.json()
                offers_data, dictionaries = data.get('data', []), data.get("dictionaries", {})
                all_offers.extend(offers_data)
                self.logger.info(f"Received {len(offers_data)} offers, total is now {len(all_offers)}")
                next_url = data.get('meta', {}).get('links', {}).get('next')
            final_offers = {"data": all_offers[:search_input.max_results], "dictionaries": dictionaries}
            return self._process_amadeus_response(final_offers, search_input)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Flight search failed: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"Failed to search for flights: {e}") from e

    def _process_amadeus_response(self, response_data: Dict, search_input: FlightSearchInput) -> List[FlightOption]:
        flight_options: List[FlightOption] = []
        carriers = response_data.get('dictionaries', {}).get('carriers', {})
        for offer in response_data.get('data', []):
            try:
                for itinerary in offer.get('itineraries', []):
                    all_segments = []
                    for seg_data in itinerary['segments']:
                        carrier_code = seg_data.get('carrierCode')
                        all_segments.append(FlightSegment(
                            departure_airport=seg_data['departure']['iataCode'], departure_time=seg_data['departure']['at'],
                            arrival_airport=seg_data['arrival']['iataCode'], arrival_time=seg_data['arrival']['at'],
                            airline_name=carriers.get(carrier_code, carrier_code),
                            flight_number=f"{carrier_code}{seg_data['number']}", duration=seg_data['duration']
                        ))
                    flight_options.append(FlightOption(
                        id=offer['id'], price=float(offer['price']['grandTotal']),
                        origin=search_input.origin, destination=search_input.destination,
                        departure_date=search_input.departure_date, return_date=search_input.return_date,
                        segments=all_segments, total_duration=itinerary['duration'],
                        stop_count=len(itinerary['segments']) - 1
                    ))
            except (KeyError, IndexError) as e:
                self.logger.warning(f"Skipping malformed flight offer {offer.get('id', 'N/A')}: {e}")
        self.logger.info(f"Successfully processed {len(flight_options)} flight options.")
        return flight_options

# MELHORIA: Classe GeminiClient atualizada com a nova lógica de prompt
class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = logger.bind(service='gemini_client')
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}"); raise

    async def analyze_flights(self, search_input: FlightSearchInput, flight_options: List[FlightOption], language: str = "pt-BR") -> Dict[str, Any]:
        try:
            flight_data = [f.model_dump(include={
                'price': True, 
                'total_duration': True, 
                'stop_count': True, 
                'segments': {'__all__': {'airline_name'}}
            }) for f in flight_options[:10]]  # Limit to 10 flights for analysis
            prompt = self._build_analysis_prompt(search_input, flight_data, language)
            response_text = await asyncio.wait_for(self._generate_content(prompt), timeout=45)
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Error in Gemini analysis: {e}")
            return {"summary": {"message": f"Análise indisponível: {e}"}, "recommendations": [], "insights": {}}

    def _build_analysis_prompt(self, search_input: FlightSearchInput, flight_data: List[Dict], language: str = "pt-BR") -> str:
        # Esta é a sua implementação de prompt robusto, integrada como um método de classe.
        if not flight_data:
            return self._build_empty_data_prompt(search_input, language)

        departure_date = search_input.departure_date.strftime("%d-%m-%Y")
        return_date = search_input.return_date.strftime("%d-%m-%Y") if search_input.return_date else "Apenas ida"
        preferences = search_input.preferences or {}
        budget = preferences.get("budget", "Não especificado")
        max_stops = preferences.get("max_stops", "Não especificado")
        
        lang_templates = {
            "pt-BR": {
                "role": "Você é um analista de viagens sênior e especialista em dados.",
                "task": "Analise as opções de voo e forneça uma resposta JSON estruturada e detalhada em português.",
                "summary": "Forneça um resumo quantitativo: número de voos, faixa de preço (min/max), duração média e faixa de paradas (min/max).",
                "recs": "Com base nos dados e preferências, forneça 2-3 recomendações (melhor custo-benefício, mais rápido, melhor voo geral) com justificativas claras. Inclua o índice do voo na lista original.",
                "insights": "Forneça 1-2 insights acionáveis sobre a busca (ex: 'Voos diretos são 30% mais caros, mas economizam 5 horas.').",
                "context": "Considere o contexto da busca (orçamento, paradas) para personalizar a análise."
            }
        }
        template = lang_templates.get(language, lang_templates["pt-BR"])

        # Define JSON template with proper escaping
        json_template = '''
        {{
            "summary": {{
                "flight_count": "<int>",
                "price_range": {{"min": "<float>", "max": "<float>"}},
                "avg_duration": "<str>",
                "stop_range": {{"min": "<int>", "max": "<int>"}}
            }},
            "recommendations": [
                {{
                    "recommendation": "<str>",
                    "details": "<str>",
                    "flight_index": "<int>"
                }}
            ],
            "insights": {{"general": "<str>"}}
        }}
        '''

        return f"""{template['role']} {template['task']}
        **DADOS DA BUSCA:**
        - Rota: {search_input.origin} -> {search_input.destination}
        - Datas: {departure_date} a {return_date}
        - Preferências: Orçamento de R${budget}, Máximo de {max_stops} paradas.
        **OPÇÕES DE VOO DISPONÍVEIS (preço, duração, paradas, companhia):**
        {json.dumps(flight_data, indent=2, ensure_ascii=False)}
        **TAREFAS:**
        1. Resumo Quantitativo: {template['summary']}
        2. Recomendações Detalhadas: {template['recs']}
        3. Insights Acionáveis: {template['insights']}
        4. Análise de Contexto: {template['context']}
        **FORMATO OBRIGATÓRIO (JSON):**
        {json_template}"""

    def _build_empty_data_prompt(self, search_input: FlightSearchInput, language: str = "pt-BR") -> str:
        # ... (implementação como você forneceu, para mensagens de erro amigáveis) ...
        return f"""Você é um assistente de viagens. Nenhum voo foi encontrado para {search_input.origin}->{search_input.destination}.
        Gere uma resposta JSON com uma mensagem amigável sugerindo ao usuário verificar as datas ou procurar aeroportos próximos.
        FORMATO JSON: {{"summary": {{"message": "Sua mensagem amigável aqui."}}, "recommendations": [], "insights": {{}}}}"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_content(self, prompt: str) -> str:
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    'temperature': 0.5,
                    'max_output_tokens': 2048,
                    'top_p': 0.9,
                    'top_k': 40
                }
            )
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            if not text:
                raise ValueError("Empty Gemini response")
            return text.strip()
        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return '{"summary": {"message": "Erro ao gerar análise"}, "recommendations": [], "insights": {}}'

# ... (Funções auxiliares e a função principal search_flights) ...
def _create_google_flights_link(origin: str, destination: str, departure_date: date, return_date: Optional[date] = None) -> str:
    """
    Gera um link de busca para o Google Flights com base nos parâmetros do voo,
    usando um formato de URL moderno e funcional.
    """
    # URL base para a busca simplificada do Google Flights
    base_url = "https://www.google.com/flights"
    
    # Parâmetros da busca
    # Os nomes 'dep_iata', 'ar_iata', 'dep_date', 'ret_date' são usados pelo Google
    params = {
        'dep_iata': origin,
        'ar_iata': destination,
        'dep_date': departure_date.strftime('%Y-%m-%d'),
    }
    
    if return_date:
        params['ret_date'] = return_date.strftime('%Y-%m-%d')
        
    # urlencode garante que todos os parâmetros sejam formatados corretamente para a URL
    query_string = urlencode(params)
    
    # Retorna o link completo
    return f"{base_url}?{query_string}"

async def search_flights(search_input: FlightSearchInput) -> Dict[str, Any]:
    logger.info(f"Starting flight search for: {search_input.origin} to {search_input.destination}")
    start_time = time.time()
    try:
        amadeus_client = AmadeusClient(api_key=AMADEUS_API_KEY, api_secret=AMADEUS_API_SECRET)
        flight_options = await amadeus_client.search_flights(search_input)
        
        for option in flight_options:
            option.booking_link = _create_google_flights_link(
                origin=option.origin, destination=option.destination,
                departure_date=option.departure_date, return_date=option.return_date)
        
        analysis = {}
        if flight_options:
            gemini_client = GeminiClient(api_key=GEMINI_API_KEY)
            analysis = await gemini_client.analyze_flights(search_input, flight_options)
        
        return {
            'search_parameters': search_input.model_dump(mode='json'),
            'flights': [option.model_dump(mode='json') for option in flight_options],
            'analysis': analysis
        }
    except Exception as e:
        logger.error(f"Search process failed: {e}"); raise

async def main():
    print("✈️  --- Buscador de Voos Inteligente --- ✈️")
    try:
        origin = input("Aeroporto de ORIGEM (ex: GRU): ").upper().strip()
        destination = input("Aeroporto de DESTINO (ex: SDU): ").upper().strip()

        while True:
            try:
                departure_date = datetime.strptime(input(f"Data de PARTIDA [DD-MM-YYYY]: ").strip(), '%d-%m-%Y').date()
                break
            except ValueError: print("❗️ Formato de data inválido.")
        
        return_date = None
        if input("Viagem de ida e volta? (s/n): ").lower() == 's':
            while True:
                try:
                    return_date_str = input(f"Data de RETORNO [DD-MM-YYYY]: ").strip()
                    return_date = datetime.strptime(return_date_str, '%d-%m-%Y').date()
                    if return_date < departure_date: print("❗️ Data de retorno não pode ser antes da partida."); continue
                    break
                except ValueError: print("❗️ Formato de data inválido.")

        while True:
            try:
                passengers = int(input("Número de passageiros (1-9): ").strip())
                if 1 <= passengers <= 9:
                    break
                print("Por favor, insira um número entre 1 e 9.")
            except ValueError:
                print("Por favor, insira um número válido.")
        
        # MELHORIA: Coleta de preferências do usuário
        print("\n--- Preferências (Opcional) ---")
        budget_str = input("Orçamento máximo por pessoa (deixe em branco se não houver): ").strip()
        max_stops_str = input("Número máximo de paradas (deixe em branco se não houver): ").strip()
        preferences = {
            "budget": float(budget_str) if budget_str and budget_str.replace('.', '').isdigit() else None,
            "max_stops": int(max_stops_str) if max_stops_str and max_stops_str.isdigit() else None
        }

        print("\n🔄  Analisando voos com IA... Isso pode levar um momento.")
        
        search_input = FlightSearchInput(
            origin=origin, destination=destination, departure_date=departure_date,
            return_date=return_date, passengers=passengers, preferences=preferences
        )
        result = await search_flights(search_input)

        flights = result.get('flights', [])
        analysis = result.get('analysis', {})

        if not flights:
            print(f"\n❌ {analysis.get('summary', {}).get('message', 'Nenhum voo encontrado.')}")
            return

        print("\n🧠 --- Análise da IA ---")
        print(f"   Resumo: {analysis.get('summary', {}).get('message', 'N/A')}")
        if insights := analysis.get('insights', {}).get('general'):
            print(f"   Insight: {insights}")
        
        print("\n⭐ --- Recomendações da IA ---")
        for rec in analysis.get('recommendations', []):
            print(f"  - {rec['recommendation']}: {rec['details']}")

        print("\n🏆 --- Top Voos Encontrados (do mais barato para o mais caro) --- 🏆")
        sorted_flights = sorted(flights, key=lambda f: f['price'])
        for i, flight in enumerate(sorted_flights[:10], 1):
            price = flight.get('price', 0)
            airline = flight.get('segments', [{}])[0].get('airline_name', 'N/A')
            stops_text = "Direto" if flight['stop_count'] == 0 else f"{flight['stop_count']} parada(s)"
            print("-" * 60)
            print(f"✈️ Voo {i} - {airline} | 💰 R$ {price:,.2f} | ⏰ {flight['total_duration'].replace('PT','')} ({stops_text})")
            print(f"  🔗 Link para visualização: {flight.get('booking_link', 'N/A')}")
        print("-" * 60)

    except (ValueError, ValidationError) as ve:
        print(f"\n❗️ Erro de entrada: {ve}")
    except Exception as e:
        print(f"\n💥 Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nBusca cancelada pelo usuário.")