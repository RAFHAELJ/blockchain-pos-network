"""
Verifica se os 3 nos estao sincronizados e mostra info das carteiras.
Rode apos o test_rpc.py com os 3 nos rodando.

  python check_nodes.py
"""

import requests
import json

NODES = [
    ("node-SP", "http://localhost:8545"),
    ("node-RJ", "http://localhost:8546"),
    ("node-MG", "http://localhost:8547"),
]


def rpc(url, method, params=None):
    try:
        r = requests.post(url, json={
            "jsonrpc": "2.0", "method": method, "params": params or [], "id": 1
        }, timeout=3)
        return r.json().get("result")
    except Exception:
        return None


def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    sep("VERIFICACAO DOS NOS")

    # --- 1. Status de cada no ---
    sep("1. STATUS DE CADA NO")
    stats = {}
    for name, url in NODES:
        s = rpc(url, "pos_getStats")
        if s:
            stats[name] = s
            print(f"\n  [{name}] {url}")
            print(f"    Blocos:      {s['blocks']}")
            print(f"    Epoch:       {s['epoch']}")
            print(f"    Validadores: {s['validators']}")
            print(f"    Mempool:     {s['mempool']}")
            print(f"    Queimado:    {s['burned']}")
            print(f"    Supply:      {s['supply']}")
            print(f"    Finalizados: {s['finalized']}")
            print(f"    Historico:   {s['txHistory']} txns")
        else:
            print(f"\n  [{name}] {url} -- OFFLINE")

    # --- 2. Comparar blocos ---
    sep("2. COMPARACAO DE BLOCOS")
    block_counts = {}
    last_hashes = {}
    for name, url in NODES:
        bn = rpc(url, "eth_blockNumber")
        if bn is not None:
            count = int(bn, 16)
            block_counts[name] = count
            # pegar hash do ultimo bloco
            last_block = rpc(url, "eth_getBlockByNumber", [bn, False])
            if last_block:
                last_hashes[name] = last_block.get("hash", "?")
            print(f"  {name}: {count} blocos | ultimo hash: {last_hashes.get(name, '?')[:24]}...")

    if len(set(block_counts.values())) == 1 and len(set(last_hashes.values())) == 1:
        print(f"\n  RESULTADO: SINCRONIZADOS! Todos com {list(block_counts.values())[0]} blocos e mesmo hash")
    elif len(set(block_counts.values())) == 1:
        print(f"\n  RESULTADO: Mesmo numero de blocos mas HASHES DIFERENTES (cadeias divergiram)")
    else:
        print(f"\n  RESULTADO: DESSINCRONIZADOS! Blocos diferentes entre nos")

    # --- 3. Comparar bloco a bloco ---
    sep("3. HASH DE CADA BLOCO (comparacao)")
    if block_counts:
        max_blocks = max(block_counts.values()) if block_counts else 0
        for i in range(max_blocks + 1):
            hashes = {}
            for name, url in NODES:
                b = rpc(url, "eth_getBlockByNumber", [hex(i), False])
                if b:
                    hashes[name] = b.get("hash", "?")[:20]
                else:
                    hashes[name] = "N/A"

            all_same = len(set(hashes.values())) == 1
            status = "OK" if all_same else "DIFERENTE!"
            hash_display = list(hashes.values())[0] if all_same else " | ".join(f"{n}={h}" for n, h in hashes.items())
            print(f"  Bloco #{i}: [{status}] {hash_display}...")

    # --- 4. Contas e carteiras ---
    sep("4. CARTEIRAS E SALDOS")

    # pegar contas do primeiro no online
    active_url = None
    for name, url in NODES:
        accounts = rpc(url, "eth_accounts")
        if accounts:
            active_url = url
            break

    if not active_url:
        print("  Nenhum no online!")
        return

    accounts = rpc(active_url, "eth_accounts") or []
    validators = rpc(active_url, "pos_getValidators") or {}

    print(f"\n  {'ENDERECO':<46} {'LIVRE':>10} {'STAKED':>10} {'TOTAL':>10} {'VALIDADOR'}")
    print(f"  {'-'*46} {'-'*10} {'-'*10} {'-'*10} {'-'*12}")

    for addr in accounts:
        # saldo
        bal_hex = rpc(active_url, "eth_getBalance", [addr, "latest"])
        bal = int(bal_hex, 16) / 10**18 if bal_hex else 0

        # staked
        staked_info = rpc(active_url, "pos_getStaked", [addr])
        staked = staked_info.get("staked", 0) if staked_info else 0

        total = bal + staked

        # validador?
        is_val = "---"
        if addr in validators:
            v = validators[addr]
            if v.get("slashed"):
                is_val = "SLASHED"
            elif v.get("is_active"):
                is_val = "ATIVO"
            else:
                is_val = "INATIVO"

        print(f"  {addr} {bal:>10.2f} {staked:>10.2f} {total:>10.2f} {is_val}")

    # --- 5. Detalhe de cada carteira ---
    sep("5. DETALHE DE CADA CARTEIRA")

    for addr in accounts:
        bal_hex = rpc(active_url, "eth_getBalance", [addr, "latest"])
        bal = int(bal_hex, 16) / 10**18 if bal_hex else 0

        staked_info = rpc(active_url, "pos_getStaked", [addr])
        staked = staked_info.get("staked", 0) if staked_info else 0

        tx_count_hex = rpc(active_url, "eth_getTransactionCount", [addr, "latest"])
        tx_count = int(tx_count_hex, 16) if tx_count_hex else 0

        print(f"\n  Carteira: {addr}")
        print(f"    Saldo livre:   {bal:.2f} coins")
        print(f"    Staked:        {staked:.2f} coins")
        print(f"    Total:         {bal + staked:.2f} coins")
        print(f"    Transacoes:    {tx_count} enviadas")

        if addr in validators:
            v = validators[addr]
            print(f"    --- VALIDADOR ---")
            print(f"    Stake:         {v['stake']:.2f}")
            print(f"    Blocos valid.: {v['blocks_validated']}")
            print(f"    Rewards:       {v['rewards']:.2f}")
            print(f"    Ativo:         {v['is_active']}")
            print(f"    Slashed:       {v['slashed']}")

    # --- 6. Contratos ---
    sep("6. SMART CONTRACTS DEPLOYADOS")
    contracts = rpc(active_url, "pos_getContracts")
    if contracts:
        for cid, c in contracts.items():
            print(f"\n  [{cid}]")
            print(f"    Endereco: {c['address']}")
            print(f"    Criador:  {c['creator'][:20]}...")
            print(f"    Chamadas: {c['calls']}")
            state_str = json.dumps(c.get('state', {}))
            if len(state_str) > 100:
                state_str = state_str[:100] + "..."
            print(f"    State:    {state_str}")
    else:
        print("  Nenhum contrato deployado.")

    # --- 7. Validacao ---
    sep("7. VALIDACAO DA CADEIA EM CADA NO")
    for name, url in NODES:
        result = rpc(url, "pos_validate")
        if result:
            status = "OK" if result["valid"] else "FALHA"
            print(f"  {name}: [{status}] {result['message']}")
        else:
            print(f"  {name}: OFFLINE")

    sep("VERIFICACAO CONCLUIDA")


if __name__ == "__main__":
    main()
