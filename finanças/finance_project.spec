# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Hidden imports for Django and other libraries
hidden_imports = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    'whitenoise.middleware',
    'whitenoise.storage',
    'crispy_forms',
    'crispy_bootstrap5',
    'core',
    'core.apps',
    'finance_project',
    'waitress',
    'reportlab',
    'xhtml2pdf',
    'yfinance',
]

# Collect all submodules for complex packages
hidden_imports.extend(collect_submodules('django'))
hidden_imports.extend(collect_submodules('reportlab'))
hidden_imports.extend(collect_submodules('xhtml2pdf'))

# Data files (templates, static, etc.)
datas = [
    ('templates', 'templates'),
    ('staticfiles', 'static'),
    ('db.sqlite3', '.'),  # Include the database if it exists
]

# Add any other data files needed by packages
datas.extend(collect_data_files('reportlab'))
datas.extend(collect_data_files('xhtml2pdf'))
datas.extend(collect_data_files('crispy_bootstrap5'))


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='finance_project',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements=None,
)
