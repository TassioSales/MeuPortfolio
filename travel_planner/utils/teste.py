"""
Flight Search Module (Enhanced)

This module provides robust flight search functionality using the Amadeus API
with AI-powered analysis from Google Gemini. This is a final, consolidated version
with all performance, usability, and compatibility fixes.
"""

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

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

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Validate API keys
if not all([GEMINI_API_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET]):
    logger.error("Missing required API keys")
    raise ValueError("Missing API keys: Ensure GEMINI_API_KEY, AMADEUS_API_KEY, and AMADEUS_API_SECRET are set in .env")

# API Endpoints
AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
AMADEUS_AIRPORT_NAME_URL = "https://test.api.amadeus.com/v1/reference-data/locations"

# Cache for Gemini responses and airport names
gemini_cache = TTLCache(maxsize=100, ttl=3600)
airport_cache = TTLCache(maxsize=1000, ttl=86400)

# Static IATA code to airport name mapping (fallback)
AIRPORT_NAME_FALLBACK = {
    "GRU": "São Paulo-Guarulhos International Airport",
    "SDU": "Santos Dumont Airport",
    "BSB": "Brasília International Airport",
    "CNF": "Confins International Airport",
    "GIG": "Rio de Janeiro-Galeão International Airport"
}

# Rate limiter for Amadeus API
amadeus_semaphore = asyncio.Semaphore(5)

class FlightSearchInput(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: str
    return_date: Optional[str] = None
    passengers: int = Field(1, ge=1, le=9)
    travel_class: str = Field("ECONOMY")
    non_stop: bool = Field(False)
    max_results: int = Field(50, ge=1, le=250)
    
    @field_validator('departure_date', 'return_date', mode='before')
    @classmethod
    def validate_dates(cls, v: Optional[str], info: Any) -> Optional[str]:
        if not v:
            return v
        try:
            date_obj = datetime.strptime(v, '%Y-%m-%d').date()
            min_date = datetime.now().date()
            if date_obj < min_date:
                raise ValueError(f'A data {v} precisa ser hoje ou uma data futura.')
            max_date = min_date + timedelta(days=365)
            if date_obj > max_date:
                raise ValueError(f'A data {v} não pode ser mais de um ano no futuro.')
            return v
        except ValueError as e:
            if 'does not match format' in str(e):
                raise ValueError('A data deve estar no formato YYYY-MM-DD.')
            raise

    @field_validator('origin', 'destination')
    @classmethod
    def validate_airport_codes(cls, v: str) -> str:
        v = v.upper()
        if not v.isalpha() or len(v) != 3:
            raise ValueError(f'O código de aeroporto {v} deve ser um código IATA válido de 3 letras.')
        return v
    
    @field_validator('travel_class')
    @classmethod
    def validate_travel_class(cls, v: str) -> str:
        v = v.upper()
        valid_classes = ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
        if v not in valid_classes:
            raise ValueError(f"A classe de viagem deve ser uma de: {', '.join(valid_classes)}")
        return v

class FlightSegment(BaseModel):
    departure_airport: str
    departure_airport_name: Optional[str] = None
    departure_terminal: Optional[str] = None
    departure_time: str
    arrival_airport: str
    arrival_airport_name: Optional[str] = None
    arrival_time: str
    airline_code: str
    airline_name: Optional[str] = None
    flight_number: str
    aircraft_code: Optional[str] = None
    duration: str
    operating_airline: Optional[str] = None
    layover_duration: Optional[str] = None
    fare_basis: Optional[str] = None
    seats_remaining: Optional[int] = None

class FlightOption(BaseModel):
    id: str
    price: float
    currency: str = "BRL"
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    passengers: int
    travel_class: str
    segments: List[FlightSegment]
    total_duration: str
    stop_count: int
    baggage_allowance: Optional[Dict[str, Any]] = None
    fare_rules: Optional[Dict[str, Any]] = None
    source: str = "amadeus"
    booking_code: Optional[str] = None


class AmadeusClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
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
            response = await self.http_client.post(
                AMADEUS_TOKEN_URL,
                data={'client_id': self.api_key, 'client_secret': self.api_secret, 'grant_type': 'client_credentials'},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 1799)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
            self.logger.info("Successfully obtained Amadeus access token")
            return self.access_token
        except httpx.RequestError as e:
            self.logger.error(f"Failed to obtain Amadeus token: {e}")
            raise Exception(f"Failed to authenticate with Amadeus API: {e}") from e
    
    async def _fetch_airport_name(self, iata_code: str) -> Optional[str]:
        if iata_code in airport_cache:
            return airport_cache[iata_code]
        if iata_code in AIRPORT_NAME_FALLBACK:
            return AIRPORT_NAME_FALLBACK[iata_code]
        
        async with amadeus_semaphore:
            try:
                token = await self._get_auth_token()
                params = {'subType': 'AIRPORT', 'keyword': iata_code}
                headers = {'Authorization': f'Bearer {token}'}
                response = await self.http_client.get(AMADEUS_AIRPORT_NAME_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json().get('data', [])
                if data and (name := data[0].get('name')):
                    airport_cache[iata_code] = name
                    return name
                return None
            except httpx.RequestError as e:
                self.logger.warning(f"Failed to fetch airport name for {iata_code}: {e}")
                return AIRPORT_NAME_FALLBACK.get(iata_code)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_flights(self, search_input: FlightSearchInput) -> List[FlightOption]:
        token = await self._get_auth_token()
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        params = {
            'originLocationCode': search_input.origin,
            'destinationLocationCode': search_input.destination,
            'departureDate': search_input.departure_date,
            'adults': search_input.passengers,
            'travelClass': search_input.travel_class,
            'nonStop': str(search_input.non_stop).lower(),
            'currencyCode': 'BRL',
            'max': 250
        }
        if search_input.return_date:
            params['returnDate'] = search_input.return_date
        
        all_offers = []
        next_url: Optional[str] = AMADEUS_FLIGHT_OFFERS_URL
        dictionaries = {}
        
        try:
            while next_url and len(all_offers) < search_input.max_results:
                self.logger.info(f"Searching flights on URL: {next_url}")
                current_params = params if next_url == AMADEUS_FLIGHT_OFFERS_URL else None
                response = await self.http_client.get(next_url, headers=headers, params=current_params)
                response.raise_for_status()
                data = response.json()
                
                offers_data = data.get('data', [])
                all_offers.extend(offers_data)
                dictionaries = data.get("dictionaries", {})
                self.logger.info(f"Received {len(offers_data)} offers, total is now {len(all_offers)}")

                links = data.get('meta', {}).get('links', {})
                next_url = links.get('next')

            final_offers = {"data": all_offers[:search_input.max_results], "dictionaries": dictionaries}
            return await self._process_amadeus_response(final_offers, search_input)

        except httpx.HTTPStatusError as e:
            error_message = f"Flight search failed: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_message)
            raise Exception(error_message) from e
        except httpx.RequestError as e:
            self.logger.error(f"Flight search request failed: {e}")
            raise Exception(f"Failed to search for flights: {e}") from e

    async def _process_amadeus_response(self, response_data: Dict, search_input: FlightSearchInput) -> List[FlightOption]:
        flight_options: List[FlightOption] = []
        carriers = response_data.get('dictionaries', {}).get('carriers', {})

        all_airport_codes = set()
        for offer in response_data.get('data', []):
            for itinerary in offer.get('itineraries', []):
                for segment in itinerary.get('segments', []):
                    all_airport_codes.add(segment['departure']['iataCode'])
                    all_airport_codes.add(segment['arrival']['iataCode'])

        airport_name_tasks = [self._fetch_airport_name(code) for code in all_airport_codes]
        airport_results = await asyncio.gather(*airport_name_tasks)
        airport_map = dict(zip(all_airport_codes, airport_results))

        for offer in response_data.get('data', []):
            try:
                for itinerary in offer.get('itineraries', []):
                    all_segments = []
                    for i, seg_data in enumerate(itinerary['segments']):
                        departure_time = datetime.fromisoformat(seg_data['departure']['at'])
                        arrival_time = datetime.fromisoformat(seg_data['arrival']['at'])
                        layover_duration = None
                        if i > 0:
                            prev_arrival = datetime.fromisoformat(itinerary['segments'][i-1]['arrival']['at'])
                            layover = departure_time - prev_arrival
                            layover_duration = f"PT{int(layover.total_seconds() // 3600)}H{int((layover.total_seconds() % 3600) // 60)}M"
                        
                        carrier_code = seg_data.get('carrierCode')
                        segment = FlightSegment(
                            departure_airport=seg_data['departure']['iataCode'],
                            departure_airport_name=airport_map.get(seg_data['departure']['iataCode']),
                            departure_terminal=seg_data['departure'].get('terminal'),
                            departure_time=seg_data['departure']['at'],
                            arrival_airport=seg_data['arrival']['iataCode'],
                            arrival_airport_name=airport_map.get(seg_data['arrival']['iataCode']),
                            arrival_time=seg_data['arrival']['at'],
                            airline_code=carrier_code,
                            airline_name=carriers.get(carrier_code, carrier_code),
                            flight_number=f"{carrier_code}{seg_data['number']}",
                            duration=seg_data['duration'],
                            seats_remaining=offer.get('numberOfBookableSeats')
                        )
                        all_segments.append(segment)
                    
                    flight_option = FlightOption(
                        id=offer['id'],
                        price=float(offer['price']['grandTotal']),
                        origin=search_input.origin,
                        destination=search_input.destination,
                        departure_date=search_input.departure_date,
                        return_date=search_input.return_date,
                        passengers=search_input.passengers,
                        travel_class=search_input.travel_class,
                        segments=all_segments,
                        total_duration=itinerary['duration'],
                        stop_count=len(itinerary['segments']) - 1
                    )
                    flight_options.append(flight_option)
            except (KeyError, IndexError) as e:
                self.logger.warning(f"Skipping malformed flight offer {offer.get('id', 'N/A')}: {e}")
                continue
        
        self.logger.info(f"Successfully processed {len(flight_options)} flight options.")
        return flight_options

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = logger.bind(service='gemini_client')
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    async def analyze_flights(self, search_input: FlightSearchInput, flight_options: List[FlightOption]) -> Dict[str, Any]:
        try:
            self.logger.info(f"Generating flight analysis for {len(flight_options)} options.")
            cache_key = f"analysis_{search_input.model_dump_json()}_{len(flight_options)}"
            if cache_key in gemini_cache:
                self.logger.info("Returning cached Gemini analysis.")
                return gemini_cache[cache_key]

            sorted_flights = sorted(flight_options, key=lambda x: x.price)[:10]
            flight_data = [f.model_dump(include={'price': True, 'total_duration': True, 'stop_count': True, 'segments': {'__all__': {'airline_name': True}}}) for f in sorted_flights]
            
            prompt = self._build_analysis_prompt(search_input, flight_data)
            response_text = await asyncio.wait_for(self._generate_content(prompt), timeout=30)
            analysis = self._parse_analysis_response(response_text)
            gemini_cache[cache_key] = analysis
            return analysis
        except Exception as e:
            self.logger.error(f"Error in Gemini analysis: {e}")
            return {'summary': f"Análise indisponível: {e}", 'recommendations': [], 'insights': {}}

    def _build_analysis_prompt(self, search_input: FlightSearchInput, flight_data: List[Dict]) -> str:
        # Este prompt instrui o Gemini a retornar JSON, uma abordagem compatível.
        return f"""
        Você é um analista de viagens especialista. Analise as opções de voo e forneça uma resposta ESTRITAMENTE NO FORMATO JSON em português. Não adicione nenhum texto ou formatação fora do JSON.

        PARÂMETROS DA BUSCA:
        - Origem: {search_input.origin}, Destino: {search_input.destination}
        - Partida: {search_input.departure_date}, Retorno: {search_input.return_date or 'Apenas ida'}

        OPÇÕES DE VOO (preço, duração, paradas, companhia):
        {json.dumps(flight_data, indent=2)}

        TAREFAS:
        1. Forneça um resumo conciso sobre as opções de voo, focando na variação de preço e duração.
        2. Dê 2 recomendações claras com justificativas (ex: melhor custo-benefício, voo mais rápido).
        3. Compartilhe um insight útil (ex: "Voos no início da manhã estão mais baratos.").

        FORMATO DA RESPOSTA (JSON):
        {{
            "summary": "Resumo da análise...",
            "recommendations": [
                {{"recommendation": "Melhor Custo-Benefício", "details": "O voo da [Companhia] por R$[Preço] oferece o melhor equilíbrio entre preço e duração."}},
                {{"recommendation": "Voo Mais Rápido", "details": "O voo direto da [Companhia] é a opção mais rápida, apesar de custar um pouco mais."}}
            ],
            "insights": {{"general": "Insight sobre a viagem..."}}
        }}
        """

    # SOLUÇÃO DE COMPATIBILIDADE: Esta versão não usa 'response_mime_type' e é mais compatível.
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_content(self, prompt: str) -> str:
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={'temperature': 0.5}
            )
            text = response.text
            # Limpa a resposta para extrair apenas o JSON, caso venha formatado
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            
            if not text: raise ValueError("Empty Gemini response")
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating Gemini content: {e}")
            if 'quota' in str(e).lower(): raise Exception(f"Gemini API quota exceeded: {e}") from e
            raise

    # SOLUÇÃO DE COMPATIBILIDADE: Parser simples que funciona com o _generate_content acima.
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Gemini JSON for analysis: {e}")
            return {'summary': f"Falha ao processar a análise: {response_text[:100]}...", 'recommendations': [], 'insights': {}}


async def search_flights(
    origin: str, destination: str, departure_date: str, return_date: Optional[str] = None,
    passengers: int = 1, travel_class: str = "ECONOMY", non_stop: bool = False,
    use_gemini_analysis: bool = True, max_results: int = 50
) -> Dict[str, Any]:
    logger.info(f"Starting flight search: {origin} to {destination} on {departure_date}")
    start_time = time.time()
    
    try:
        search_input = FlightSearchInput(
            origin=origin, destination=destination, departure_date=departure_date,
            return_date=return_date, passengers=passengers, travel_class=travel_class,
            non_stop=non_stop, max_results=max_results
        )
        
        amadeus_client = AmadeusClient(api_key=AMADEUS_API_KEY, api_secret=AMADEUS_API_SECRET)
        flight_options = await amadeus_client.search_flights(search_input)
        
        analysis = {}
        if flight_options and use_gemini_analysis:
            gemini_client = GeminiClient(api_key=GEMINI_API_KEY)
            analysis = await gemini_client.analyze_flights(search_input, flight_options)
        
        execution_time = (time.time() - start_time) * 1000
        result = {
            'metadata': {
                'search_id': f"flt_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'execution_time_ms': int(execution_time),
                'source': 'amadeus',
                'result_count': len(flight_options)
            },
            'search_parameters': search_input.model_dump(exclude_none=True),
            'flights': [option.model_dump() for option in flight_options],
            'analysis': analysis
        }
        
        logger.info(f"Search completed in {execution_time:.0f}ms with {len(flight_options)} results")
        return result
        
    except ValidationError as e:
        logger.error(f"Input validation error: {e}")
        raise ValueError(f"Invalid input: {e}") from e
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise Exception(f"Failed to complete search: {e}") from e


async def main():
    print("✈️  --- Buscador de Voos Interativo --- ✈️")

    try:
        origin = input("Digite o código do aeroporto de ORIGEM (ex: GRU): ").upper().strip()
        destination = input("Digite o código do aeroporto de DESTINO (ex: SDU): ").upper().strip()

        while True:
            departure_date_str = input(f"Data de PARTIDA ({origin} -> {destination}) [DD-MM-YYYY]: ").strip()
            try:
                departure_dt = datetime.strptime(departure_date_str, '%d-%m-%Y')
                departure_date_api = departure_dt.strftime('%Y-%m-%d')
                break
            except ValueError:
                print("❗️ Formato de data inválido. Por favor, use DD-MM-YYYY.")

        is_round_trip = input("A viagem é de ida e volta? (s/n): ").lower().strip()
        return_date_api = None
        if is_round_trip == 's':
            while True:
                return_date_str = input(f"Data de RETORNO ({destination} -> {origin}) [DD-MM-YYYY]: ").strip()
                try:
                    return_dt = datetime.strptime(return_date_str, '%d-%m-%Y')
                    if return_dt < departure_dt:
                        print("❗️ A data de retorno não pode ser anterior à data de partida.")
                        continue
                    return_date_api = return_dt.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    print("❗️ Formato de data inválido. Por favor, use DD-MM-YYYY.")

        passengers = int(input("Número de passageiros (1-9): ").strip())

        print("\n🔄  Buscando voos... Isso pode levar um momento.")
        result = await search_flights(
            origin=origin, destination=destination, departure_date=departure_date_api,
            return_date=return_date_api, passengers=passengers, max_results=20
        )

        flights = result.get('flights', [])
        if not flights:
            print("\n❌ Nenhum voo encontrado para os critérios informados.")
            return

        print(f"\n✅ Busca concluída! {len(flights)} opções encontradas.")

        if (analysis := result.get('analysis', {})) and analysis.get('summary'):
            print("\n🧠 --- Análise da IA ---")
            print(analysis['summary'])

        print("\n⭐ --- Top 5 Opções de Voo ---")
        for flight in flights[:5]:
            price = flight.get('price', 0)
            airline = flight.get('segments', [{}])[0].get('airline_name', 'N/A')
            stops = flight.get('stop_count', 'N/A')
            duration_str = flight.get('total_duration', 'PT0H0M').replace("PT", "").replace("H", "h ").replace("M", "m")
            print(f"- {airline}: R$ {price:.2f} | Paradas: {stops} | Duração: {duration_str}")

    except (ValueError, ValidationError) as ve:
        print(f"\n❗️ Erro de validação: {ve}")
        print("Por favor, verifique os dados de entrada e tente novamente.")
    except Exception as e:
        print(f"\n💥 Ocorreu um erro inesperado durante a busca: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBusca cancelada pelo usuário.")