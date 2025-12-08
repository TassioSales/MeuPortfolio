import zipfile
import os
from datetime import datetime

def create_backup():
    project_dir = os.getcwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_finance_project_{timestamp}.zip"
    
    # Folders and files to exclude
    EXCLUDE_DIRS = {'venv', '__pycache__', 'dist', 'build', '.git', '.gemini', 'logs', 'staticfiles'}
    EXCLUDE_FILES = {backup_filename, 'db.sqlite3-journal'}
    EXCLUDE_EXTENSIONS = {'.pyc', '.spec', '.exe'}

    print(f"Creating backup: {backup_filename}...")
    
    with zipfile.ZipFile(backup_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                if any(file.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_dir)
                zipf.write(file_path, arcname)
                
    print(f"Backup created successfully: {backup_filename}")

if __name__ == "__main__":
    create_backup()
