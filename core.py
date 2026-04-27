"""
Core da blockchain PoS completa.
Block, Transaction, Mempool, Staking, Slashing,
Gas, Epochs, Finality, Smart Contracts, Persistencia.
"""

import hashlib
import json
import os
import random
import time
from datetime import datetime
from uuid import uuid4


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# =============================================================
# TRANSACAO
# =============================================================
class Transaction:
    def __init__(self, sender, receiver, amount, tx_type="transfer",
                 tip=0, data=None, signature=None, public_key=None):
        self.tx_id = str(uuid4()).replace("-", "")[:16]
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.tx_type = tx_type  # transfer, stake, unstake, contract_deploy, contract_call, reward
        self.tip = tip
        self.data = data or {}
        self.signature = signature
        self.public_key = public_key
        self.timestamp = str(datetime.now())
        self.status = "pending"  # pending -> confirmed -> finalized

    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "tx_type": self.tx_type,
            "tip": self.tip,
            "data": self.data,
            "signature": self.signature,
            "public_key": self.public_key,
            "timestamp": self.timestamp,
            "status": self.status,
        }

    def calc_hash(self):
        d = {"sender": self.sender, "receiver": self.receiver,
             "amount": self.amount, "tx_type": self.tx_type,
             "tip": self.tip, "timestamp": self.timestamp}
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

    def __repr__(self):
        return f"Tx({self.tx_type}) {self.sender[:8]}..->{self.receiver[:8]}..: {self.amount}"


# =============================================================
# BLOCO
# =============================================================
class Block:
    def __init__(self, index, transactions, validator, previous_hash, epoch, slot=0):
        self.index = index
        self.timestamp = str(datetime.now())
        self.transactions = transactions  # lista de dicts
        self.validator = validator
        self.previous_hash = previous_hash
        self.epoch = epoch
        self.slot = slot  # posicao dentro da epoch
        self.merkle_root = self._merkle_root()
        self.state_root = ""
        self.hash = self.calc_hash()
        self.finalized = False
        self.attestations = []

    def calc_hash(self):
        data = json.dumps({
            "index": self.index, "timestamp": self.timestamp,
            "transactions": self.transactions, "validator": self.validator,
            "previous_hash": self.previous_hash, "epoch": self.epoch,
            "merkle_root": self.merkle_root,
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _merkle_root(self):
        if not self.transactions:
            return hashlib.sha256(b"empty").hexdigest()
        hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                  for tx in self.transactions]
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                      for i in range(0, len(hashes), 2)]
        return hashes[0]

    def to_dict(self):
        return {
            "index": self.index, "timestamp": self.timestamp,
            "transactions": self.transactions, "validator": self.validator,
            "previous_hash": self.previous_hash, "epoch": self.epoch,
            "slot": self.slot, "state_root": self.state_root,
            "merkle_root": self.merkle_root, "hash": self.hash,
            "finalized": self.finalized, "attestations": self.attestations,
        }

    def __repr__(self):
        s = "FINAL" if self.finalized else "pending"
        return f"Block #{self.index} | {self.validator} | Epoch {self.epoch} | {s} | {self.hash[:16]}..."


# =============================================================
# VALIDADOR
# =============================================================
class Validator:
    def __init__(self, address, stake):
        self.address = address
        self.stake = stake
        self.is_active = True
        self.slashed = False
        self.blocks_validated = 0
        self.rewards = 0
        self.uptime = 100.0  # percentual
        self.registered_at = str(datetime.now())

    def to_dict(self):
        return {
            "address": self.address, "stake": self.stake,
            "is_active": self.is_active, "slashed": self.slashed,
            "blocks_validated": self.blocks_validated, "rewards": self.rewards,
            "uptime": self.uptime,
        }


# =============================================================
# SMART CONTRACT
# =============================================================
class SmartContract:
    def __init__(self, contract_id, creator, logic, state=None):
        self.contract_id = contract_id
        self.address = "0xC" + hashlib.sha256(contract_id.encode()).hexdigest()[:39]
        self.creator = creator
        self.logic = logic
        self.state = state or {}
        self.deployed_at = str(datetime.now())
        self.call_count = 0

    def execute(self, caller, params, blockchain):
        self.call_count += 1
        return self.logic(self, caller, params, blockchain)


# =============================================================
# MEMPOOL (fila de transacoes)
# =============================================================
class Mempool:
    """Fila de transacoes pendentes, ordenada por tip (prioridade)."""
    def __init__(self):
        self.transactions = []

    def add(self, tx):
        self.transactions.append(tx)
        # ordena por tip (maior tip = maior prioridade)
        self.transactions.sort(key=lambda t: t.get("tip", 0), reverse=True)

    def get_batch(self, max_txns=10):
        batch = self.transactions[:max_txns]
        self.transactions = self.transactions[max_txns:]
        return batch

    def size(self):
        return len(self.transactions)


# =============================================================
# BLOCKCHAIN PoS COMPLETA
# =============================================================
class Blockchain:
    BASE_REWARD = 5
    MIN_STAKE = 32
    SLASH_PENALTY = 0.5
    BASE_FEE = 0.01
    BLOCKS_PER_EPOCH = 3
    FINALITY_THRESHOLD = 0.66
    MAX_TXN_PER_BLOCK = 10

    def __init__(self, node_id="node-0"):
        self.node_id = node_id
        self.chain = []
        self.mempool = Mempool()
        self.validators = {}
        self.contracts = {}
        self.accounts = {}      # address -> balance
        self.staked = {}        # address -> amount staked
        self.current_epoch = 0
        self.burned = 0
        self.total_supply = 1_000_000
        self.tx_history = []    # historico completo
        self.event_log = []     # log de eventos
        self._genesis()
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        os.makedirs(DATA_DIR, exist_ok=True)

    def _genesis(self):
        genesis = Block(0, [{"type": "genesis", "msg": "Block 0"}],
                        "NETWORK", "0" * 64, 0)
        genesis.finalized = True
        self.chain.append(genesis)
        self._log("Blockchain iniciada. Bloco genesis criado.")

    def _log(self, msg):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        self.event_log.append(entry)

    @property
    def last_block(self):
        return self.chain[-1]

    # ---------------------------------------------------------
    # CONTAS
    # ---------------------------------------------------------
    def create_account(self, address, balance=0, name=None):
        if address in self.accounts:
            return False, "Conta ja existe"
        self.accounts[address] = balance
        self.staked[address] = 0
        self._log(f"Conta criada: {address[:12]}... saldo={balance}")
        return True, f"Conta criada: {address}"

    def get_balance(self, address):
        return self.accounts.get(address, 0)

    def get_total_balance(self, address):
        return self.get_balance(address) + self.staked.get(address, 0)

    # ---------------------------------------------------------
    # STAKING
    # ---------------------------------------------------------
    def stake(self, address, amount):
        if address not in self.accounts:
            return False, "Conta nao existe"
        if amount < self.MIN_STAKE:
            return False, f"Minimo: {self.MIN_STAKE}"
        if self.accounts[address] < amount:
            return False, f"Saldo insuficiente ({self.accounts[address]})"

        self.accounts[address] -= amount
        self.staked[address] = self.staked.get(address, 0) + amount

        if address not in self.validators:
            self.validators[address] = Validator(address, amount)
        else:
            self.validators[address].stake += amount
            self.validators[address].is_active = True

        # registra como transacao
        tx = Transaction(address, "STAKE_CONTRACT", amount, tx_type="stake")
        self.mempool.add(tx.to_dict())

        self._log(f"STAKE: {address[:12]}... travou {amount} coins")
        return True, f"Stake de {amount} realizado. Total staked: {self.staked[address]}"

    def unstake(self, address, amount):
        if self.staked.get(address, 0) < amount:
            return False, "Stake insuficiente"

        self.staked[address] -= amount
        self.accounts[address] += amount

        if address in self.validators:
            self.validators[address].stake -= amount
            if self.validators[address].stake < self.MIN_STAKE:
                self.validators[address].is_active = False

        tx = Transaction(address, address, amount, tx_type="unstake")
        self.mempool.add(tx.to_dict())

        self._log(f"UNSTAKE: {address[:12]}... liberou {amount} coins")
        return True, f"Unstake de {amount}. Saldo livre: {self.accounts[address]}"

    # ---------------------------------------------------------
    # TRANSACOES
    # ---------------------------------------------------------
    def send(self, sender, receiver, amount, tip=0, wallet=None):
        total = amount + self.BASE_FEE + tip

        if sender not in self.accounts:
            return False, "Sender nao existe"
        if receiver not in self.accounts and not receiver.startswith("0xC"):
            return False, "Receiver nao existe"
        if self.accounts[sender] < total:
            return False, f"Saldo insuficiente. Precisa {total}, tem {self.accounts[sender]}"

        signature = None
        public_key = None
        if wallet:
            tx_data = {"sender": sender, "receiver": receiver, "amount": amount}
            signature = wallet.sign(tx_data)
            public_key = wallet.public_key

        tx = Transaction(sender, receiver, amount, tip=tip,
                         signature=signature, public_key=public_key)
        self.mempool.add(tx.to_dict())

        self._log(f"TX: {sender[:12]}.. -> {receiver[:12]}..: {amount} (fee:{self.BASE_FEE} tip:{tip})")
        return True, f"Tx {tx.tx_id} adicionada a mempool (pos: {self.mempool.size()})"

    # ---------------------------------------------------------
    # SELECAO DE VALIDADOR (SLOTS DETERMINISTICOS)
    # ---------------------------------------------------------
    def _get_epoch_seed(self, epoch):
        """Gera seed deterministica pra epoch baseada no hash do ultimo bloco da epoch anterior.
        Todos os nos calculam a mesma seed → mesma escala de slots.
        Similar ao RANDAO do Ethereum (simplificado)."""
        if epoch == 0:
            return hashlib.sha256(b"genesis_seed").hexdigest()
        # pega o hash do ultimo bloco da epoch anterior
        boundary_index = epoch * self.BLOCKS_PER_EPOCH
        if boundary_index > 0 and boundary_index <= len(self.chain):
            return self.chain[boundary_index - 1].hash
        return hashlib.sha256(f"epoch_{epoch}".encode()).hexdigest()

    def get_slot_schedule(self, epoch=None):
        """Retorna a escala de proposers pra uma epoch inteira.
        Cada no calcula independentemente e chega no mesmo resultado."""
        if epoch is None:
            epoch = len(self.chain) // self.BLOCKS_PER_EPOCH
        active = sorted([k for k, v in self.validators.items()
                         if v.is_active and not v.slashed])
        if not active:
            return {}
        seed = self._get_epoch_seed(epoch)
        schedule = {}
        for slot in range(self.BLOCKS_PER_EPOCH):
            # hash deterministico: seed + slot → indice do validador
            slot_hash = hashlib.sha256(f"{seed}:{slot}".encode()).hexdigest()
            # peso por stake: validadores com mais stake tem mais chance
            weights = [self.validators[a].stake for a in active]
            total = sum(weights)
            # usa o hash pra gerar um numero entre 0 e total
            pick = int(slot_hash, 16) % int(total * 100) / 100
            cumulative = 0
            chosen = active[0]
            for i, addr in enumerate(active):
                cumulative += weights[i]
                if pick < cumulative:
                    chosen = addr
                    break
            schedule[slot] = chosen
        return schedule

    def _select_validator(self):
        """Seleciona o proposer do slot atual baseado na escala da epoch."""
        schedule = self.get_slot_schedule()
        if not schedule:
            return None
        slot_in_epoch = (len(self.chain)) % self.BLOCKS_PER_EPOCH
        return schedule.get(slot_in_epoch)

    # ---------------------------------------------------------
    # EXECUCAO DE TRANSACOES (usado pelo proposer e pela validacao)
    # ---------------------------------------------------------
    def _execute_transactions(self, batch, accounts_snapshot, burned):
        """Re-executa transacoes sobre um snapshot de contas.
        Retorna (block_txns, total_tips, accounts_final, burned_final).
        Tanto o proposer quanto os validadores usam este metodo,
        garantindo que todos chegam no mesmo resultado."""
        accounts = dict(accounts_snapshot)  # copia pra nao alterar original
        block_txns = []
        total_tips = 0

        for tx_dict in batch:
            tx_type = tx_dict.get("tx_type", "transfer")

            if tx_type == "transfer":
                sender = tx_dict["sender"]
                receiver = tx_dict["receiver"]
                amount = tx_dict["amount"]
                tip = tx_dict.get("tip", 0)
                total_cost = amount + self.BASE_FEE + tip

                if sender in accounts and accounts[sender] >= total_cost:
                    accounts[sender] -= total_cost
                    if receiver not in accounts:
                        accounts[receiver] = 0
                    accounts[receiver] += amount
                    burned += self.BASE_FEE
                    total_tips += tip
                    tx_dict["status"] = "confirmed"
                else:
                    tx_dict["status"] = "failed"

            elif tx_type in ("stake", "unstake", "contract_deploy", "contract_call"):
                tx_dict["status"] = "confirmed"

            block_txns.append(tx_dict)

        return block_txns, total_tips, accounts, burned

    # ---------------------------------------------------------
    # PRODUCAO DE BLOCO (PROPOSER)
    # ---------------------------------------------------------
    def produce_block(self):
        validator_addr = self._select_validator()
        if not validator_addr:
            return None, "Sem validadores ativos"

        start = time.time()
        validator = self.validators[validator_addr]
        slot_in_epoch = (len(self.chain)) % self.BLOCKS_PER_EPOCH
        epoch = len(self.chain) // self.BLOCKS_PER_EPOCH

        self._log(f"SLOT {slot_in_epoch}/epoch {epoch}: proposer designado = {validator_addr[:12]}...")

        # pega transacoes da mempool (priorizadas por tip)
        batch = self.mempool.get_batch(self.MAX_TXN_PER_BLOCK)

        # executa transacoes (mesma logica que os validadores vao usar)
        block_txns, total_tips, new_accounts, new_burned = self._execute_transactions(
            batch, self.accounts, self.burned
        )

        # aplica estado
        self.accounts = new_accounts
        self.burned = new_burned
        for tx in block_txns:
            self.tx_history.append(tx)

        # recompensa
        reward = self.BASE_REWARD + total_tips
        reward_tx = {
            "tx_id": "rw_" + str(uuid4()).replace("-", "")[:12],
            "sender": "NETWORK",
            "receiver": validator_addr,
            "amount": reward,
            "tx_type": "reward",
            "detail": f"base={self.BASE_REWARD}+tips={total_tips}",
            "timestamp": str(datetime.now()),
            "status": "confirmed",
        }
        block_txns.append(reward_tx)

        if validator_addr not in self.accounts:
            self.accounts[validator_addr] = 0
        self.accounts[validator_addr] += reward
        validator.rewards += reward
        validator.blocks_validated += 1

        new_block = Block(
            index=len(self.chain),
            transactions=block_txns,
            validator=validator_addr,
            previous_hash=self.last_block.hash,
            epoch=epoch,
            slot=slot_in_epoch,
        )

        # state root = hash do estado das contas apos executar tudo
        new_block.state_root = hashlib.sha256(
            json.dumps(self.accounts, sort_keys=True).encode()
        ).hexdigest()
        new_block.hash = new_block.calc_hash()

        # NAO adiciona attestations aqui — os peers vao validar e atestar via gossip
        # o proposer atesta o proprio bloco
        new_block.attestations.append(validator_addr)

        self.chain.append(new_block)
        elapsed = time.time() - start

        if epoch > self.current_epoch:
            self.current_epoch = epoch
            self._log(f"=== NOVA EPOCH: {epoch} ===")

        self._log(f"BLOCO #{new_block.index} PROPOSTO por {validator_addr[:12]}... "
                  f"(slot {slot_in_epoch}, {len(block_txns)} txns, {elapsed:.4f}s) "
                  f"state_root={new_block.state_root[:16]}...")

        return new_block, elapsed

    # ---------------------------------------------------------
    # VALIDACAO DE BLOCO RECEBIDO (re-execucao independente)
    # ---------------------------------------------------------
    def validate_block(self, block_data):
        """Valida um bloco recebido de outro no, re-executando as transacoes.
        Cada no faz isso independentemente — ninguem confia em ninguem.

        Verifica:
          1. Hash do bloco anterior bate com nosso ultimo bloco
          2. O proposer e o designado pra esse slot (escala deterministica)
          3. Re-executa TODAS as transacoes sobre nosso estado local
          4. Calcula state root e compara com o declarado pelo proposer
          5. Se tudo bater → ACEITA. Senao → REJEITA.
        """
        block_index = block_data.get("index", 0)
        declared_state_root = block_data.get("state_root", "")
        declared_validator = block_data.get("validator", "")
        declared_prev_hash = block_data.get("previous_hash", "")
        epoch = block_data.get("epoch", 0)
        slot = block_data.get("slot", 0)

        # 1. Verifica encadeamento: hash anterior bate?
        if declared_prev_hash != self.last_block.hash:
            return False, f"Hash anterior nao bate. Esperado={self.last_block.hash[:16]}... Recebido={declared_prev_hash[:16]}..."

        # 2. Verifica proposer: e o validador designado pra esse slot?
        schedule = self.get_slot_schedule(epoch)
        expected_proposer = schedule.get(slot)
        if expected_proposer and declared_validator != expected_proposer:
            return False, f"Proposer invalido! Slot {slot} designado={expected_proposer[:12]}... recebido={declared_validator[:12]}..."

        # 3. Re-executa transacoes (IGNORA reward tx — recalcula)
        txns_without_reward = [tx for tx in block_data.get("transactions", [])
                               if tx.get("tx_type") != "reward"]

        _, total_tips, simulated_accounts, simulated_burned = self._execute_transactions(
            txns_without_reward, self.accounts, self.burned
        )

        # aplica recompensa no estado simulado
        reward = self.BASE_REWARD + total_tips
        if declared_validator not in simulated_accounts:
            simulated_accounts[declared_validator] = 0
        simulated_accounts[declared_validator] += reward

        # 4. Calcula state root e compara
        computed_state_root = hashlib.sha256(
            json.dumps(simulated_accounts, sort_keys=True).encode()
        ).hexdigest()

        if declared_state_root and computed_state_root != declared_state_root:
            return False, (f"State root NAO BATE! "
                           f"Calculado={computed_state_root[:16]}... "
                           f"Declarado={declared_state_root[:16]}... "
                           f"BLOCO REJEITADO (proposer pode estar trapaceando)")

        # 5. Tudo bateu → retorna estado simulado pra aplicar
        return True, {
            "accounts": simulated_accounts,
            "burned": simulated_burned,
            "reward": reward,
            "state_root": computed_state_root,
        }

    # ---------------------------------------------------------
    # SLASHING
    # ---------------------------------------------------------
    def slash(self, address, reason="violacao"):
        if address not in self.validators:
            return False, "Nao e validador"
        v = self.validators[address]
        penalty = v.stake * self.SLASH_PENALTY
        v.stake -= penalty
        v.slashed = True
        v.is_active = False
        self.staked[address] -= penalty
        self.burned += penalty
        self._log(f"SLASH: {address[:12]}... perdeu {penalty} coins ({reason})")
        return True, f"Slashed: -{penalty} coins ({reason})"

    # ---------------------------------------------------------
    # SMART CONTRACTS
    # ---------------------------------------------------------
    def deploy_contract(self, creator, contract_id, logic):
        if creator not in self.accounts:
            return False, "Conta nao existe"
        contract = SmartContract(contract_id, creator, logic)
        self.contracts[contract_id] = contract

        tx = Transaction(creator, contract.address, 0, tx_type="contract_deploy",
                         data={"contract_id": contract_id})
        self.mempool.add(tx.to_dict())

        self._log(f"CONTRACT DEPLOY: {contract_id} por {creator[:12]}... addr={contract.address[:12]}...")
        return True, f"Contrato '{contract_id}' deployado em {contract.address}"

    def call_contract(self, caller, contract_id, params):
        if contract_id not in self.contracts:
            return False, "Contrato nao encontrado"

        result = self.contracts[contract_id].execute(caller, params, self)

        tx = Transaction(caller, self.contracts[contract_id].address, 0,
                         tx_type="contract_call",
                         data={"contract_id": contract_id, "params": params})
        self.mempool.add(tx.to_dict())

        return result

    # ---------------------------------------------------------
    # VALIDACAO
    # ---------------------------------------------------------
    def is_valid(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.hash != curr.calc_hash():
                return False, f"Hash invalido bloco #{curr.index}"
            if curr.previous_hash != prev.hash:
                return False, f"Encadeamento quebrado bloco #{curr.index}"
        return True, "Cadeia integra"

    # ---------------------------------------------------------
    # PERSISTENCIA (salvar/carregar em disco)
    # ---------------------------------------------------------
    def save(self):
        data = {
            "node_id": self.node_id,
            "chain": [b.to_dict() for b in self.chain],
            "accounts": self.accounts,
            "staked": self.staked,
            "validators": {k: v.to_dict() for k, v in self.validators.items()},
            "burned": self.burned,
            "current_epoch": self.current_epoch,
            "tx_history_count": len(self.tx_history),
        }
        path = os.path.join(DATA_DIR, f"{self.node_id}_chain.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._log(f"Blockchain salva em {path}")
        return path

    def load(self):
        path = os.path.join(DATA_DIR, f"{self.node_id}_chain.json")
        if not os.path.exists(path):
            return False, "Arquivo nao encontrado"
        with open(path) as f:
            data = json.load(f)
        self._log(f"Blockchain carregada de {path} ({len(data['chain'])} blocos)")
        return True, data

    # ---------------------------------------------------------
    # EXPLORER (visualizacao)
    # ---------------------------------------------------------
    def explorer_block(self, index):
        if index >= len(self.chain):
            return None
        b = self.chain[index]
        return b.to_dict()

    def explorer_tx(self, tx_id):
        for tx in self.tx_history:
            if tx["tx_id"] == tx_id:
                return tx
        return None

    def explorer_account(self, address):
        txns = [tx for tx in self.tx_history
                if tx.get("sender") == address or tx.get("receiver") == address]
        return {
            "address": address,
            "balance": self.get_balance(address),
            "staked": self.staked.get(address, 0),
            "total": self.get_total_balance(address),
            "transactions": len(txns),
            "is_validator": address in self.validators,
        }

    # ---------------------------------------------------------
    # PRINT
    # ---------------------------------------------------------
    def check_finality(self, block):
        """Verifica se o bloco atingiu finalidade (>= 66% dos validadores atestaram)."""
        active = [v for v in self.validators.values() if v.is_active and not v.slashed]
        if len(active) == 0:
            return False
        ratio = len(block.attestations) / len(active)
        if ratio >= self.FINALITY_THRESHOLD:
            block.finalized = True
            for tx in block.transactions:
                tx["status"] = "finalized"
            self._log(f"BLOCO #{block.index} FINALIZADO! ({len(block.attestations)}/{len(active)} attestations = {ratio:.0%})")
            return True
        return False

    def print_chain(self):
        print("\n" + "=" * 70)
        print(f"  BLOCKCHAIN [{self.node_id}] - {len(self.chain)} blocos")
        print("=" * 70)
        for b in self.chain:
            status = "[FINAL]" if b.finalized else "[pend.]"
            att = len(b.attestations)
            print(f"\n  +-- Bloco #{b.index} {status} (slot {b.slot}, attestations: {att})")
            print(f"  |  Validator:  {b.validator}")
            print(f"  |  Epoch:      {b.epoch}")
            print(f"  |  Hash:       {b.hash}")
            print(f"  |  Prev:       {b.previous_hash}")
            print(f"  |  Merkle:     {b.merkle_root[:32]}...")
            print(f"  |  Txns:       {len(b.transactions)}")
            for tx in b.transactions:
                t = tx.get("tx_type", "?")
                if t == "reward":
                    print(f"  |    [REWARD] {tx['receiver'][:12]}...: +{tx['amount']} ({tx.get('detail','')})")
                elif t == "genesis":
                    print(f"  |    [GENESIS]")
                elif t == "stake":
                    print(f"  |    [STAKE] {tx['sender'][:12]}...: {tx['amount']}")
                elif t == "unstake":
                    print(f"  |    [UNSTAKE] {tx['sender'][:12]}...: {tx['amount']}")
                elif t == "contract_deploy":
                    print(f"  |    [DEPLOY] {tx.get('data',{}).get('contract_id','?')}")
                elif t == "contract_call":
                    print(f"  |    [CALL] {tx.get('data',{}).get('contract_id','?')}")
                else:
                    print(f"  |    {tx.get('sender','?')[:12]}.. -> {tx.get('receiver','?')[:12]}..: {tx.get('amount',0)} (tip:{tx.get('tip',0)})")
            if b.index < len(self.chain) - 1:
                print("  |")
                print("  +====== CHAIN ======+")
                print("  |")
        print("  +-- FIM")
        print("=" * 70)

    def print_validators(self):
        print("\n  VALIDADORES:")
        print("  " + "-" * 60)
        for addr, v in self.validators.items():
            s = "SLASHED" if v.slashed else ("active" if v.is_active else "inactive")
            print(f"  {addr[:16]}... | stake:{v.stake:>8.2f} | blocos:{v.blocks_validated} | reward:{v.rewards:.2f} | {s}")

    def print_accounts(self):
        print("\n  CONTAS:")
        print("  " + "-" * 60)
        for addr in sorted(self.accounts.keys()):
            bal = self.accounts[addr]
            stk = self.staked.get(addr, 0)
            print(f"  {addr[:16]}... | livre:{bal:>10.2f} | staked:{stk:>8.2f} | total:{bal+stk:>10.2f}")

    def print_stats(self):
        print("\n  STATS:")
        print("  " + "-" * 40)
        print(f"  Node:            {self.node_id}")
        print(f"  Blocos:          {len(self.chain)}")
        print(f"  Epoch:           {self.current_epoch}")
        print(f"  Validadores:     {len(self.validators)}")
        print(f"  Mempool:         {self.mempool.size()} txns")
        print(f"  Fees queimadas:  {self.burned:.4f}")
        print(f"  Supply atual:    {self.total_supply - self.burned:.4f}")
        finalized = sum(1 for b in self.chain if b.finalized)
        print(f"  Finalizados:     {finalized}/{len(self.chain)}")
        print(f"  Historico txns:  {len(self.tx_history)}")

    def print_log(self, last_n=20):
        print(f"\n  EVENT LOG (ultimos {last_n}):")
        print("  " + "-" * 50)
        for entry in self.event_log[-last_n:]:
            print(f"  {entry}")
