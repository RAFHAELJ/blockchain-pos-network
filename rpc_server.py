"""
=============================================================
  JSON-RPC 2.0 Server - Padrao Ethereum
=============================================================
  Endpoint unico: POST /
  Todas as chamadas seguem o formato:

  {
    "jsonrpc": "2.0",
    "method": "eth_blockNumber",
    "params": [],
    "id": 1
  }

  Rode:
    python rpc_server.py --port 8545 --node node-SP

  Porta 8545 = padrao Ethereum (MetaMask, Web3.py, etc)
=============================================================
"""

import argparse
import requests
from flask import Flask, jsonify, request
from core import Blockchain, Block, Validator
from wallet import Wallet
from contracts import token_erc20, nft_contract, crowdfunding, dex_swap, voting

import threading
from uuid import uuid4 as _uuid4

app = Flask(__name__)
bc = None
node_wallets = {}
peers = []
seen_gossip = set()  # IDs de mensagens ja vistas (evita loop)
GOSSIP_TTL = 5       # maximo de saltos

CONTRACT_TYPES = {
    "token": token_erc20,
    "nft": nft_contract,
    "crowdfunding": crowdfunding,
    "dex": dex_swap,
    "voting": voting,
}


# =============================================================
# HELPERS
# =============================================================
def success(result, req_id):
    return jsonify({"jsonrpc": "2.0", "result": result, "id": req_id})


def error(code, message, req_id):
    return jsonify({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id})


def to_hex(value):
    """Converte numero pra hex (padrao Ethereum)."""
    if isinstance(value, float):
        value = int(value * 10**18)  # wei
    return hex(int(value))


def from_hex(value):
    """Converte hex pra int."""
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


# =============================================================
# GOSSIP PROTOCOL
# =============================================================
def gossip(msg_type, data, ttl=None, gossip_id=None):
    """
    Fofoca: envia mensagem pra todos os peers.
    Cada mensagem tem um ID unico pra evitar loop infinito.
    TTL (time to live) limita quantos saltos a fofoca faz.

    Fluxo:
      1. Node-SP recebe transacao do usuario
      2. Node-SP fofoca pra Node-RJ e Node-MG
      3. Node-RJ recebe, ve que e nova, processa e fofoca pra Node-MG
      4. Node-MG recebe de Node-SP, processa. Recebe de Node-RJ, ve que ja viu, ignora.
    """
    if ttl is None:
        ttl = GOSSIP_TTL
    if gossip_id is None:
        gossip_id = str(_uuid4()).replace("-", "")[:16]

    if gossip_id in seen_gossip:
        return  # ja vi essa fofoca, ignoro
    seen_gossip.add(gossip_id)

    # limpa mensagens antigas (evita memoria infinita)
    if len(seen_gossip) > 10000:
        seen_gossip.clear()

    if ttl <= 0:
        return  # fofoca morreu

    payload = {
        "jsonrpc": "2.0",
        "method": f"gossip_{msg_type}",
        "params": [{"data": data, "gossip_id": gossip_id, "ttl": ttl - 1, "origin": bc.node_id}],
        "id": 1,
    }

    def _send(peer_url):
        try:
            requests.post(peer_url, json=payload, timeout=2)
        except Exception:
            pass

    for peer in peers:
        t = threading.Thread(target=_send, args=(peer,), daemon=True)
        t.start()

    bc._log(f"GOSSIP [{msg_type}] id={gossip_id[:8]}... ttl={ttl} -> {len(peers)} peers")


# =============================================================
# JSON-RPC ENDPOINT UNICO
# =============================================================
@app.route("/", methods=["POST"])
def rpc():
    body = request.get_json()

    # suporte a batch (array de requests)
    if isinstance(body, list):
        results = [handle_rpc(req) for req in body]
        return jsonify(results)

    return handle_rpc(body)


def handle_rpc(body):
    if not body or "method" not in body:
        return error(-32600, "Invalid Request", None)

    method = body.get("method", "")
    params = body.get("params", [])
    req_id = body.get("id", 1)

    # mapeia metodo -> handler
    handlers = {
        # --- Gossip (interno entre nos) ---
        "gossip_tx": rpc_gossip_tx,
        "gossip_block": rpc_gossip_block,
        "gossip_account": rpc_gossip_account,
        "gossip_stake": rpc_gossip_stake,
        "gossip_contract": rpc_gossip_contract,
        "gossip_slash": rpc_gossip_slash,

        # --- Ethereum Standard ---
        "eth_blockNumber": rpc_block_number,
        "eth_getBlockByNumber": rpc_get_block_by_number,
        "eth_getBlockByHash": rpc_get_block_by_hash,
        "eth_getTransactionByHash": rpc_get_tx_by_hash,
        "eth_getBalance": rpc_get_balance,
        "eth_sendTransaction": rpc_send_transaction,
        "eth_getTransactionCount": rpc_get_tx_count,
        "eth_gasPrice": rpc_gas_price,
        "eth_chainId": rpc_chain_id,
        "eth_accounts": rpc_accounts,
        "eth_mining": rpc_mining,
        "eth_syncing": rpc_syncing,
        "net_version": rpc_net_version,
        "net_peerCount": rpc_peer_count,
        "net_listening": rpc_net_listening,
        "web3_clientVersion": rpc_client_version,

        # --- Custom (nossa blockchain) ---
        "pos_createWallet": rpc_create_wallet,
        "pos_createAccount": rpc_create_account,
        "pos_stake": rpc_stake,
        "pos_unstake": rpc_unstake,
        "pos_getValidators": rpc_get_validators,
        "pos_produceBlock": rpc_produce_block,
        "pos_slash": rpc_slash,
        "pos_deployContract": rpc_deploy_contract,
        "pos_callContract": rpc_call_contract,
        "pos_getContracts": rpc_get_contracts,
        "pos_getMempool": rpc_get_mempool,
        "pos_getStats": rpc_get_stats,
        "pos_getStaked": rpc_get_staked,
        "pos_addPeer": rpc_add_peer,
        "pos_getPeers": rpc_get_peers,
        "pos_getLog": rpc_get_log,
        "pos_save": rpc_save,
        "pos_validate": rpc_validate,
    }

    handler = handlers.get(method)
    if not handler:
        return error(-32601, f"Method not found: {method}", req_id)

    try:
        result = handler(params)
        return {"jsonrpc": "2.0", "result": result, "id": req_id}
    except Exception as e:
        return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}, "id": req_id}


# =============================================================
# ETHEREUM STANDARD METHODS
# =============================================================
def rpc_block_number(params):
    """eth_blockNumber - retorna o numero do ultimo bloco em hex."""
    return to_hex(len(bc.chain) - 1)


def rpc_get_block_by_number(params):
    """eth_getBlockByNumber - retorna bloco por numero."""
    idx = from_hex(params[0]) if params else len(bc.chain) - 1
    full_tx = params[1] if len(params) > 1 else False

    if idx >= len(bc.chain):
        return None

    b = bc.chain[idx]
    block_data = {
        "number": to_hex(b.index),
        "hash": "0x" + b.hash,
        "parentHash": "0x" + b.previous_hash,
        "timestamp": to_hex(int(b.timestamp.split(".")[0].replace("-", "").replace(":", "").replace(" ", ""))),
        "validator": b.validator,
        "epoch": to_hex(b.epoch),
        "transactionsRoot": "0x" + b.merkle_root,
        "stateRoot": "0x" + (b.state_root or "0" * 64),
        "finalized": b.finalized,
        "attestations": b.attestations,
        "transactions": b.transactions if full_tx else [
            tx.get("tx_id", "") for tx in b.transactions
        ],
    }
    return block_data


def rpc_get_block_by_hash(params):
    """eth_getBlockByHash - retorna bloco por hash."""
    target_hash = params[0].replace("0x", "") if params else ""
    for b in bc.chain:
        if b.hash == target_hash:
            return rpc_get_block_by_number([to_hex(b.index), params[1] if len(params) > 1 else False])
    return None


def rpc_get_tx_by_hash(params):
    """eth_getTransactionByHash - busca transacao por tx_id."""
    tx_id = params[0] if params else ""
    tx = bc.explorer_tx(tx_id)
    return tx


def rpc_get_balance(params):
    """eth_getBalance - retorna saldo em hex (wei)."""
    address = params[0] if params else ""
    balance = bc.get_balance(address)
    return to_hex(balance)


def rpc_send_transaction(params):
    """eth_sendTransaction - envia transacao e fofoca pros peers."""
    tx = params[0] if params else {}
    sender = tx.get("from", "")
    receiver = tx.get("to", "")
    amount = from_hex(tx.get("value", "0x0")) / 10**18 if tx.get("value", "").startswith("0x") else float(tx.get("value", 0))
    tip = float(tx.get("tip", 0))

    wallet = node_wallets.get(sender)
    ok, msg = bc.send(sender, receiver, amount, tip, wallet)

    if ok:
        # GOSSIP: fofoca a transacao pra toda a rede
        gossip("tx", {"from": sender, "to": receiver, "value": amount, "tip": tip})

    if not ok:
        raise Exception(msg)
    return msg


def rpc_get_tx_count(params):
    """eth_getTransactionCount - numero de txns de uma conta."""
    address = params[0] if params else ""
    count = sum(1 for tx in bc.tx_history if tx.get("sender") == address)
    return to_hex(count)


def rpc_gas_price(params):
    """eth_gasPrice - retorna base fee em hex."""
    return to_hex(int(bc.BASE_FEE * 10**18))


def rpc_chain_id(params):
    """eth_chainId - ID da chain."""
    return "0x539"  # 1337 (padrao dev)


def rpc_accounts(params):
    """eth_accounts - lista de contas no no."""
    return list(bc.accounts.keys())


def rpc_mining(params):
    """eth_mining - PoS nao minera, mas retorna se esta validando."""
    return len(bc.validators) > 0


def rpc_syncing(params):
    """eth_syncing - status de sincronizacao."""
    return False


def rpc_net_version(params):
    """net_version - versao da rede."""
    return "1337"


def rpc_peer_count(params):
    """net_peerCount - numero de peers."""
    return to_hex(len(peers))


def rpc_net_listening(params):
    """net_listening - se esta aceitando conexoes."""
    return True


def rpc_client_version(params):
    """web3_clientVersion - versao do cliente."""
    return f"CofenChain/v1.0/{bc.node_id}"


# =============================================================
# CUSTOM METHODS (pos_*)
# =============================================================
def rpc_create_wallet(params):
    """pos_createWallet - cria carteira e fofoca a conta pros peers."""
    p = params[0] if params else {}
    name = p.get("name", "wallet")
    balance = p.get("balance", 0)

    w = Wallet(name)
    node_wallets[w.address] = w
    bc.create_account(w.address, balance, name)

    # GOSSIP: fofoca a nova conta pra toda a rede
    gossip("account", {"address": w.address, "balance": balance})

    return {
        "name": w.name,
        "address": w.address,
        "publicKey": w.public_key,
        "privateKey": w.private_key,
    }


def rpc_create_account(params):
    """pos_createAccount - cria conta."""
    p = params[0] if params else {}
    ok, msg = bc.create_account(p.get("address", ""), p.get("balance", 0))
    if not ok:
        raise Exception(msg)
    return msg


def rpc_stake(params):
    """pos_stake - fazer stake e fofoca pros peers."""
    p = params[0] if params else {}
    ok, msg = bc.stake(p["address"], p["amount"])
    if not ok:
        raise Exception(msg)
    # GOSSIP: fofoca o stake
    gossip("stake", {"address": p["address"], "amount": p["amount"]})
    return msg


def rpc_unstake(params):
    """pos_unstake - desfazer stake."""
    p = params[0] if params else {}
    ok, msg = bc.unstake(p["address"], p["amount"])
    if not ok:
        raise Exception(msg)
    return msg


def rpc_get_validators(params):
    """pos_getValidators - lista validadores."""
    return {k: v.to_dict() for k, v in bc.validators.items()}


def rpc_produce_block(params):
    """pos_produceBlock - produz bloco e fofoca pra rede inteira."""
    block, elapsed = bc.produce_block()
    if not block:
        raise Exception(elapsed)

    # GOSSIP: fofoca o bloco inteiro pra toda a rede
    gossip("block", {
        "block": block.to_dict(),
        "accounts": bc.accounts.copy(),
        "staked": bc.staked.copy(),
        "validators": {k: v.to_dict() for k, v in bc.validators.items()},
        "burned": bc.burned,
    })

    return {
        "blockNumber": to_hex(block.index),
        "hash": "0x" + block.hash,
        "validator": block.validator,
        "transactions": len(block.transactions),
        "finalized": block.finalized,
        "time": round(elapsed, 4),
    }


def rpc_slash(params):
    """pos_slash - penalizar validador e fofoca."""
    p = params[0] if params else {}
    ok, msg = bc.slash(p["address"], p.get("reason", "violacao"))
    if not ok:
        raise Exception(msg)
    # GOSSIP: fofoca o slashing
    gossip("slash", {"address": p["address"], "reason": p.get("reason", "violacao")})
    return msg


def rpc_deploy_contract(params):
    """pos_deployContract - deploy smart contract e fofoca."""
    p = params[0] if params else {}
    ctype = p.get("type", "token")
    if ctype not in CONTRACT_TYPES:
        raise Exception(f"Tipos disponiveis: {list(CONTRACT_TYPES.keys())}")

    ok, msg = bc.deploy_contract(p["creator"], p["id"], CONTRACT_TYPES[ctype])
    if ok and "state" in p:
        bc.contracts[p["id"]].state.update(p["state"])
    if not ok:
        raise Exception(msg)
    # GOSSIP: fofoca o deploy
    gossip("contract", {"creator": p["creator"], "id": p["id"], "type": ctype, "state": p.get("state", {})})
    return msg


def rpc_call_contract(params):
    """pos_callContract - chamar smart contract."""
    p = params[0] if params else {}
    result = bc.call_contract(p["caller"], p["id"], p.get("params", {}))
    if isinstance(result, tuple):
        ok, msg = result
        if not ok:
            raise Exception(msg)
        return msg
    return str(result)


def rpc_get_contracts(params):
    """pos_getContracts - lista contratos."""
    return {cid: {"address": c.address, "creator": c.creator, "calls": c.call_count, "state": c.state}
            for cid, c in bc.contracts.items()}


def rpc_get_mempool(params):
    """pos_getMempool - transacoes pendentes."""
    return {"size": bc.mempool.size(), "transactions": bc.mempool.transactions}


def rpc_get_stats(params):
    """pos_getStats - estatisticas."""
    finalized = sum(1 for b in bc.chain if b.finalized)
    return {
        "node": bc.node_id,
        "blocks": len(bc.chain),
        "epoch": bc.current_epoch,
        "validators": len(bc.validators),
        "mempool": bc.mempool.size(),
        "burned": bc.burned,
        "supply": bc.total_supply - bc.burned,
        "finalized": f"{finalized}/{len(bc.chain)}",
        "txHistory": len(bc.tx_history),
    }


def rpc_get_staked(params):
    """pos_getStaked - quanto uma conta tem staked."""
    address = params[0] if params else ""
    return {"address": address, "staked": bc.staked.get(address, 0)}


def rpc_add_peer(params):
    """pos_addPeer - registrar peer."""
    url = (params[0] if params else "").rstrip("/")
    if url and url not in peers:
        peers.append(url)
    return {"peers": peers}


def rpc_get_peers(params):
    """pos_getPeers - listar peers."""
    return peers


def rpc_get_log(params):
    """pos_getLog - event log."""
    n = params[0] if params else 50
    return bc.event_log[-n:]


def rpc_save(params):
    """pos_save - salvar blockchain em disco."""
    path = bc.save()
    return {"path": path}


def rpc_validate(params):
    """pos_validate - validar cadeia."""
    ok, msg = bc.is_valid()
    return {"valid": ok, "message": msg}


# =============================================================
# GOSSIP HANDLERS (recebe fofoca dos peers)
# =============================================================
def rpc_gossip_tx(params):
    """Recebe fofoca de transacao de outro no."""
    p = params[0] if params else {}
    gid = p.get("gossip_id", "")
    ttl = p.get("ttl", 0)
    data = p.get("data", {})

    if gid in seen_gossip:
        return "already seen"
    seen_gossip.add(gid)

    # garante que as contas existem
    if data.get("from") and data["from"] not in bc.accounts:
        bc.create_account(data["from"], 0)
    if data.get("to") and data["to"] not in bc.accounts:
        bc.create_account(data["to"], 0)

    bc.send(data.get("from", ""), data.get("to", ""), data.get("value", 0), data.get("tip", 0))
    bc._log(f"GOSSIP RECV [tx] from {p.get('origin','?')} id={gid[:8]}...")

    # repassa a fofoca
    if ttl > 0:
        gossip("tx", data, ttl=ttl, gossip_id=gid)
    return "ok"


def rpc_gossip_block(params):
    """Recebe fofoca de bloco de outro no."""
    p = params[0] if params else {}
    gid = p.get("gossip_id", "")
    ttl = p.get("ttl", 0)
    data = p.get("data", {})

    if gid in seen_gossip:
        return "already seen"
    seen_gossip.add(gid)

    block_data = data.get("block", {})
    block_index = block_data.get("index", 0)

    # so aceita se e o proximo bloco na cadeia
    if block_index == len(bc.chain):
        new_block = Block(
            index=block_data["index"],
            transactions=block_data["transactions"],
            validator=block_data["validator"],
            previous_hash=block_data["previous_hash"],
            epoch=block_data["epoch"],
        )
        new_block.hash = block_data["hash"]
        new_block.finalized = block_data.get("finalized", False)
        new_block.attestations = block_data.get("attestations", [])
        new_block.merkle_root = block_data.get("merkle_root", "")
        new_block.timestamp = block_data.get("timestamp", "")

        # sincroniza state
        bc.accounts.update(data.get("accounts", {}))
        bc.staked.update(data.get("staked", {}))
        bc.burned = data.get("burned", bc.burned)

        # sincroniza validadores
        for addr, vdata in data.get("validators", {}).items():
            if addr not in bc.validators:
                bc.validators[addr] = Validator(addr, vdata["stake"])
            v = bc.validators[addr]
            v.stake = vdata["stake"]
            v.is_active = vdata["is_active"]
            v.slashed = vdata["slashed"]
            v.blocks_validated = vdata["blocks_validated"]
            v.rewards = vdata["rewards"]

        bc.chain.append(new_block)
        bc.current_epoch = block_data.get("epoch", bc.current_epoch)
        # limpa mempool (transacoes ja foram incluidas no bloco)
        bc.mempool.transactions.clear()

        bc._log(f"GOSSIP RECV [block] #{block_index} from {p.get('origin','?')}")
    elif block_index <= len(bc.chain) - 1:
        bc._log(f"GOSSIP RECV [block] #{block_index} ja tenho, ignorando")
    else:
        bc._log(f"GOSSIP RECV [block] #{block_index} futuro! Preciso sync (tenho {len(bc.chain)-1})")

    if ttl > 0:
        gossip("block", data, ttl=ttl, gossip_id=gid)
    return "ok"


def rpc_gossip_account(params):
    """Recebe fofoca de nova conta."""
    p = params[0] if params else {}
    gid = p.get("gossip_id", "")
    ttl = p.get("ttl", 0)
    data = p.get("data", {})

    if gid in seen_gossip:
        return "already seen"
    seen_gossip.add(gid)

    addr = data.get("address", "")
    bal = data.get("balance", 0)
    if addr and addr not in bc.accounts:
        bc.create_account(addr, bal)
        bc._log(f"GOSSIP RECV [account] {addr[:12]}... bal={bal} from {p.get('origin','?')}")

    if ttl > 0:
        gossip("account", data, ttl=ttl, gossip_id=gid)
    return "ok"


def rpc_gossip_stake(params):
    """Recebe fofoca de stake."""
    p = params[0] if params else {}
    gid = p.get("gossip_id", "")
    ttl = p.get("ttl", 0)
    data = p.get("data", {})

    if gid in seen_gossip:
        return "already seen"
    seen_gossip.add(gid)

    addr = data.get("address", "")
    amount = data.get("amount", 0)
    if addr in bc.accounts:
        bc.stake(addr, amount)
        bc._log(f"GOSSIP RECV [stake] {addr[:12]}... amount={amount} from {p.get('origin','?')}")

    if ttl > 0:
        gossip("stake", data, ttl=ttl, gossip_id=gid)
    return "ok"


def rpc_gossip_contract(params):
    """Recebe fofoca de deploy de contrato."""
    p = params[0] if params else {}
    gid = p.get("gossip_id", "")
    ttl = p.get("ttl", 0)
    data = p.get("data", {})

    if gid in seen_gossip:
        return "already seen"
    seen_gossip.add(gid)

    cid = data.get("id", "")
    ctype = data.get("type", "token")
    creator = data.get("creator", "")
    if cid and cid not in bc.contracts and ctype in CONTRACT_TYPES:
        bc.deploy_contract(creator, cid, CONTRACT_TYPES[ctype])
        if data.get("state"):
            bc.contracts[cid].state.update(data["state"])
        bc._log(f"GOSSIP RECV [contract] {cid} from {p.get('origin','?')}")

    if ttl > 0:
        gossip("contract", data, ttl=ttl, gossip_id=gid)
    return "ok"


def rpc_gossip_slash(params):
    """Recebe fofoca de slashing."""
    p = params[0] if params else {}
    gid = p.get("gossip_id", "")
    ttl = p.get("ttl", 0)
    data = p.get("data", {})

    if gid in seen_gossip:
        return "already seen"
    seen_gossip.add(gid)

    addr = data.get("address", "")
    if addr in bc.validators and not bc.validators[addr].slashed:
        bc.slash(addr, data.get("reason", "gossip"))
        bc._log(f"GOSSIP RECV [slash] {addr[:12]}... from {p.get('origin','?')}")

    if ttl > 0:
        gossip("slash", data, ttl=ttl, gossip_id=gid)
    return "ok"


# =============================================================
# INFO (GET / pra browser)
# =============================================================
@app.route("/", methods=["GET"])
def info():
    return jsonify({
        "name": f"CofenChain JSON-RPC [{bc.node_id}]",
        "jsonrpc": "2.0",
        "port": "8545 (padrao Ethereum)",
        "blocks": len(bc.chain),
        "methods": {
            "Ethereum Standard": [
                "eth_blockNumber", "eth_getBlockByNumber", "eth_getBlockByHash",
                "eth_getTransactionByHash", "eth_getBalance", "eth_sendTransaction",
                "eth_getTransactionCount", "eth_gasPrice", "eth_chainId",
                "eth_accounts", "eth_mining", "eth_syncing",
                "net_version", "net_peerCount", "net_listening",
                "web3_clientVersion",
            ],
            "Custom PoS": [
                "pos_createWallet", "pos_createAccount", "pos_stake", "pos_unstake",
                "pos_getValidators", "pos_produceBlock", "pos_slash",
                "pos_deployContract", "pos_callContract", "pos_getContracts",
                "pos_getMempool", "pos_getStats", "pos_getStaked",
                "pos_addPeer", "pos_getPeers", "pos_getLog", "pos_save", "pos_validate",
            ],
        },
        "example": {
            "method": "POST /",
            "body": '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}',
        }
    })


# =============================================================
# MAIN
# =============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blockchain PoS JSON-RPC Node")
    parser.add_argument("--port", type=int, default=8545)
    parser.add_argument("--node", type=str, default="node-0")
    parser.add_argument("--peer", type=str, action="append", default=[])
    args = parser.parse_args()

    bc = Blockchain(node_id=args.node)
    peers.extend(args.peer)

    print(f"\n{'='*50}")
    print(f"  CofenChain JSON-RPC 2.0")
    print(f"  Node: {args.node}")
    print(f"  URL:  http://localhost:{args.port}")
    print(f"  Peers: {peers or 'nenhum'}")
    print(f"{'='*50}")
    print(f"  Padrao Ethereum - compativel com Web3.py")
    print(f"  GET  / = info dos metodos")
    print(f"  POST / = JSON-RPC endpoint")
    print(f"{'='*50}\n")

    app.run(host="0.0.0.0", port=args.port, debug=False)
