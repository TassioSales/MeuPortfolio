import os
import sys
import webbrowser
from threading import Timer
from waitress import serve
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

def open_browser():
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
    print("Starting server at http://127.0.0.1:8080/")
    Timer(1.5, open_browser).start()
    
    application = get_wsgi_application()
    serve(application, host='127.0.0.1', port=8080)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nCRITICAL ERROR: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
