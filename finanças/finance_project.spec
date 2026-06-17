# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Patrimônio — Personal Finance ERP
Build: pyinstaller finance_project.spec --noconfirm
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

# ── Hidden imports ─────────────────────────────────────────────────────────────
hidden_imports = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.template.loaders.filesystem",
    "django.template.loaders.app_directories",
    "django.template.defaulttags",
    "django.template.defaultfilters",

    # Our app — all view sub-modules must be explicit
    "core",
    "core.apps",
    "core.models",
    "core.forms",
    "core.services",
    "core.market_data",
    "core.admin",
    "core.views",
    "core.views_dashboard",
    "core.views_transactions",
    "core.views_categories",
    "core.views_budgets",
    "core.views_reports",
    "core.views_investments",
    "core.views_goals",
    "core.views_loans",
    "core.views_accounts",
    "core.views_audit",
    "core.views_cashflow",
    "core.views_ofx",
    "core.views_shared",
    "core.templatetags",
    "core.templatetags.core_extras",

    # Project settings / urls / wsgi
    "finance_project",
    "finance_project.settings",
    "finance_project.urls",
    "finance_project.wsgi",

    # Third-party
    "whitenoise",
    "whitenoise.middleware",
    "whitenoise.storage",
    "crispy_forms",
    "crispy_bootstrap5",
    "waitress",
    "loguru",
    "decouple",
    "reportlab",
    "xhtml2pdf",
    "yfinance",
    "openpyxl",

    # DB backends
    "django.db.backends.sqlite3",
    "_sqlite3",
]

# Collect all sub-packages of complex libraries
hidden_imports += collect_submodules("django")
hidden_imports += collect_submodules("reportlab")
hidden_imports += collect_submodules("xhtml2pdf")
hidden_imports += collect_submodules("yfinance")
hidden_imports += collect_submodules("waitress")
hidden_imports += collect_submodules("crispy_forms")
hidden_imports += collect_submodules("crispy_bootstrap5")

# numpy and pandas require collect_all to include compiled C extensions (.pyd binaries)
_numpy_datas, _numpy_binaries, _numpy_hidden = collect_all("numpy")
_pandas_datas, _pandas_binaries, _pandas_hidden = collect_all("pandas")
hidden_imports += _numpy_hidden
hidden_imports += _pandas_hidden

# ── Data files ─────────────────────────────────────────────────────────────────
# Format: (source_path, dest_inside_bundle)
# Note: staticfiles/ must be collected BEFORE build with: manage.py collectstatic
datas = [
    ("templates",    "templates"),
    ("staticfiles",  "staticfiles"),   # must match STATIC_ROOT = BASE_DIR/'staticfiles'
    ("core/migrations", "core/migrations"),
]

datas += collect_data_files("reportlab")
datas += collect_data_files("xhtml2pdf")
datas += collect_data_files("crispy_bootstrap5")
datas += collect_data_files("loguru")
datas += _numpy_datas
datas += _pandas_datas

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    ["run_app.py"],
    pathex=[],
    binaries=_numpy_binaries + _pandas_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
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
    name="Patrimonio",          # output: dist/Patrimonio.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,               # keep True so errors are visible; set False for silent launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                  # add an .ico file path here if you have one
)
