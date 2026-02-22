import os
import sys
import webbrowser
from threading import Timer
from waitress import serve
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

import socket

def get_local_ip():
    try:
        # Create a dummy socket to detect the preferred interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def open_browser():
    # Only open locally
    webbrowser.open_new("http://127.0.0.1:8080/")

def main():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
    
    # Ensure we are in the correct directory (for relative paths to work in exe)
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add base_dir to sys.path so we can import modules
    sys.path.append(base_dir)
    
    # Setup Django
    import django
    django.setup()

    # Run migrations to ensure DB exists and is up to date
    print("Checking database...")
    try:
        call_command('migrate')
    except Exception as e:
        print(f"Error running migrations: {e}")
        # Continue anyway, maybe DB is fine or it's a permission issue? 
        # But usually we want to stop. For now let's print and continue.

    # Collect static files (optional, but good if we want to serve them properly)
    # In a frozen app, we might want to rely on pre-collected static files or 
    # configure Whitenoise to serve them from a specific directory.
    # For simplicity with Whitenoise, we ensure STATIC_ROOT exists.
    
    # Start the server
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print(" SERVIDOR INICIADO COM SUCESSO")
    print("="*50)
    print(f" Acesso Local (PC):    http://127.0.0.1:8080/")
    if local_ip != "127.0.0.1":
        print(f" Acesso na Rede (Celular/Tablet): http://{local_ip}:8080/")
    print("="*50 + "\n")
    
    Timer(1.5, open_browser).start()
    
    application = get_wsgi_application()
    # Bind to 0.0.0.0 to allow external access (mobile)
    serve(application, host='0.0.0.0', port=8080)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nCRITICAL ERROR: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
