#!/bin/bash
echo "============================================"
echo "  Subindo 3 nos JSON-RPC na rede local"
echo "============================================"
echo ""

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Iniciando Node SP (porta 8545)..."
python3 "$DIR/rpc_server.py" --port 8545 --node node-SP --peer http://localhost:8546 --peer http://localhost:8547 &
PID1=$!
sleep 2

echo "Iniciando Node RJ (porta 8546)..."
python3 "$DIR/rpc_server.py" --port 8546 --node node-RJ --peer http://localhost:8545 --peer http://localhost:8547 &
PID2=$!
sleep 2

echo "Iniciando Node MG (porta 8547)..."
python3 "$DIR/rpc_server.py" --port 8547 --node node-MG --peer http://localhost:8545 --peer http://localhost:8546 &
PID3=$!

echo ""
echo "============================================"
echo "  3 nos JSON-RPC rodando:"
echo "    node-SP: http://localhost:8545 (PID: $PID1)"
echo "    node-RJ: http://localhost:8546 (PID: $PID2)"
echo "    node-MG: http://localhost:8547 (PID: $PID3)"
echo ""
echo "  Testar: python3 test_rpc.py"
echo "  Sync:   python3 check_nodes.py"
echo "  Parar:  kill $PID1 $PID2 $PID3"
echo "============================================"
echo ""
echo "Pressione Ctrl+C para parar todos os nos..."

trap "kill $PID1 $PID2 $PID3 2>/dev/null; echo 'Nos parados.'; exit 0" SIGINT SIGTERM
wait
