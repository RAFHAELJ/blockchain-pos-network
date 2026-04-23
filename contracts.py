"""
Smart Contracts de exemplo.
Token ERC-20, NFT, Crowdfunding, DEX, Votacao.
"""


def token_erc20(contract, caller, params, blockchain):
    """Token ERC-20 simplificado (como USDT, LINK, etc)."""
    action = params.get("action")
    state = contract.state
    state.setdefault("name", params.get("name", "MyToken"))
    state.setdefault("symbol", params.get("symbol", "MTK"))
    state.setdefault("total_supply", 0)
    state.setdefault("balances", {})

    if action == "mint":
        amount = params.get("amount", 0)
        to = params.get("to", caller)
        state["balances"][to] = state["balances"].get(to, 0) + amount
        state["total_supply"] += amount
        return True, f"Mint: {amount} {state['symbol']} para {to[:12]}..."

    elif action == "transfer":
        to = params.get("to")
        amount = params.get("amount", 0)
        if state["balances"].get(caller, 0) < amount:
            return False, "Saldo de tokens insuficiente"
        state["balances"][caller] -= amount
        state["balances"][to] = state["balances"].get(to, 0) + amount
        return True, f"Transfer: {amount} {state['symbol']} {caller[:12]}.. -> {to[:12]}.."

    elif action == "balance_of":
        addr = params.get("address", caller)
        bal = state["balances"].get(addr, 0)
        return True, f"{addr[:12]}... tem {bal} {state['symbol']}"

    elif action == "info":
        return True, f"{state['name']} ({state['symbol']}) supply={state['total_supply']}"

    return False, "Acao desconhecida"


def nft_contract(contract, caller, params, blockchain):
    """NFT simplificado (como ERC-721)."""
    action = params.get("action")
    state = contract.state
    state.setdefault("tokens", {})  # token_id -> {owner, metadata}
    state.setdefault("next_id", 1)

    if action == "mint":
        token_id = state["next_id"]
        metadata = params.get("metadata", {})
        state["tokens"][str(token_id)] = {
            "owner": caller,
            "metadata": metadata,
        }
        state["next_id"] += 1
        return True, f"NFT #{token_id} mintado para {caller[:12]}... metadata={metadata}"

    elif action == "transfer":
        token_id = str(params.get("token_id"))
        to = params.get("to")
        if token_id not in state["tokens"]:
            return False, "NFT nao existe"
        if state["tokens"][token_id]["owner"] != caller:
            return False, "Voce nao e o dono"
        state["tokens"][token_id]["owner"] = to
        return True, f"NFT #{token_id} transferido para {to[:12]}..."

    elif action == "owner_of":
        token_id = str(params.get("token_id"))
        if token_id not in state["tokens"]:
            return False, "NFT nao existe"
        owner = state["tokens"][token_id]["owner"]
        return True, f"NFT #{token_id} pertence a {owner[:12]}..."

    elif action == "list":
        owned = {k: v for k, v in state["tokens"].items() if v["owner"] == caller}
        return True, f"{caller[:12]}... possui {len(owned)} NFTs: {list(owned.keys())}"

    return False, "Acao desconhecida"


def crowdfunding(contract, caller, params, blockchain):
    """Vaquinha on-chain."""
    action = params.get("action")
    state = contract.state
    state.setdefault("meta", params.get("meta", 100))
    state.setdefault("total", 0)
    state.setdefault("contributors", {})
    state.setdefault("closed", False)

    if action == "contribute":
        if state["closed"]:
            return False, "Campanha encerrada"
        amount = params.get("amount", 0)
        if blockchain.accounts.get(caller, 0) < amount:
            return False, "Saldo insuficiente"
        blockchain.accounts[caller] -= amount
        state["total"] += amount
        state["contributors"][caller] = state["contributors"].get(caller, 0) + amount
        if state["total"] >= state["meta"]:
            state["closed"] = True
            return True, f"META ATINGIDA! Total: {state['total']}/{state['meta']}"
        return True, f"+{amount} coins. Total: {state['total']}/{state['meta']}"

    elif action == "status":
        s = "ENCERRADA" if state["closed"] else "ABERTA"
        return True, f"[{s}] {state['total']}/{state['meta']} | {len(state['contributors'])} contribuidores"

    elif action == "refund":
        if state["closed"]:
            return False, "Meta atingida, sem reembolso"
        contributed = state["contributors"].get(caller, 0)
        if contributed == 0:
            return False, "Nada a reembolsar"
        blockchain.accounts[caller] = blockchain.accounts.get(caller, 0) + contributed
        state["total"] -= contributed
        del state["contributors"][caller]
        return True, f"Reembolso: {contributed} coins para {caller[:12]}..."

    return False, "Acao desconhecida"


def dex_swap(contract, caller, params, blockchain):
    """DEX simplificada (exchange descentralizada)."""
    action = params.get("action")
    state = contract.state
    state.setdefault("pool_a", 1000)  # liquidez token A
    state.setdefault("pool_b", 1000)  # liquidez token B
    state.setdefault("swaps", [])
    state.setdefault("fee_rate", 0.003)  # 0.3% fee

    if action == "swap_a_to_b":
        amount_in = params.get("amount", 0)
        if blockchain.accounts.get(caller, 0) < amount_in:
            return False, "Saldo insuficiente"
        # formula AMM (x * y = k)
        fee = amount_in * state["fee_rate"]
        amount_after_fee = amount_in - fee
        amount_out = (state["pool_b"] * amount_after_fee) / (state["pool_a"] + amount_after_fee)
        state["pool_a"] += amount_in
        state["pool_b"] -= amount_out
        blockchain.accounts[caller] -= amount_in
        state["swaps"].append({"who": caller, "in": amount_in, "out": round(amount_out, 4), "dir": "A->B"})
        return True, f"Swap: {amount_in} A -> {amount_out:.4f} B (fee: {fee:.4f})"

    elif action == "swap_b_to_a":
        amount_in = params.get("amount", 0)
        if blockchain.accounts.get(caller, 0) < amount_in:
            return False, "Saldo insuficiente"
        fee = amount_in * state["fee_rate"]
        amount_after_fee = amount_in - fee
        amount_out = (state["pool_a"] * amount_after_fee) / (state["pool_b"] + amount_after_fee)
        state["pool_b"] += amount_in
        state["pool_a"] -= amount_out
        blockchain.accounts[caller] -= amount_in
        state["swaps"].append({"who": caller, "in": amount_in, "out": round(amount_out, 4), "dir": "B->A"})
        return True, f"Swap: {amount_in} B -> {amount_out:.4f} A (fee: {fee:.4f})"

    elif action == "pool_info":
        k = state["pool_a"] * state["pool_b"]
        rate = state["pool_b"] / state["pool_a"]
        return True, f"Pool A:{state['pool_a']:.2f} B:{state['pool_b']:.2f} | Rate:1:{rate:.4f} | K:{k:.2f}"

    return False, "Acao desconhecida"


def voting(contract, caller, params, blockchain):
    """Sistema de votacao on-chain."""
    action = params.get("action")
    state = contract.state
    state.setdefault("proposals", {})
    state.setdefault("voters", {})  # voter -> proposal votado

    if action == "create_proposal":
        pid = params.get("id")
        desc = params.get("description", "")
        state["proposals"][pid] = {"description": desc, "votes": 0, "voters": []}
        return True, f"Proposta '{pid}' criada: {desc}"

    elif action == "vote":
        pid = params.get("id")
        if pid not in state["proposals"]:
            return False, "Proposta nao existe"
        if caller in state["voters"]:
            return False, f"Ja votou na proposta '{state['voters'][caller]}'"
        state["proposals"][pid]["votes"] += 1
        state["proposals"][pid]["voters"].append(caller)
        state["voters"][caller] = pid
        return True, f"Voto registrado em '{pid}' ({state['proposals'][pid]['votes']} votos)"

    elif action == "results":
        lines = []
        for pid, p in state["proposals"].items():
            lines.append(f"  {pid}: {p['votes']} votos - {p['description']}")
        return True, "Resultados:\n" + "\n".join(lines)

    return False, "Acao desconhecida"
