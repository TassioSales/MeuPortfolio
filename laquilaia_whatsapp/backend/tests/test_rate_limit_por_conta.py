"""
O limite de uso é por conta, não do processo.

Antes havia contadores únicos no LLMService: um usuário sozinho esgotava a
cota de todos os outros, e bastava um agente movimentado para o serviço
recusar as chamadas de qualquer outro cliente.
"""

import pytest

from app.services.llm_service import LLMService
from app.utils.exceptions import ValidationException


class TestBucketsPorConta:
    def test_uso_de_um_usuario_nao_conta_para_outro(self):
        service = LLMService()

        service._track_usage(100, "user-a")
        service._track_usage(100, "user-a")

        assert service.get_rate_limit_status("user-a")["calls_used"] == 2
        assert service.get_rate_limit_status("user-b")["calls_used"] == 0

    def test_limite_estourado_por_um_nao_bloqueia_o_outro(self):
        service = LLMService()
        service.max_calls_per_minute = 2

        service._track_usage(10, "user-a")
        service._track_usage(10, "user-a")

        with pytest.raises(ValidationException):
            service._check_rate_limits("user-a")

        # O ponto da mudança: o segundo usuário segue atendido.
        service._check_rate_limits("user-b")

    def test_tokens_tambem_sao_contados_por_conta(self):
        service = LLMService()
        service.max_tokens_per_minute = 1000

        service._track_usage(900, "user-a")
        service._track_usage(200, "user-a")

        with pytest.raises(ValidationException):
            service._check_rate_limits("user-a")

        assert service.get_rate_limit_status("user-b")["tokens_used"] == 0

    def test_sem_usuario_usa_o_balde_compartilhado(self):
        service = LLMService()

        service._track_usage(50)

        assert service.get_rate_limit_status()["calls_used"] == 1
        # Não vaza para a conta de ninguém.
        assert service.get_rate_limit_status("user-a")["calls_used"] == 0

    def test_status_reporta_o_restante_da_conta(self):
        service = LLMService()
        service.max_calls_per_minute = 10

        service._track_usage(10, "user-a")

        status = service.get_rate_limit_status("user-a")
        assert status["calls_remaining"] == 9
        assert status["tokens_used"] == 10
