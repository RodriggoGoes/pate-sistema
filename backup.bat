@echo off
set BACKUP_DIR=C:\backup_pate
set DATA_DIR=C:\sistema-pacientes\backup

if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%
if not exist %DATA_DIR% mkdir %DATA_DIR%

echo ========================================
echo    Realizando Backup do Banco de Dados
echo ========================================
echo.

REM Backup do MongoDB
mongodump --db pate_santarem --out %BACKUP_DIR%\backup_%date:~6,4%%date:~3,2%%date:~0,2%

echo.
echo ✅ Backup concluído em: %BACKUP_DIR%
pause