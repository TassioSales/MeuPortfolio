"""Nexus TUI — AI Agent Terminal."""
from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static
from textual import work

from rich.markdown import Markdown

from ..core.agent import Agent
from ..core.events import AgentEvent, EventType
from ..core.llm import MistralClient
from ..core.memory import Memory
from ..core.tools import TOOLS_SCHEMA, execute_tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_tool_executor(name: str, args: dict) -> str:
    """Synchronous wrapper around the async execute_tool.

    Agent.run() calls this inside a thread-pool executor, so there is no
    running event loop in the calling thread — we can safely create one.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(execute_tool(name, args))
    finally:
        loop.close()


def _format_args(args: dict) -> str:
    """Format tool arguments as 'key: "value"' pairs, truncating long values."""
    if not args:
        return "(sem argumentos)"
    parts: list[str] = []
    for key, value in args.items():
        str_value = str(value)
        if len(str_value) > 60:
            str_value = str_value[:57] + "..."
        parts.append(f'{key}: "{str_value}"')
    return "  ".join(parts)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class NexusApp(App):
    """Nexus — AI Agent Terminal com Textual."""

    CSS_PATH = "styles.tcss"
    TITLE = "NEXUS ◈ AI Agent Terminal"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Sair"),
        Binding("ctrl+n", "new_session", "Nova Sessão"),
        Binding("ctrl+l", "clear_chat", "Limpar Chat"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.memory: Memory
        self.llm: MistralClient
        self.agent: Agent
        self.session_id: int = 0
        self.is_thinking: bool = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("📋 SESSÕES", id="sidebar-title")
                yield ListView(id="session-list")
                yield Button("＋ Nova Sessão", id="new-session-btn", variant="default")
            with Vertical(id="main-area"):
                yield ScrollableContainer(id="chat-container")
                yield Label(
                    "🔧 web_search  python_repl  read_file  write_file  list_directory  fetch_url",
                    id="tools-bar",
                )
                with Horizontal(id="input-area"):
                    yield Input(
                        placeholder="💬 Mensagem para o Nexus... (Enter para enviar)",
                        id="message-input",
                    )
                    yield Button("Enviar", id="send-button")
        yield Footer()

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Initialize core components and create the first session."""
        self.memory = Memory()
        self.llm = MistralClient()
        self.agent = Agent(
            llm=self.llm,
            memory=self.memory,
            tools_schema=TOOLS_SCHEMA,
            tool_executor=_sync_tool_executor,
        )

        # Show API key warning if not configured.
        if not self.llm.is_configured:
            self._append_to_chat(
                "⚠️  **MISTRAL_API_KEY não está configurada.**\n\n"
                "Defina a variável de ambiente `MISTRAL_API_KEY` e reinicie o Nexus:\n\n"
                "```bash\nexport MISTRAL_API_KEY='sua-chave-aqui'\nnexus\n```",
                "msg-error",
            )

        self.session_id = self.memory.create_session("Nova Sessão")
        self._refresh_sessions()
        self._add_welcome_message()
        self.query_one("#message-input", Input).focus()

    # ------------------------------------------------------------------
    # Welcome message
    # ------------------------------------------------------------------

    def _add_welcome_message(self) -> None:
        content = (
            "🤖 **Nexus está pronto!**\n"
            "Sou seu assistente IA com acesso a ferramentas reais:\n"
            "• 🔍 Busca na web (DuckDuckGo)\n"
            "• 🐍 Execução de Python\n"
            "• 📁 Leitura e escrita de arquivos\n"
            "• 🌐 Fetch de URLs\n\n"
            "Digite sua pergunta ou tarefa abaixo."
        )
        self._append_to_chat(content, "msg-assistant")

    # ------------------------------------------------------------------
    # Chat helpers
    # ------------------------------------------------------------------

    def _append_to_chat(self, content: str, css_class: str = "msg-assistant") -> None:
        """Mount a Static widget into the chat container and scroll to bottom."""
        widget = Static(content, classes=css_class)
        self.query_one("#chat-container", ScrollableContainer).mount(widget)
        self.query_one("#chat-container", ScrollableContainer).scroll_end(animate=False)

    def _append_raw(self, widget: Widget) -> None:
        """Mount an arbitrary widget into the chat container and scroll to bottom."""
        self.query_one("#chat-container", ScrollableContainer).mount(widget)
        self.query_one("#chat-container", ScrollableContainer).scroll_end(animate=False)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the message input."""
        if event.input.id == "message-input":
            text = event.value.strip()
            event.input.value = ""
            if not text or self.is_thinking:
                return
            self._send_message(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "send-button":
            input_widget = self.query_one("#message-input", Input)
            text = input_widget.value.strip()
            input_widget.value = ""
            if not text or self.is_thinking:
                return
            self._send_message(text)
        elif event.button.id == "new-session-btn":
            self.action_new_session()

    # ------------------------------------------------------------------
    # Agent worker
    # ------------------------------------------------------------------

    @work(exclusive=False)
    async def _send_message(self, text: str) -> None:
        """Run the agent loop and stream results into the chat."""
        # Show the user's message immediately.
        self._append_to_chat(f"**👤 Você:** {text}", "msg-user")

        self.is_thinking = True

        # Placeholder widgets that will be updated as tokens and tools arrive.
        resp_widget = Static("", classes="msg-assistant")
        self._append_raw(resp_widget)

        status = Static("🤔 *Nexus está pensando...*", classes="msg-assistant status-thinking")
        self._append_raw(status)

        accumulated: str = ""
        tool_widget: Static | None = None
        status_removed = False

        try:
            async for event in self.agent.run(text, self.session_id):
                if event.type == EventType.TOKEN:
                    accumulated += event.data
                    resp_widget.update(Markdown("**🤖 Nexus:** " + accumulated))
                    self.query_one("#chat-container", ScrollableContainer).scroll_end(animate=False)

                elif event.type == EventType.TOOL_START:
                    # Remove the "thinking" status before showing tool activity.
                    if not status_removed:
                        try:
                            status.remove()
                        except Exception:
                            pass
                        status_removed = True

                    tool_widget = Static(
                        f"╭─ 🔧 **{event.tool_name}** ─╮\n"
                        f"│ {_format_args(event.tool_args)}\n"
                        f"│ ⏳ executando...",
                        classes="msg-tool",
                    )
                    self._append_raw(tool_widget)

                elif event.type == EventType.TOOL_END:
                    if tool_widget is not None:
                        tool_widget.update(
                            f"╭─ 🔧 **{event.tool_name}** ({event.duration_ms:.0f}ms) ─╮\n"
                            f"│ {_format_args(event.tool_args)}\n"
                            f"│ ✓ concluído\n"
                            f"╰──"
                        )
                    # Show a truncated preview of the tool result.
                    if event.data:
                        preview = event.data if len(event.data) <= 300 else event.data[:300] + "..."
                        result_widget = Static(preview, classes="msg-tool tool-result")
                        self._append_raw(result_widget)
                    tool_widget = None

                elif event.type == EventType.TOOL_ERROR:
                    if tool_widget is not None:
                        tool_widget.update(
                            f"╭─ 🔧 **{event.tool_name}** ({event.duration_ms:.0f}ms) ─╮\n"
                            f"│ {_format_args(event.tool_args)}\n"
                            f"│ ❌ {event.error}\n"
                            f"╰──"
                        )
                    tool_widget = None

                elif event.type == EventType.DONE:
                    if not status_removed:
                        try:
                            status.remove()
                        except Exception:
                            pass
                        status_removed = True
                    self.is_thinking = False

                elif event.type == EventType.ERROR:
                    if not status_removed:
                        try:
                            status.remove()
                        except Exception:
                            pass
                        status_removed = True
                    self._append_to_chat(f"❌ {event.error}", "msg-error")
                    self.is_thinking = False

        except Exception as exc:
            if not status_removed:
                try:
                    status.remove()
                except Exception:
                    pass
            self._append_to_chat(f"❌ Erro inesperado: {exc}", "msg-error")
            self.is_thinking = False

        # Update session title with first words of the user's message.
        if text:
            self.memory.update_session_title(self.session_id, text[:40])
            self._refresh_sessions()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _refresh_sessions(self) -> None:
        """Reload the session list in the sidebar."""
        sessions = self.memory.get_sessions()
        session_list = self.query_one("#session-list", ListView)

        # Clear existing items.
        for child in list(session_list.children):
            child.remove()

        for s in sessions:
            indicator = "●" if s["id"] == self.session_id else "○"
            label_text = f"{indicator} {s['title'][:25]}"
            item = ListItem(Label(label_text), id=f"session-{s['id']}")
            if s["id"] == self.session_id:
                item.add_class("active")
            session_list.mount(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Switch to the selected session."""
        item = event.item
        if item.id and item.id.startswith("session-"):
            try:
                session_id = int(item.id.split("-", 1)[1])
            except (ValueError, IndexError):
                return

            self.session_id = session_id
            self._refresh_sessions()
            self._load_session_history(session_id)

    def _load_session_history(self, session_id: int) -> None:
        """Clear the chat pane and replay stored messages for a session."""
        chat = self.query_one("#chat-container", ScrollableContainer)
        for child in list(chat.children):
            child.remove()

        messages = self.memory.get_messages(session_id)
        if not messages:
            self._add_welcome_message()
            return

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content") or ""

            if role == "user" and content:
                self._append_to_chat(f"**👤 Você:** {content}", "msg-user")
            elif role == "assistant" and content:
                self._append_to_chat(f"**🤖 Nexus:** {content}", "msg-assistant")
            elif role == "tool" and content:
                tool_name = msg.get("name", "ferramenta")
                preview = content if len(content) <= 300 else content[:300] + "..."
                self._append_to_chat(
                    f"╭─ 🔧 **{tool_name}** ─╮\n│ ✓ {preview}\n╰──",
                    "msg-tool",
                )
            # Assistant messages with only tool_calls (no text content) are skipped.

    # ------------------------------------------------------------------
    # Actions (key bindings)
    # ------------------------------------------------------------------

    def action_new_session(self) -> None:
        """Create a brand-new session and reset the chat."""
        self.session_id = self.memory.create_session("Nova Sessão")
        chat = self.query_one("#chat-container", ScrollableContainer)
        for child in list(chat.children):
            child.remove()
        self._add_welcome_message()
        self._refresh_sessions()
        self.query_one("#message-input", Input).focus()

    def action_clear_chat(self) -> None:
        """Clear the chat visually and delete messages from the database."""
        self.memory.clear_session(self.session_id)
        chat = self.query_one("#chat-container", ScrollableContainer)
        for child in list(chat.children):
            child.remove()
        self._add_welcome_message()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = NexusApp()
    app.run()
