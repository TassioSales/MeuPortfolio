"""Tests for the flight_search module."""

import os
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock, ANY
from typing import Dict, Any

# Mock the genai module before importing flight_search
import sys
from unittest.mock import MagicMock

class MockGenAI:
    class GenerativeModel:
        def __init__(self, *args, **kwargs):
            pass
        
        def generate_content(self, *args, **kwargs):
            mock_response = MagicMock()
            mock_response.text = '{"analysis": "Test analysis"}'
            return mock_response

sys.modules['genai'] = MockGenAI

from utils.flight_search import (
    FlightSearchInput, FlightSegment, FlightOption,
    AmadeusClient, GeminiClient, search_flights
)

# Helper function to get future dates
def get_future_date(days_in_future: int) -> str:
    return (datetime.now() + timedelta(days=days_in_future)).strftime('%Y-%m-%d')

# Fixtures for test data
@pytest.fixture
def sample_search_input():
    return {
        'origin': 'GRU',
        'destination': 'SDU',
        'departure_date': get_future_date(30),  # 30 days from now
        'return_date': get_future_date(37),     # 37 days from now (7-day trip)
        'passengers': 1,
        'travel_class': 'ECONOMY',
        'non_stop': False
    }

@pytest.fixture
def mock_amadeus_response():
    return {
        'meta': {'count': 1},
        'data': [{
            'id': '1',
            'price': {
                'total': '1200.50',
                'currency': 'BRL'
            },
            'itineraries': [{
                'duration': 'PT2H10M',
                'segments': [{
                    'departure': {
                        'iataCode': 'GRU',
                        'terminal': '2',
                        'at': '2025-08-30T08:30:00'
                    },
                    'arrival': {
                        'iataCode': 'SDU',
                        'terminal': '1',
                        'at': '2025-08-30T10:40:00'
                    },
                    'carrierCode': 'LA',
                    'number': '1234',
                    'aircraft': {'code': '320'},
                    'duration': 'PT2H10M',
                    'numberOfStops': 0
                }]
            }],
            'pricingOptions': {'fareType': ['PUBLISHED']}
        }]
    }

# Mock API responses
MOCK_AMADEUS_RESPONSE = {
    'data': [
        {
            'id': '1',
            'price': {'grandTotal': '1200.50', 'currency': 'BRL'},
            'itineraries': [
                {
                    'duration': 'PT2H10M',
                    'segments': [
                        {
                            'departure': {'iataCode': 'GRU', 'terminal': '2', 'at': '2024-04-15T08:30:00'},
                            'arrival': {'iataCode': 'SDU', 'terminal': '1', 'at': '2024-04-15T10:40:00'},
                            'carrierCode': 'LA',
                            'number': '1234',
                            'aircraft': {'code': '320'},
                            'operating': {'carrierCode': 'LA'},
                            'duration': 'PT2H10M'
                        }
                    ]
                }
            ],
            'travelerPricings': [
                {'fareDetailsBySegment': [{'includedCheckedBags': {'quantity': 1}, 'cabin': 'ECONOMY'}]}
            ],
            'pricingOptions': {'fareType': ['PUBLISHED']}
        }
    ]
}


class TestFlightSearchInput:
    """Tests for the FlightSearchInput model."""
    
    def test_valid_input(self):
        """Test that valid input passes validation."""
        input_data = SAMPLE_SEARCH_INPUT.copy()
        search_input = FlightSearchInput(**input_data)
        
        assert search_input.origin == 'GRU'
        assert search_input.destination == 'SDU'
        assert search_input.passengers == 1
        assert search_input.travel_class == 'ECONOMY'
    
    def test_invalid_airport_code(self):
        """Test validation of airport codes."""
        input_data = SAMPLE_SEARCH_INPUT.copy()
        input_data['origin'] = 'INVALID'
        
        with pytest.raises(ValueError) as excinfo:
            FlightSearchInput(**input_data)
        assert 'Airport code INVALID must be a 3-letter IATA code' in str(excinfo.value)
    
    def test_past_date_validation(self):
        """Test that past dates are rejected."""
        input_data = SAMPLE_SEARCH_INPUT.copy()
        input_data['departure_date'] = '2020-01-01'
        
        with pytest.raises(ValueError) as excinfo:
            FlightSearchInput(**input_data)
        assert 'cannot be in the past' in str(excinfo.value)
    
    def test_passenger_count_validation(self):
        """Test validation of passenger count."""
        input_data = SAMPLE_SEARCH_INPUT.copy()
        input_data['passengers'] = 10  # More than max allowed (9)
        
        with pytest.raises(ValueError) as excinfo:
            FlightSearchInput(**input_data)
        assert 'Input should be less than or equal to 9' in str(excinfo.value)


class TestAmadeusClient:
    """Tests for the AmadeusClient class."""
    
    @patch('utils.flight_search.requests.post')
    def test_get_auth_token(self, mock_post, mock_amadeus_response):
        """Test successful token retrieval."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 1799
        }
        mock_post.return_value = mock_response
        
        with patch('utils.flight_search.log') as mock_log:
            client = AmadeusClient(api_key='test_key', api_secret='test_secret')
            token = client._get_auth_token()
            
            assert token == 'test_token'
            assert client.access_token == 'test_token'
            assert client.token_expiry is not None
            mock_log.info.assert_called()
    
    @patch('utils.flight_search.requests.get')
    @patch('utils.flight_search.requests.post')
    def test_search_flights(self, mock_post, mock_get, mock_amadeus_response):
        """Test flight search with mock API response."""
        # Setup auth mock
        auth_response = MagicMock()
        auth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 1799}
        mock_post.return_value = auth_response
        
        # Setup search mock
        search_response = MagicMock()
        search_response.json.return_value = mock_amadeus_response
        search_response.raise_for_status.return_value = None
        mock_get.return_value = search_response
        
        # Test
        with patch('utils.flight_search.log') as mock_log:
            client = AmadeusClient(api_key='test_key', api_secret='test_secret')
            search_input = FlightSearchInput(**SAMPLE_SEARCH_INPUT)
            results = client.search_flights(search_input)
            
            # Assertions
            assert len(results) == 1
            assert results[0].price == 1200.50
            assert results[0].segments[0].airline_code == 'LA'
            assert results[0].segments[0].flight_number == '1234'
            mock_log.info.assert_called()
    
    @patch('utils.flight_search.requests.get')
    @patch('utils.flight_search.requests.post')
    def test_search_flights_error_handling(self, mock_post, mock_get):
        """Test error handling during flight search."""
        # Setup auth mock
        auth_response = MagicMock()
        auth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 1799}
        mock_post.return_value = auth_response
        
        # Setup error mock
        mock_get.side_effect = Exception("API Error")
        
        # Test
        with patch('utils.flight_search.log') as mock_log:
            client = AmadeusClient(api_key='test_key', api_secret='test_secret')
            search_input = FlightSearchInput(**SAMPLE_SEARCH_INPUT)
            
            with pytest.raises(Exception) as excinfo:
                client.search_flights(search_input)
            assert "Failed to search for flights" in str(excinfo.value)
            mock_log.error.assert_called()


class TestGeminiClient:
    """Tests for the GeminiClient class."""
    
    @patch('utils.flight_search.genai')
    def test_analyze_flights(self, mock_genai):
        """Test flight analysis with Gemini."""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'analysis': 'Test analysis',
            'recommendations': ['Rec 1', 'Rec 2'],
            'insights': {'key': 'value'}
        })
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test
        client = GeminiClient(api_key='test_key')
        search_input = FlightSearchInput(**SAMPLE_SEARCH_INPUT)
        
        # Create a sample flight option
        segment = FlightSegment(
            departure_airport='GRU',
            departure_terminal='2',
            departure_time='2024-04-15T08:30:00',
            arrival_airport='SDU',
            arrival_terminal='1',
            arrival_time='2024-04-15T10:40:00',
            airline_code='LA',
            flight_number='LA1234',
            duration='PT2H10M'
        )
        
        flight_option = FlightOption(
            id='1',
            price=1200.50,
            currency='BRL',
            origin='GRU',
            destination='SDU',
            departure_date=SAMPLE_SEARCH_INPUT['departure_date'],
            return_date=SAMPLE_SEARCH_INPUT['return_date'],
            passengers=1,
            travel_class='ECONOMY',
            segments=[segment],
            total_duration='PT2H10M',
            stop_count=0,
            source='amadeus'
        )
        
        # Call the method
        analysis = client.analyze_flights(search_input, [flight_option])
        
        # Assertions
        assert 'analysis' in analysis
        assert 'recommendations' in analysis
        assert 'insights' in analysis
        assert analysis['analysis'] == 'Test analysis'
    
    @patch('utils.flight_search.genai')
    def test_generate_fallback_flights(self, mock_genai):
        """Test fallback flight generation."""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'flights': [
                {
                    'id': 'fallback_1',
                    'price': 1100.00,
                    'currency': 'BRL',
                    'airline': 'GOL',
                    'flight_number': 'G31000',
                    'departure_time': '2024-04-15T09:00:00',
                    'arrival_time': '2024-04-15T11:00:00',
                    'stops': 1,
                    'duration': 'PT2H',
                    'baggage': {"cabin": "1 x 23kg", "hand": "1 x 10kg"},
                    'refundable': True
                }
            ]
        })
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test
        client = GeminiClient(api_key='test_key')
        search_input = FlightSearchInput(**SAMPLE_SEARCH_INPUT)
        flights = client.generate_fallback_flights(search_input)
        
        # Assertions
        assert len(flights) == 1
        assert flights[0].price == 1100.00
        assert flights[0].source == 'gemini'
        assert flights[0].segments[0].airline_code == 'GOL'


class TestSearchFlightsIntegration:
    """Integration tests for the search_flights function."""
    
    @patch('utils.flight_search.AmadeusClient.search_flights')
    @patch('utils.flight_search.GeminiClient.analyze_flights')
    def test_successful_search(self, mock_analyze, mock_search):
        """Test successful flight search with analysis."""
        # Create a sample flight option
        segment = FlightSegment(
            departure_airport='GRU',
            departure_terminal='2',
            departure_time='2024-04-15T08:30:00',
            arrival_airport='SDU',
            arrival_terminal='1',
            arrival_time='2024-04-15T10:40:00',
            airline_code='LA',
            flight_number='LA1234',
            duration='PT2H10M'
        )
        
        flight_option = FlightOption(
            id='1',
            price=1200.50,
            currency='BRL',
            origin='GRU',
            destination='SDU',
            departure_date=SAMPLE_SEARCH_INPUT['departure_date'],
            return_date=SAMPLE_SEARCH_INPUT['return_date'],
            passengers=1,
            travel_class='ECONOMY',
            segments=[segment],
            total_duration='PT2H10M',
            stop_count=0,
            source='amadeus'
        )
        
        # Setup mocks
        mock_search.return_value = [flight_option]
        mock_analyze.return_value = {
            'analysis': 'Test analysis',
            'recommendations': ['Rec 1'],
            'insights': {'key': 'value'}
        }
        
        # Call the function
        result = search_flights(**SAMPLE_SEARCH_INPUT)
        
        # Assertions
        assert 'flights' in result
        assert len(result['flights']) == 1
        assert result['flights'][0]['price'] == 1200.50
        assert 'analysis' in result
        assert result['analysis']['analysis'] == 'Test analysis'
    
    @patch('utils.flight_search.AmadeusClient.search_flights')
    @patch('utils.flight_search.GeminiClient.generate_fallback_flights')
    def test_fallback_to_gemini(self, mock_fallback, mock_search):
        """Test fallback to Gemini when Amadeus fails."""
        # Setup mocks
        mock_search.side_effect = Exception("API Error")
        
        # Create a fallback flight option
        segment = FlightSegment(
            departure_airport='GRU',
            departure_time='2024-04-15T09:00:00',
            arrival_airport='SDU',
            arrival_time='2024-04-15T11:00:00',
            airline_code='G3',
            flight_number='G31000',
            duration='PT2H'
        )
        
        fallback_flight = FlightOption(
            id='fallback_1',
            price=1100.00,
            currency='BRL',
            origin='GRU',
            destination='SDU',
            departure_date=SAMPLE_SEARCH_INPUT['departure_date'],
            return_date=SAMPLE_SEARCH_INPUT['return_date'],
            passengers=1,
            travel_class='ECONOMY',
            segments=[segment],
            total_duration='PT2H',
            stop_count=0,
            source='gemini'
        )
        
        mock_fallback.return_value = [fallback_flight]
        
        # Call the function with fallback enabled
        result = search_flights(
            **SAMPLE_SEARCH_INPUT,
            enable_fallback=True
        )
        
        # Assertions
        assert 'flights' in result
        assert len(result['flights']) == 1
        assert result['flights'][0]['price'] == 1100.00
        assert result['metadata']['source'] == 'gemini_fallback'
    
    def test_invalid_input_handling(self):
        """Test that invalid input raises appropriate errors."""
        with pytest.raises(ValueError) as excinfo:
            search_flights(
                origin='INVALID',  # Invalid airport code
                destination='SDU',
                departure_date='2024-04-15',
                passengers=1
            )
        assert 'Invalid input parameters' in str(excinfo.value)
