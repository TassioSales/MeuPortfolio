"""
Módulo stub para substituir o TensorFlow quando não estiver disponível.
"""

class Sequential:
    """Classe stub para substituir tensorflow.keras.models.Sequential"""
    def __init__(self, *args, **kwargs):
        pass
    
    def add(self, layer):
        pass
    
    def compile(self, *args, **kwargs):
        pass
    
    def fit(self, *args, **kwargs):
        pass
    
    def predict(self, *args, **kwargs):
        return None

class LSTM:
    """Classe stub para substituir tensorflow.keras.layers.LSTM"""
    def __init__(self, *args, **kwargs):
        pass

class Dense:
    """Classe stub para substituir tensorflow.keras.layers.Dense"""
    def __init__(self, *args, **kwargs):
        pass

class Dropout:
    """Classe stub para substituir tensorflow.keras.layers.Dropout"""
    def __init__(self, *args, **kwargs):
        pass

class Flatten:
    """Classe stub para substituir tensorflow.keras.layers.Flatten"""
    def __init__(self, *args, **kwargs):
        pass
