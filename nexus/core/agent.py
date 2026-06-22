"""ReAct agent loop that orchestrates LLM calls and tool execution."""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Callable

from loguru import logger

from .events import AgentEvent, EventType
from .llm import MistralClient
from .memory import Memory


class Agent:
    """Orchestrates the ReAct loop: Reason → Act → Observe → repeat.

    Args:
        llm:           Configured :class:`MistralClient` instance.
        memory:        :class:`Memory` instance for persisting conversations.
        tools_schema:  List of Mistral-format tool definition dicts.
        tool_executor: Callable ``(tool_name: str, tool_args: dict) -> str``
                       that executes a named tool and returns its string result.
    """

    _MAX_ITERATIONS = 8

    def __init__(
        self,
        llm: MistralClient,
        memory: Memory,
        tools_schema: list[dict],
        tool_executor: Callable[[str, dict], str],
    ) -> None:
        self.llm = llm
        self.memory = memory
        self.tools_schema = tools_schema
        self.tool_executor = tool_executor

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(
        self, user_message: str, session_id: int
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run the ReAct loop for a single user turn.

        Yields :class:`AgentEvent` instances as the agent reasons and acts.
        """
        # Guard: API key must be configured before doing anything.
        if not self.llm.is_configured:
            yield AgentEvent(
                type=EventType.ERROR,
                error=(
                    "MISTRAL_API_KEY não está configurada. "
                    "Defina a variável de ambiente e reinicie o Nexus."
                ),
            )
            return

        # 1. Persist the user message.
        self.memory.add_user_message(session_id, user_message)
        logger.info("Nova mensagem do usuário na sessão {}", session_id)

        loop = asyncio.get_event_loop()

        # 2. ReAct loop — at most _MAX_ITERATIONS rounds.
        for iteration in range(self._MAX_ITERATIONS):
            logger.debug("Iteração ReAct {}/{}", iteration + 1, self._MAX_ITERATIONS)

            messages = self.memory.get_messages(session_id)

            # 2b. Call the LLM in a thread executor so we don't block the
            #     asyncio event loop while waiting for the HTTP response.
            try:
                response: dict = await loop.run_in_executor(
                    None, self.llm.chat, messages, self.tools_schema
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Erro ao chamar a API Mistral")
                yield AgentEvent(
                    type=EventType.ERROR,
                    error=f"Erro na API Mistral: {exc}",
                )
                return

            choice: dict = response.get("choices", [{}])[0]
            finish_reason: str = choice.get("finish_reason", "stop")
            message: dict = choice.get("message", {})

            # ----------------------------------------------------------
            # 2c. Tool call branch
            # ----------------------------------------------------------
            if finish_reason == "tool_calls":
                tool_calls: list[dict] = message.get("tool_calls", [])

                # Persist the assistant's intent (with tool_calls) so the
                # conversation history stays coherent for follow-up turns.
                self.memory.add_assistant_message(
                    session_id,
                    content=message.get("content") or "",
                    tool_calls=tool_calls,
                )

                for tool_call in tool_calls:
                    tool_id: str = tool_call.get("id", "")
                    function_info: dict = tool_call.get("function", {})
                    tool_name: str = function_info.get("name", "")
                    raw_args: Any = function_info.get("arguments", {})

                    # Arguments may arrive as a JSON string or as a dict.
                    if isinstance(raw_args, str):
                        import json as _json

                        try:
                            tool_args: dict = _json.loads(raw_args)
                        except Exception:  # noqa: BLE001
                            tool_args = {}
                    else:
                        tool_args = raw_args or {}

                    logger.info("Executando ferramenta '{}' args={}", tool_name, tool_args)
                    yield AgentEvent(
                        type=EventType.TOOL_START,
                        tool_name=tool_name,
                        tool_args=tool_args,
                    )

                    t_start = time.perf_counter()
                    try:
                        # Execute in thread executor so blocking tools don't
                        # stall the event loop.
                        tool_result: str = await loop.run_in_executor(
                            None, self.tool_executor, tool_name, tool_args
                        )
                        duration_ms = (time.perf_counter() - t_start) * 1_000

                        logger.debug(
                            "Ferramenta '{}' concluída em {:.1f} ms", tool_name, duration_ms
                        )
                        yield AgentEvent(
                            type=EventType.TOOL_END,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            data=tool_result,
                            duration_ms=duration_ms,
                        )

                    except Exception as exc:  # noqa: BLE001
                        duration_ms = (time.perf_counter() - t_start) * 1_000
                        error_msg = f"Erro na ferramenta '{tool_name}': {exc}"
                        logger.exception("Ferramenta '{}' falhou", tool_name)
                        tool_result = error_msg
                        yield AgentEvent(
                            type=EventType.TOOL_ERROR,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            error=error_msg,
                            duration_ms=duration_ms,
                        )

                    # Persist the tool result so the LLM can observe it.
                    self.memory.add_tool_result(
                        session_id,
                        tool_call_id=tool_id,
                        tool_name=tool_name,
                        content=tool_result,
                    )

                # Continue the loop so the LLM can reason about tool results.
                continue

            # ----------------------------------------------------------
            # 2d. Final answer branch (finish_reason == "stop")
            # ----------------------------------------------------------
            content: str = message.get("content") or ""

            # Typewriter effect — emit one character at a time.
            for char in content:
                yield AgentEvent(type=EventType.TOKEN, data=char)
                await asyncio.sleep(0.008)

            # Persist the full assistant response.
            self.memory.add_assistant_message(session_id, content=content)

            logger.info(
                "Resposta final gerada | sessão={} chars={}", session_id, len(content)
            )
            yield AgentEvent(type=EventType.DONE)
            return

        # Reached without a "stop" — the agent ran out of iterations.
        logger.warning(
            "Limite de iterações ({}) atingido na sessão {}",
            self._MAX_ITERATIONS,
            session_id,
        )
        yield AgentEvent(
            type=EventType.ERROR,
            error=(
                f"O agente atingiu o limite máximo de {self._MAX_ITERATIONS} iterações "
                "sem produzir uma resposta final. Tente reformular sua pergunta."
            ),
        )
