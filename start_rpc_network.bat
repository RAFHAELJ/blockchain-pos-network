@echo off
echo ============================================
echo   Subindo 3 nos JSON-RPC na rede local
echo ============================================
echo.

echo Iniciando Node SP (porta 8545)...
start "RPC-SP" cmd /k "cd /d %~dp0 && python rpc_server.py --port 8545 --node node-SP --peer http://localhost:8546 --peer http://localhost:8547"

timeout /t 2 >nul

echo Iniciando Node RJ (porta 8546)...
start "RPC-RJ" cmd /k "cd /d %~dp0 && python rpc_server.py --port 8546 --node node-RJ --peer http://localhost:8545 --peer http://localhost:8547"

timeout /t 2 >nul

echo Iniciando Node MG (porta 8547)...
start "RPC-MG" cmd /k "cd /d %~dp0 && python rpc_server.py --port 8547 --node node-MG --peer http://localhost:8545 --peer http://localhost:8546"

echo.
echo ============================================
echo   3 nos JSON-RPC rodando:
echo     node-SP: http://localhost:8545
echo     node-RJ: http://localhost:8546
echo     node-MG: http://localhost:8547
echo.
echo   Testar: python test_rpc.py
echo   Browser: http://localhost:8545
echo ============================================
pause
