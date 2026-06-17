"""
Entry point for the PyInstaller-packaged Windows executable.
Starts a Waitress WSGI server and opens the browser automatically.
"""
import os
import sys
import socket
import webbrowser
from pathlib import Path
from threading import Timer


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_browser():
    webbrowser.open_new("http://127.0.0.1:8080/")


def main():
    # ── Path setup ────────────────────────────────────────────────────────────
    # sys._MEIPASS is the PyInstaller extraction dir (read-only temp folder).
    # All writable data (DB, logs) must live beside the .exe.
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        data_dir = Path(sys.executable).parent
    else:
        bundle_dir = Path(__file__).resolve().parent
        data_dir = bundle_dir

    # Add bundle dir first so Django can find its modules
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))

    # ── Environment variables (must be set BEFORE django.setup()) ─────────────
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_project.settings")

    # Point the SQLite database to a writable location beside the exe
    db_path = data_dir / "patrimonio.db"
    os.environ.setdefault("SQLITE_DB_PATH", str(db_path))

    # ── Django bootstrap ──────────────────────────────────────────────────────
    import django
    django.setup()

    from django.core.management import call_command

    print("Verificando banco de dados...")
    try:
        call_command("migrate", verbosity=0)
    except Exception as exc:
        print(f"Aviso ao migrar: {exc}")

    # ── Start server ──────────────────────────────────────────────────────────
    local_ip = get_local_ip()
    border = "=" * 52
    print(f"\n{border}")
    print("   PATRIMÔNIO — Sistema Financeiro Pessoal")
    print(border)
    print(f"   Local  →  http://127.0.0.1:8080/")
    if local_ip != "127.0.0.1":
        print(f"   Rede   →  http://{local_ip}:8080/")
    print(f"   Banco  →  {db_path}")
    print(f"{border}\n")

    Timer(1.5, open_browser).start()

    from waitress import serve
    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()
    serve(application, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"\nERRO CRÍTICO: {exc}")
        input("Pressione Enter para sair...")
        sys.exit(1)
