"""
Módulo para análise preditiva de ativos financeiros.
Utiliza modelos de machine learning para prever preços futuros.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import sys
import warnings

# Tenta importar o TensorFlow, mas não falha se não estiver disponível
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    TENSORFLOW_AVAILABLE = True
except ImportError:
    warnings.warn("TensorFlow não está instalado. Usando implementação simulada.")
    from .tensorflow_stub import Sequential, LSTM, Dense, Dropout
    TENSORFLOW_AVAILABLE = False

from ..models.ativo import Ativo, HistoricoPreco
from .. import db
from ..utils.logger import logger

class AnalisePred:
    """Classe para análise preditiva de ativos financeiros."""
    
    def __init__(self, model_type: str = 'lstm', look_back: int = 30, forecast_days: int = 7):
        """
        Inicializa o serviço de análise preditiva.
        
        Args:
            model_type (str): Tipo de modelo a ser utilizado ('linear', 'random_forest', 'lstm').
            look_back (int): Número de dias anteriores a serem considerados para previsão.
            forecast_days (int): Número de dias a serem previstos.
        """
        self.model_type = model_type
        self.look_back = look_back
        self.forecast_days = forecast_days
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_trained = False
    
    def prepare_data(self, data: List[Dict], target_column: str = 'close') -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara os dados para treinamento do modelo.
        
        Args:
            data (List[Dict]): Lista de dicionários com os dados históricos.
            target_column (str): Nome da coluna alvo (padrão: 'close').
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Dados de entrada (X) e saída (y) preparados.
        """
        try:
            # Converte para DataFrame
            df = pd.DataFrame(data)
            
            # Ordena por data
            if 'timestamp' in df.columns:
                df = df.sort_values('timestamp')
            
            # Seleciona a coluna alvo
            dataset = df[target_column].values.reshape(-1, 1)
            
            # Normaliza os dados
            dataset = self.scaler.fit_transform(dataset)
            
            # Prepara os dados para treinamento
            X, y = [], []
            
            for i in range(len(dataset) - self.look_back - self.forecast_days + 1):
                X.append(dataset[i:(i + self.look_back), 0])
                y.append(dataset[(i + self.look_back):(i + self.look_back + self.forecast_days), 0])
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Erro ao preparar dados para análise preditiva: {str(e)}")
            raise
    
    def create_model(self, input_shape: Tuple[int, int]):
        """
        Cria o modelo de machine learning.
        
        Args:
            input_shape (Tuple[int, int]): Formato dos dados de entrada.
            
        Returns:
            tf.keras.Model: Modelo de machine learning.
        """
        try:
            if self.model_type == 'linear':
                return self._create_linear_model(input_shape)
            elif self.model_type == 'random_forest':
                return self._create_random_forest_model(input_shape)
            elif self.model_type == 'lstm':
                return self._create_lstm_model(input_shape)
            else:
                raise ValueError(f"Tipo de modelo não suportado: {self.model_type}")
        except Exception as e:
            logger.error(f"Erro ao criar modelo {self.model_type}: {str(e)}")
            raise
    
    def _create_linear_model(self, input_shape: Tuple[int, int]):
        """Cria um modelo de regressão linear."""
        if not TENSORFLOW_AVAILABLE:
            warnings.warn("TensorFlow não está disponível. Usando modelo linear simples.")
            return LinearRegression()
            
        model = Sequential()
        if TENSORFLOW_AVAILABLE:
            import tensorflow.keras.layers as layers
            model.add(layers.Flatten(input_shape=input_shape))
        else:
            from .tensorflow_stub import Flatten
            model.add(Flatten(input_shape=input_shape))
        model.add(Dense(self.forecast_days))
        
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def _create_random_forest_model(self, input_shape: Tuple[int, int]):
        """Cria um modelo de Random Forest."""
        if not TENSORFLOW_AVAILABLE:
            warnings.warn("TensorFlow não está disponível. Usando RandomForestRegressor diretamente.")
            return RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Se chegamos aqui, TENSORFLOW_AVAILABLE é True
        class RandomForestWrapper(tf.keras.Model):
            def __init__(self, input_shape, forecast_days):
                super(RandomForestWrapper, self).__init__()
                self.forest = RandomForestRegressor(n_estimators=100, random_state=42)
                self.flat = tf.keras.layers.Flatten(input_shape=input_shape)
                self.output_dim = forecast_days
            
            def call(self, inputs):
                # O RandomForest não suporta gradientes, então não pode ser treinado com backpropagation
                # Este é apenas um wrapper para compatibilidade
                return tf.py_function(
                    lambda x: self.forest.predict(x.numpy().reshape(-1, np.prod(input_shape))),
                    [inputs],
                    tf.float32
                )
            
            def fit(self, x, y, **kwargs):
                # Treina o RandomForest
                x_flat = x.numpy().reshape(x.shape[0], -1)
                self.forest.fit(x_flat, y.numpy())
                return self
        
        return RandomForestWrapper(input_shape, self.forecast_days)
    
    def _create_lstm_model(self, input_shape: Tuple[int, int]):
        """Cria um modelo LSTM."""
        if not TENSORFLOW_AVAILABLE:
            warnings.warn("TensorFlow não está disponível. Usando RandomForest como substituto para LSTM.")
            return RandomForestRegressor(n_estimators=100, random_state=42)
            
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(self.forecast_days)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 50, batch_size: int = 32, 
              validation_split: float = 0.1) -> Dict:
        """
        Treina o modelo com os dados fornecidos.
        
        Args:
            X (np.ndarray): Dados de entrada.
            y (np.ndarray): Dados de saída.
            epochs (int): Número de épocas de treinamento.
            batch_size (int): Tamanho do lote.
            validation_split (float): Proporção dos dados para validação.
            
        Returns:
            Dict: Histórico de treinamento.
        """
        try:
            # Redimensiona os dados para o formato esperado pelo modelo
            if len(X.shape) == 2 and TENSORFLOW_AVAILABLE:
                X = X.reshape((X.shape[0], X.shape[1], 1))
            
            # Cria o modelo
            input_shape = (X.shape[1], X.shape[2]) if TENSORFLOW_AVAILABLE else (X.shape[1],)
            self.model = self.create_model(input_shape)
            
            # Treina o modelo
            if not TENSORFLOW_AVAILABLE or self.model_type == 'random_forest':
                # Para modelos scikit-learn ou quando o TensorFlow não está disponível
                if len(X.shape) > 2:
                    X_flat = X.reshape(X.shape[0], -1)
                else:
                    X_flat = X
                
                if validation_split > 0:
                    from sklearn.model_selection import train_test_split
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_flat, y, test_size=validation_split, random_state=42
                    )
                    self.model.fit(X_train, y_train)
                    
                    # Calcula métricas de treino e validação
                    train_score = self.model.score(X_train, y_train)
                    val_score = self.model.score(X_val, y_val)
                    
                    history = {
                        'loss': [1 - train_score],
                        'val_loss': [1 - val_score]
                    }
                else:
                    self.model.fit(X_flat, y)
                    train_score = self.model.score(X_flat, y)
                    history = {
                        'loss': [1 - train_score],
                        'val_loss': [0]  # Placeholder
                    }
            else:
                # Para modelos Keras
                history = self.model.fit(
                    X, y,
                    epochs=epochs,
                    batch_size=batch_size,
                    validation_split=validation_split,
                    verbose=1
                ).history
            
            self.is_trained = True
            return history
            
        except Exception as e:
            logger.error(f"Erro ao treinar o modelo: {str(e)}")
            raise
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Faz previsões com o modelo treinado.
        
        Args:
            X (np.ndarray): Dados de entrada.
            
        Returns:
            np.ndarray: Previsões do modelo.
        """
        try:
            if not self.is_trained or self.model is None:
                raise ValueError("O modelo não foi treinado. Chame o método train() primeiro.")
                
            # Redimensiona os dados para o formato esperado pelo modelo
            if TENSORFLOW_AVAILABLE and len(X.shape) == 2:
                X = X.reshape((X.shape[0], X.shape[1], 1))
            
            # Para modelos scikit-learn, achata os dados se necessário
            if not TENSORFLOW_AVAILABLE or isinstance(self.model, (LinearRegression, RandomForestRegressor)):
                if len(X.shape) > 2:
                    X = X.reshape(X.shape[0], -1)
            
            # Faz as previsões
            predictions = self.model.predict(X)
            
            # Se for um modelo Keras, pode retornar um array aninhado
            if hasattr(predictions, 'numpy'):
                predictions = predictions.numpy()
            
            # Garante que as previsões tenham o formato esperado (n_samples, forecast_days)
            if len(predictions.shape) == 1:
                predictions = predictions.reshape(-1, 1)
                
            # Desfaz a normalização
            if hasattr(self, 'scaler'):
                # Cria um array temporário com o mesmo formato dos dados originais
                temp = np.zeros((len(predictions), 1))
                temp[:, 0] = predictions.flatten()
                predictions = self.scaler.inverse_transform(temp)[:, 0]
            
            return predictions
            
        except Exception as e:
            logger.error(f"Erro ao fazer previsões: {str(e)}")
            raise
    
    def evaluate(self, X: np.ndarray, y_true: np.ndarray) -> Dict[str, float]:
        """
        Avalia o desempenho do modelo.
        
        Args:
            X (np.ndarray): Dados de entrada.
            y_true (np.ndarray): Valores reais.
            
        Returns:
            Dict[str, float]: Métricas de avaliação (MSE, RMSE, MAE, R²).
        """
        try:
            y_pred = self.predict(X)
            
            # Se y_true for 2D (para previsão de múltiplos passos à frente),
            # calculamos as métricas para cada passo e tiramos a média
            if len(y_true.shape) > 1 and y_true.shape[1] > 1:
                mse = [mean_squared_error(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])]
                rmse = [np.sqrt(m) for m in mse]
                mae = [mean_absolute_error(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])]
                r2 = [r2_score(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])]
                
                return {
                    'mse': np.mean(mse),
                    'rmse': np.mean(rmse),
                    'mae': np.mean(mae),
                    'r2': np.mean(r2)
                }
            else:
                return {
                    'mse': mean_squared_error(y_true, y_pred),
                    'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
                    'mae': mean_absolute_error(y_true, y_pred),
                    'r2': r2_score(y_true, y_pred)
                }
                
        except Exception as e:
            logger.error(f"Erro ao avaliar o modelo: {str(e)}")
            raise
    
    def forecast(self, historical_data: List[Dict], target_column: str = 'close', 
                 epochs: int = 50, batch_size: int = 32) -> Dict:
        """
        Executa o pipeline completo de previsão.
        
        Args:
            historical_data (List[Dict]): Dados históricos do ativo.
            target_column (str): Nome da coluna alvo.
            epochs (int): Número de épocas de treinamento.
            batch_size (int): Tamanho do lote.
            
        Returns:
            Dict: Resultados da previsão, incluindo métricas e previsões.
        """
        try:
            # Prepara os dados
            X, y = self.prepare_data(historical_data, target_column)
            
            # Divide em conjuntos de treino e teste (80/20)
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # Treina o modelo
            history = self.train(X_train, y_train, epochs=epochs, batch_size=batch_size)
            
            # Avalia o modelo
            metrics = self.evaluate(X_test, y_test)
            
            # Faz previsões para os próximos dias
            last_window = X[-1:]
            future_predictions = []
            
            # Prepara a janela para previsão
            if not TENSORFLOW_AVAILABLE or isinstance(self.model, (LinearRegression, RandomForestRegressor)):
                # Para modelos scikit-learn, achatamos a janela
                last_window_flat = last_window.reshape(1, -1)
                
                # Fazemos previsões para todos os dias de uma vez
                future_predictions = self.model.predict(last_window_flat)[0]
                
                # Se o modelo retornar apenas um valor, repetimos para todos os dias
                if len(future_predictions) == 1:
                    future_predictions = [future_predictions[0]] * self.forecast_days
                    
                # Garantimos que temos o número correto de previsões
                future_predictions = future_predictions[:self.forecast_days]
            else:
                # Para modelos Keras, usamos a abordagem sequencial
                for _ in range(self.forecast_days):
                    # Faz a previsão para o próximo dia
                    next_pred = self.model.predict(last_window)
                    future_predictions.append(next_pred[0][0])
                    
                    # Atualiza a janela para incluir a previsão
                    last_window = np.roll(last_window, -1, axis=1)
                    last_window[0, -1, 0] = next_pred[0][0]
            
            # Desfaz a normalização das previsões futuras
            temp = np.zeros((len(future_predictions), 1))
            temp[:, 0] = future_predictions
            future_predictions = self.scaler.inverse_transform(temp)[:, 0]
            
            # Prepara as datas futuras
            last_date = pd.to_datetime(historical_data[-1]['timestamp'])
            future_dates = [last_date + timedelta(days=i+1) for i in range(len(future_predictions))]
            
            return {
                'model_type': self.model_type,
                'metrics': metrics,
                'predictions': [
                    {
                        'date': date.strftime('%Y-%m-%d'),
                        'predicted_price': float(price)
                    }
                    for date, price in zip(future_dates, future_predictions)
                ],
                'training_history': history
            }
        except Exception as e:
            logger.error(f"Erro ao executar previsão: {str(e)}")
            raise

def predict_prices(symbol: str, days: int = 7, model_type: str = 'lstm', look_back: int = 30) -> Dict:
    """
    Função de alto nível para prever preços futuros de um ativo.
    
    Args:
        symbol (str): Símbolo do ativo (ex: 'PETR4.SA', 'BTC-USD')
        days (int): Número de dias para prever (padrão: 7)
        model_type (str): Tipo de modelo a ser utilizado ('linear', 'random_forest', 'lstm')
        look_back (int): Número de dias anteriores a serem considerados (padrão: 30)
        
    Returns:
        Dict: Dicionário com as previsões e métricas de avaliação
    """
    try:
        # Obtém os dados históricos do ativo
        # Aqui você deve implementar a lógica para obter os dados históricos reais
        # Por exemplo, usando o YFinanceService ou outra fonte de dados
        
        # Exemplo de implementação simulada
        logger.warning("Usando dados simulados para previsão. Implemente a obtenção de dados reais.")
        
        # Cria uma instância do serviço de análise preditiva
        analise = AnalisePred(model_type=model_type, look_back=look_back, forecast_days=days)
        
        # Prepara os dados (substitua por dados reais)
        # X, y = analise.prepare_data(historical_data)
        
        # Treina o modelo (comente esta linha se estiver usando dados simulados)
        # analise.train(X, y)
        
        # Faz previsões (comente esta linha se estiver usando dados simulados)
        # predictions = analise.predict(X[-1:])
        
        # Retorno de exemplo com dados simulados
        return {
            'symbol': symbol,
            'predictions': [
                {'date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'), 
                 'price': 100 + i * 0.5}  # Exemplo de previsão linear
                for i in range(1, days + 1)
            ],
            'model_type': model_type,
            'look_back': look_back,
            'forecast_days': days,
            'metrics': {
                'mse': 0.0,  # Exemplo de métricas
                'mae': 0.0,
                'r2': 1.0
            },
            'warning': 'Dados simulados. Implemente a obtenção de dados reais.'
        }
        
    except Exception as e:
        logger.error(f"Erro ao prever preços para {symbol}: {str(e)}")
        return {
            'error': f'Erro ao prever preços: {str(e)}',
            'symbol': symbol
        }

# Exemplo de uso:
if __name__ == "__main__":
    # Exemplo de dados históricos (substitua por dados reais)
    historical_data = [
        {'timestamp': '2023-01-01', 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000},
        {'timestamp': '2023-01-02', 'open': 102, 'high': 108, 'low': 101, 'close': 105, 'volume': 1200},
        # Adicione mais dados históricos conforme necessário
    ]
    
    # Cria uma instância do serviço
    analise = AnalisePred(model_type='linear', look_back=5, forecast_days=3)
    
    # Prepara os dados
    X, y = analise.prepare_data(historical_data)
    
    # Treina o modelo
    analise.train(X, y)
    
    # Faz previsões
    predictions = analise.predict(X[-1:])
    print(f"Previsões: {predictions}")
    
    # Exemplo de uso da função predict_prices
    print("\nExemplo de uso da função predict_prices:")
    result = predict_prices("PETR4.SA", days=5)
    print(f"Previsões para {result['symbol']}:")
    for pred in result['predictions']:
        print(f"{pred['date']}: R$ {pred['price']:.2f}")
