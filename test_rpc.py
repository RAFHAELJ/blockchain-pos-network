"""
Teste JSON-RPC 2.0 - padrao Ethereum.
Rode primeiro: python rpc_server.py --port 8545 --node node-SP
Depois:        python test_rpc.py
"""

import requests
import json

URL = "http://localhost:8545"
REQ_ID = 0


def rpc(method, params=None):
    global REQ_ID
    REQ_ID += 1
    body = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": REQ_ID}

    print(f"\n>>> {method}")
    print(f"    Request:  {json.dumps(body)[:120]}...")

    r = requests.post(URL, json=body)
    resp = r.json()

    if "error" in resp:
        print(f"    ERROR:    {resp['error']['message']}")
    else:
        result = resp.get("result", "")
        display = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        if len(display) > 150:
            display = display[:150] + "..."
        print(f"    Result:   {display}")

    return resp.get("result")


def sep(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def main():
    sep("JSON-RPC 2.0 - TESTE COMPLETO")

    # --- Info ---
    sep("1. INFO DA REDE")
    rpc("web3_clientVersion")
    rpc("eth_chainId")
    rpc("net_version")
    rpc("net_peerCount")
    rpc("net_listening")
    rpc("eth_syncing")
    rpc("eth_blockNumber")

    # --- Carteiras ---
    sep("2. CRIAR CARTEIRAS")
    w1 = rpc("pos_createWallet", [{"name": "Alice", "balance": 500}])
    w2 = rpc("pos_createWallet", [{"name": "Bob", "balance": 300}])
    w3 = rpc("pos_createWallet", [{"name": "Carol", "balance": 150}])
    w4 = rpc("pos_createWallet", [{"name": "Dave", "balance": 80}])

    alice = w1["address"]
    bob = w2["address"]
    carol = w3["address"]
    dave = w4["address"]

    # --- Contas ---
    sep("3. CONSULTAR CONTAS")
    rpc("eth_accounts")
    rpc("eth_getBalance", [alice, "latest"])

    # --- Staking ---
    sep("4. STAKING")
    rpc("pos_stake", [{"address": alice, "amount": 200}])
    rpc("pos_stake", [{"address": bob, "amount": 100}])
    rpc("pos_stake", [{"address": carol, "amount": 50}])
    rpc("pos_getValidators")

    # --- Transacoes ---
    sep("5. TRANSACOES (eth_sendTransaction)")
    rpc("eth_sendTransaction", [{"from": alice, "to": dave, "value": 30, "tip": 0.5}])
    rpc("eth_sendTransaction", [{"from": bob, "to": carol, "value": 20, "tip": 0.3}])
    rpc("eth_sendTransaction", [{"from": carol, "to": alice, "value": 10, "tip": 0.1}])

    rpc("eth_gasPrice")
    rpc("pos_getMempool")

    # --- Produzir blocos ---
    sep("6. PRODUZIR BLOCOS (pos_produceBlock)")
    rpc("pos_produceBlock")
    rpc("pos_produceBlock")

    rpc("eth_blockNumber")

    # --- Consultar bloco ---
    sep("7. CONSULTAR BLOCO (eth_getBlockByNumber)")
    rpc("eth_getBlockByNumber", ["0x1", True])

    # --- Smart Contracts ---
    sep("8. SMART CONTRACTS")

    rpc("pos_deployContract", [{"creator": alice, "id": "CofenToken", "type": "token",
                                 "state": {"name": "CofenToken", "symbol": "CFN"}}])
    rpc("pos_callContract", [{"caller": alice, "id": "CofenToken",
                               "params": {"action": "mint", "amount": 10000, "to": alice}}])
    rpc("pos_callContract", [{"caller": alice, "id": "CofenToken",
                               "params": {"action": "transfer", "to": bob, "amount": 500}}])
    rpc("pos_callContract", [{"caller": bob, "id": "CofenToken",
                               "params": {"action": "balance_of"}}])

    # NFT
    rpc("pos_deployContract", [{"creator": alice, "id": "CofenNFT", "type": "nft"}])
    rpc("pos_callContract", [{"caller": alice, "id": "CofenNFT",
                               "params": {"action": "mint", "metadata": {"name": "Art #1"}}}])

    # Votacao
    rpc("pos_deployContract", [{"creator": alice, "id": "Votacao", "type": "voting"}])
    rpc("pos_callContract", [{"caller": alice, "id": "Votacao",
                               "params": {"action": "create_proposal", "id": "P1", "description": "Aumentar reward"}}])
    rpc("pos_callContract", [{"caller": alice, "id": "Votacao",
                               "params": {"action": "vote", "id": "P1"}}])
    rpc("pos_callContract", [{"caller": bob, "id": "Votacao",
                               "params": {"action": "vote", "id": "P1"}}])
    rpc("pos_callContract", [{"caller": alice, "id": "Votacao",
                               "params": {"action": "results"}}])

    rpc("pos_produceBlock")
    rpc("pos_getContracts")

    # --- Slashing ---
    sep("9. SLASHING")
    rpc("pos_slash", [{"address": carol, "reason": "double voting"}])
    rpc("pos_getValidators")

    # --- Stats ---
    sep("10. ESTADO FINAL")
    rpc("eth_accounts")
    rpc("eth_blockNumber")
    rpc("pos_getStats")
    rpc("pos_validate")

    # --- Salvar ---
    rpc("pos_save")

    # --- Batch request ---
    sep("11. BATCH REQUEST (multiplas chamadas)")
    batch = [
        {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 100},
        {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 101},
        {"jsonrpc": "2.0", "method": "net_version", "params": [], "id": 102},
    ]
    print(f"\n>>> BATCH (3 chamadas)")
    r = requests.post(URL, json=batch)
    for resp in r.json():
        print(f"    id={resp['id']}: {resp.get('result', resp.get('error'))}")

    sep("TESTE JSON-RPC CONCLUIDO!")


if __name__ == "__main__":
    main()
