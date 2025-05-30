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
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
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
    
    def create_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
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
    
    def _create_linear_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Cria um modelo de regressão linear."""
        model = Sequential([
            tf.keras.layers.Flatten(input_shape=input_shape),
            Dense(self.forecast_days)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def _create_random_forest_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Cria um modelo de Random Forest."""
        # O RandomForestRegressor do scikit-learn não é um modelo Keras
        # Portanto, usamos uma camada personalizada para encapsulá-lo
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
    
    def _create_lstm_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Cria um modelo LSTM."""
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
            if len(X.shape) == 2:
                X = X.reshape((X.shape[0], X.shape[1], 1))
            
            # Cria o modelo
            self.model = self.create_model((X.shape[1], X.shape[2]))
            
            # Treina o modelo
            if self.model_type == 'random_forest':
                # Para Random Forest, usamos o método fit personalizado
                self.model.fit(X, y)
                history = {'loss': [0], 'val_loss': [0]}  # Placeholder
            else:
                # Para outros modelos, usamos o método fit padrão do Keras
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
        if not self.is_trained or self.model is None:
            raise RuntimeError("O modelo não foi treinado. Chame o método train() primeiro.")
        
        try:
            # Redimensiona os dados para o formato esperado pelo modelo
            if len(X.shape) == 2:
                X = X.reshape((X.shape[0], X.shape[1], 1))
            
            # Faz as previsões
            predictions = self.model.predict(X)
            
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
            future_dates = [last_date + timedelta(days=i+1) for i in range(self.forecast_days)]
            
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

# Exemplo de uso:
if __name__ == "__main__":
    # Exemplo de dados históricos (substitua por dados reais)
    historical_data = [
        {'timestamp': '2023-01-01', 'close': 100},
        {'timestamp': '2023-01-02', 'close': 102},
        # ... mais dados históricos ...
    ]
    
    # Cria uma instância do analisador preditivo
    analyzer = AnalisePred(model_type='lstm', look_back=30, forecast_days=7)
    
    # Executa a previsão
    try:
        results = analyzer.forecast(historical_data)
        print(f"Previsões para os próximos {analyzer.forecast_days} dias:")
        for pred in results['predictions']:
            print(f"{pred['date']}: {pred['predicted_price']:.2f}")
        print(f"\nMétricas de desempenho: {results['metrics']}")
    except Exception as e:
        print(f"Erro ao executar previsão: {str(e)}")
