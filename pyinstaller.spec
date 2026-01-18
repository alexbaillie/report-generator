# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['backend/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'pydantic.json',
        'pydantic.v1',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.ext.asyncio',
        'email_validator',
        'passlib.handlers.pbkdf2',
        'email.mime.text',
        'email.mime.multipart',
        'email.mime.application',
        'email.mime.base',
        'email.mime.nonmultipart',
        'email.encoders',
        'PyPDF2',
        'docx',
        'pdfplumber',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add data files - only include directories that exist
import os

# Helper function to safely add directory if it exists
def add_dir_if_exists(analysis, source, target):
    if os.path.exists(source) and os.path.isdir(source):
        analysis.datas += Tree(source, prefix=target)

# Add existing directories
add_dir_if_exists(a, 'backend/data', 'data')
add_dir_if_exists(a, 'backend/ollama_models', 'ollama_models')

# Add any additional files needed by your application
# a.binaries += [('path/to/file', 'path/in/bundle', 'DATA')]

# Ensure the database file is included
#a.datas += [('backend/database/*.db', '.', 'DATA')]
a.datas += Tree('backend/database', prefix='backend/database')

# Handle hidden imports for SQLAlchemy
a.hiddenimports.extend([
    'sqlalchemy.ext.asyncio',
    'sqlalchemy.dialects.sqlite',
    'aiosqlite',
])

# Handle hidden imports for FastAPI/Starlette
a.hiddenimports.extend([
    'starlette.middleware.cors',
    'starlette.responses',
    'starlette.requests',
    'starlette.staticfiles',
])

# Handle hidden imports for uvicorn
a.hiddenimports.extend([
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.auto',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
])

# Handle hidden imports for Python standard library
a.hiddenimports.extend([
    'email.mime.multipart',
    'email.mime.text',
    'email.mime.application',
    'email.mime.base',
    'email.mime.nonmultipart',
    'email.encoders',
])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='report_generator_backend',
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
    entitlements_file=None,
    icon=None,
)
