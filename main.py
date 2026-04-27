"""
=============================================================
  SIMULACAO COMPLETA - Blockchain PoS Full
=============================================================
  Fluxo:
  1.  Criar carteiras (chave publica/privada)
  2.  Criar contas com saldo
  3.  Registrar validadores (staking)
  4.  Enviar transacoes assinadas (com gas + tip)
  5.  Mempool prioriza por tip
  6.  Validador selecionado por stake
  7.  Bloco produzido + attestations + finality
  8.  Smart Contracts (Token, NFT, Vaquinha, DEX, Votacao)
  9.  Slashing de validador malicioso
  10. Rede P2P com multiplos nos + sync
  11. Persistencia em disco (JSON)
  12. Explorer (consultar blocos, txns, contas)
=============================================================
"""

from wallet import Wallet
from core import Blockchain
from network import Network, Node
from contracts import token_erc20, nft_contract, crowdfunding, dex_swap, voting


def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    sep("BLOCKCHAIN PoS FULL - SIMULACAO COMPLETA")

    # ==========================================================
    # 1. CARTEIRAS
    # ==========================================================
    sep("1. CRIANDO CARTEIRAS (chave publica/privada)")

    wallets = {}
    for name in ["Alice", "Bob", "Carol", "Dave", "Eve"]:
        w = Wallet(name)
        wallets[name] = w
        print(f"  {w.name}:")
        print(f"    Endereco:      {w.address}")
        print(f"    Chave publica: {w.public_key[:24]}...")
        print(f"    Chave privada: {w.private_key[:8]}...{'*'*20} (secreta!)")

    # ==========================================================
    # 2. BLOCKCHAIN + CONTAS
    # ==========================================================
    sep("2. CRIANDO BLOCKCHAIN E CONTAS")

    bc = Blockchain(node_id="main-node")

    initial = {"Alice": 500, "Bob": 300, "Carol": 150, "Dave": 80, "Eve": 50}
    for name, bal in initial.items():
        bc.create_account(wallets[name].address, bal, name)
    print("  Contas criadas com saldo inicial.")
    bc.print_accounts()

    # ==========================================================
    # 3. STAKING (virar validador)
    # ==========================================================
    sep("3. STAKING - REGISTRANDO VALIDADORES")

    stakes = {"Alice": 200, "Bob": 100, "Carol": 50}
    for name, amount in stakes.items():
        ok, msg = bc.stake(wallets[name].address, amount)
        print(f"  {name}: {msg}")

    # Dave tenta com pouco
    ok, msg = bc.stake(wallets["Dave"].address, 10)
    print(f"  Dave: {msg}")

    bc.print_validators()
    bc.print_accounts()

    # ==========================================================
    # 4. TRANSACOES ASSINADAS
    # ==========================================================
    sep("4. TRANSACOES COM ASSINATURA DIGITAL")

    txns = [
        ("Alice", "Dave", 30, 0.5),
        ("Bob", "Eve", 20, 0.3),
        ("Carol", "Alice", 10, 0.1),
        ("Dave", "Bob", 5, 0),
        ("Alice", "Carol", 15, 0.8),  # tip alto = prioridade
    ]
    for sender, receiver, amount, tip in txns:
        ok, msg = bc.send(
            wallets[sender].address,
            wallets[receiver].address,
            amount, tip,
            wallet=wallets[sender]
        )
        print(f"  {sender}->{receiver}: {msg}")

    print(f"\n  Mempool: {bc.mempool.size()} transacoes (ordenadas por tip)")
    for i, tx in enumerate(bc.mempool.transactions):
        print(f"    {i+1}. tip={tx['tip']} | {tx['sender'][:10]}.. -> {tx['receiver'][:10]}..: {tx['amount']}")

    # ==========================================================
    # 5. PRODUZIR BLOCOS
    # ==========================================================
    sep("5. PRODUZINDO BLOCOS (PoS)")

    for i in range(1, 4):
        block, elapsed = bc.produce_block()
        att = len(block.attestations)
        total_v = len([v for v in bc.validators.values() if v.is_active])
        print(f"\n  Bloco #{block.index}:")
        print(f"    Validador:    {block.validator[:16]}...")
        print(f"    Epoch:        {block.epoch}")
        print(f"    Transacoes:   {len(block.transactions)}")
        print(f"    Attestations: {att}/{total_v} ({att/total_v*100:.0f}%)")
        print(f"    Finalizado:   {block.finalized}")
        print(f"    Tempo:        {elapsed:.4f}s")
        print(f"    Hash:         {block.hash[:32]}...")

    # ==========================================================
    # 6. SMART CONTRACTS
    # ==========================================================
    sep("6. SMART CONTRACTS")

    # --- Token ERC-20 ---
    print("\n  --- TOKEN ERC-20 ---")
    ok, msg = bc.deploy_contract(wallets["Alice"].address, "PosToken", token_erc20)
    print(f"  Deploy: {msg}")

    bc.contracts["PosToken"].state["name"] = "PosToken"
    bc.contracts["PosToken"].state["symbol"] = "CFN"

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosToken",
                               {"action": "mint", "amount": 10000, "to": wallets["Alice"].address})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosToken",
                               {"action": "transfer", "to": wallets["Bob"].address, "amount": 500})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Bob"].address, "PosToken",
                               {"action": "balance_of"})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosToken", {"action": "info"})
    print(f"  {msg}")

    # --- NFT ---
    print("\n  --- NFT ---")
    ok, msg = bc.deploy_contract(wallets["Alice"].address, "PosNFT", nft_contract)
    print(f"  Deploy: {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosNFT",
                               {"action": "mint", "metadata": {"name": "PosArt #1", "rarity": "legendary"}})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Bob"].address, "PosNFT",
                               {"action": "mint", "metadata": {"name": "PosArt #2", "rarity": "common"}})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosNFT",
                               {"action": "transfer", "token_id": 1, "to": wallets["Carol"].address})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Carol"].address, "PosNFT", {"action": "list"})
    print(f"  {msg}")

    # --- Crowdfunding ---
    print("\n  --- CROWDFUNDING ---")
    ok, msg = bc.deploy_contract(wallets["Alice"].address, "Vaquinha", crowdfunding)
    print(f"  Deploy: {msg}")
    bc.contracts["Vaquinha"].state["meta"] = 40

    for name, amount in [("Bob", 15), ("Dave", 10), ("Eve", 5), ("Carol", 15)]:
        ok, msg = bc.call_contract(wallets[name].address, "Vaquinha",
                                   {"action": "contribute", "amount": amount})
        print(f"  {name}: {msg}")

    # --- DEX ---
    print("\n  --- DEX (Exchange Descentralizada) ---")
    ok, msg = bc.deploy_contract(wallets["Alice"].address, "PosDEX", dex_swap)
    print(f"  Deploy: {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosDEX", {"action": "pool_info"})
    print(f"  {msg}")

    ok, msg = bc.call_contract(wallets["Bob"].address, "PosDEX",
                               {"action": "swap_a_to_b", "amount": 50})
    print(f"  Bob: {msg}")

    ok, msg = bc.call_contract(wallets["Carol"].address, "PosDEX",
                               {"action": "swap_b_to_a", "amount": 30})
    print(f"  Carol: {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "PosDEX", {"action": "pool_info"})
    print(f"  {msg}")

    # --- Votacao ---
    print("\n  --- VOTACAO ON-CHAIN ---")
    ok, msg = bc.deploy_contract(wallets["Alice"].address, "Votacao", voting)
    print(f"  Deploy: {msg}")

    bc.call_contract(wallets["Alice"].address, "Votacao",
                     {"action": "create_proposal", "id": "P1", "description": "Aumentar recompensa pra 10"})
    bc.call_contract(wallets["Alice"].address, "Votacao",
                     {"action": "create_proposal", "id": "P2", "description": "Reduzir taxa base pra 0.005"})

    for name, prop in [("Alice", "P1"), ("Bob", "P1"), ("Carol", "P2"), ("Dave", "P1"), ("Eve", "P2")]:
        ok, msg = bc.call_contract(wallets[name].address, "Votacao",
                                   {"action": "vote", "id": prop})
        print(f"  {name}: {msg}")

    ok, msg = bc.call_contract(wallets["Alice"].address, "Votacao", {"action": "results"})
    print(f"  {msg}")

    # Produzir bloco com contratos
    print("\n  Produzindo blocos com transacoes de contratos...")
    for _ in range(2):
        block, _ = bc.produce_block()
        print(f"  {block}")

    # ==========================================================
    # 7. SLASHING
    # ==========================================================
    sep("7. SLASHING")

    print("  Carol tentou double voting...")
    ok, msg = bc.slash(wallets["Carol"].address, "double voting")
    print(f"  {msg}")
    bc.print_validators()

    # ==========================================================
    # 8. UNSTAKING
    # ==========================================================
    sep("8. UNSTAKING")

    ok, msg = bc.unstake(wallets["Bob"].address, 30)
    print(f"  Bob: {msg}")
    bc.print_validators()

    # Mais blocos
    bc.send(wallets["Alice"].address, wallets["Eve"].address, 10, 0.2, wallets["Alice"])
    block, _ = bc.produce_block()
    print(f"\n  {block}")

    # ==========================================================
    # 9. REDE P2P
    # ==========================================================
    sep("9. REDE P2P (multiplos nos)")

    net = Network()
    node1 = net.add_node("node-SP")
    node2 = net.add_node("node-RJ")
    node3 = net.add_node("node-MG")
    net.connect_all()

    # Copiar estado pro node1
    node1.blockchain = bc

    print("  Antes do sync:")
    net.print_status()

    net.sync_all()

    print("\n  Depois do sync:")
    net.print_status()

    # ==========================================================
    # 10. PERSISTENCIA
    # ==========================================================
    sep("10. PERSISTENCIA (salvar em disco)")

    path = bc.save()
    print(f"  Blockchain salva em: {path}")

    ok, data = bc.load()
    if ok:
        print(f"  Blockchain carregada: {len(data['chain'])} blocos, {len(data['accounts'])} contas")

    # ==========================================================
    # 11. EXPLORER
    # ==========================================================
    sep("11. EXPLORER")

    print("\n  --- Bloco #1 ---")
    b = bc.explorer_block(1)
    if b:
        print(f"  Index:     {b['index']}")
        print(f"  Validator: {b['validator'][:16]}...")
        print(f"  Hash:      {b['hash'][:32]}...")
        print(f"  Txns:      {len(b['transactions'])}")
        print(f"  Finalized: {b['finalized']}")

    print(f"\n  --- Conta Alice ---")
    info = bc.explorer_account(wallets["Alice"].address)
    for k, v in info.items():
        val = f"{v[:16]}..." if isinstance(v, str) and len(v) > 16 else v
        print(f"  {k}: {val}")

    # ==========================================================
    # 12. ESTADO FINAL
    # ==========================================================
    sep("12. ESTADO FINAL")

    valid, msg = bc.is_valid()
    print(f"\n  Validacao: {msg}")

    bc.print_stats()
    bc.print_accounts()
    bc.print_validators()
    bc.print_chain()
    bc.print_log(30)

    sep("SIMULACAO CONCLUIDA")


if __name__ == "__main__":
    main()
