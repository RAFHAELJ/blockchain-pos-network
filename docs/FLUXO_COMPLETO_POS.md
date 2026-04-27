# ⛓️ Fluxo Completo: Blockchain Proof-of-Stake

> Documento didático explicando passo a passo como funciona uma blockchain PoS,
> desde a criação da carteira até a finalização de um bloco.
> Baseado na implementação deste projeto e no Ethereum 2.0.

---

## 📑 Índice

1. [Criar Carteira (Wallet)](#1-criar-carteira-wallet)
2. [Criar Conta na Blockchain](#2-criar-conta-na-blockchain)
3. [Fazer Stake (virar Validador)](#3-fazer-stake-virar-validador)
4. [Escala de Slots (quem valida quando)](#4-escala-de-slots-quem-valida-quando)
5. [Enviar Transação](#5-enviar-transação)
6. [Mempool (fila de espera)](#6-mempool-fila-de-espera)
7. [Proposer Monta o Bloco](#7-proposer-monta-o-bloco)
8. [Validadores Re-executam e Atestam](#8-validadores-re-executam-e-atestam)
9. [Finalidade (bloco vira irreversível)](#9-finalidade-bloco-vira-irreversível)
10. [Smart Contracts](#10-smart-contracts)
11. [Protocolo Gossip (propagação na rede)](#11-protocolo-gossip-propagação-na-rede)
12. [Slashing (punição)](#12-slashing-punição)
13. [Epochs e Ciclo Completo](#13-epochs-e-ciclo-completo)
14. [Comparação: Este Projeto vs Ethereum Real](#14-comparação-este-projeto-vs-ethereum-real)

---

## 1. Criar Carteira (Wallet)

A carteira é a identidade do usuário na blockchain. Tudo começa aqui.

### O que acontece

```
Usuário pede: "quero uma carteira"
        │
        ▼
┌─────────────────────────────────┐
│  1. Gera CHAVE PRIVADA          │  ← 256 bits aleatórios (segredo)
│     ex: a3f8c1...64 chars hex   │
│                                 │
│  2. Deriva CHAVE PÚBLICA        │  ← hash da chave privada
│     ex: 7b2e9d...64 chars hex   │
│                                 │
│  3. Deriva ENDEREÇO             │  ← hash da chave pública
│     ex: 0x1a2b3c...40 chars hex │
└─────────────────────────────────┘
```

### Analogia

| Conceito | Analogia |
|----------|----------|
| Chave Privada | Senha do banco (só você sabe) |
| Chave Pública | Número da conta (qualquer um pode ver) |
| Endereço | Seu "PIX" (derivado da conta) |

### No código (`wallet.py`)

```python
class Wallet:
    def __init__(self, name):
        self.private_key = secrets.token_hex(32)          # 1. gera segredo
        self.public_key = hash(self.private_key)           # 2. deriva pública
        self.address = "0x" + hash(self.public_key)[:40]   # 3. deriva endereço
```

### Via API

```bash
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_createWallet","params":[{"name":"Alice","balance":500}],"id":1}'
```

### Regra fundamental

```
Chave Privada → Chave Pública → Endereço
     ✅              ✅            ✅      (caminho de ida)

Endereço → Chave Pública → Chave Privada
     ❌              ❌            ❌      (impossível voltar)
```

**Quem tem a chave privada, controla os fundos. Perdeu = perdeu pra sempre.**

---

## 2. Criar Conta na Blockchain

Depois de ter a carteira, o endereço é registrado na blockchain.

### O que acontece

```
Carteira criada (local)
        │
        ▼
┌─────────────────────────────────┐
│  Blockchain registra:           │
│                                 │
│  accounts["0x1a2b3c..."] = 500  │  ← saldo livre
│  staked["0x1a2b3c..."]   = 0    │  ← saldo travado (stake)
└─────────────────────────────────┘
        │
        ▼
  Gossip propaga pra todos os nós
  (Node-RJ e Node-MG também criam a conta)
```

### No código (`core.py`)

```python
def create_account(self, address, balance=0):
    self.accounts[address] = balance   # saldo livre
    self.staked[address] = 0           # nada travado ainda
```

### Estado da conta

```
┌──────────────────────────────┐
│  Conta: 0x1a2b3c...          │
│  ├── Saldo livre:  500       │  ← pode gastar
│  ├── Saldo staked: 0         │  ← travado (não pode gastar)
│  └── Total:        500       │
└──────────────────────────────┘
```

---

## 3. Fazer Stake (virar Validador)

Para participar do consenso (validar blocos), é preciso travar moedas como garantia.

### O que acontece

```
Alice tem 500 coins livres
        │
        ▼  pos_stake(address, 200)
┌─────────────────────────────────┐
│  1. Verifica: tem saldo? (500 ≥ 200) ✅  │
│  2. Verifica: mínimo 32? (200 ≥ 32)  ✅  │
│  3. Debita saldo livre:  500 → 300        │
│  4. Credita staked:      0   → 200        │
│  5. Registra como Validador               │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  Validador criado:              │
│  ├── address: 0xAlice...        │
│  ├── stake: 200                 │
│  ├── is_active: true            │
│  ├── slashed: false             │
│  ├── blocks_validated: 0        │
│  └── rewards: 0                 │
└─────────────────────────────────┘
        │
        ▼
  Gossip propaga stake pra toda a rede
```

### Por que fazer stake?

```
INCENTIVO:
  ✅ Ganha recompensa por validar blocos (BASE_REWARD = 5 + tips)
  ✅ Quanto mais stake, mais chance de ser escolhido proposer

RISCO:
  ❌ Moedas ficam travadas (não pode gastar)
  ❌ Se agir mal → SLASHING (perde 50% do stake)
```

### Mínimo de stake

```
Neste projeto:  32 coins
Ethereum real:  32 ETH (~US$80.000+)
```



---

## 4. Escala de Slots (quem valida quando)

No início de cada epoch, **todos os nós calculam independentemente** quem propõe em cada slot — e chegam no **mesmo resultado**.

### O que acontece

```
Epoch 0 começa (3 slots por epoch neste projeto)
        │
        ▼
Todos os nós calculam a escala:
┌─────────────────────────────────────────────┐
│  Inputs (públicos, na chain):               │
│  ├── Lista de validadores: [Alice, Bob]     │
│  ├── Stakes: [200, 100]                     │
│  └── Seed: hash do último bloco da epoch    │
│            anterior (determinístico)        │
│                                             │
│  Algoritmo:                                 │
│  seed + slot_number → hash → peso por stake │
│                                             │
│  Resultado (IGUAL em todos os nós):         │
│  ├── Slot 0 → Alice (proposer)              │
│  ├── Slot 1 → Bob   (proposer)              │
│  └── Slot 2 → Alice (proposer)              │
└─────────────────────────────────────────────┘
```

### Por que é determinístico?

```
Node-SP calcula: seed="abc123" + slot=0 → hash → Alice
Node-RJ calcula: seed="abc123" + slot=0 → hash → Alice
Node-MG calcula: seed="abc123" + slot=0 → hash → Alice

Mesmos inputs → mesmo resultado → ninguém precisa perguntar pra ninguém
```

### No código (`core.py`)

```python
def get_slot_schedule(self, epoch):
    seed = self._get_epoch_seed(epoch)     # hash do último bloco da epoch anterior
    schedule = {}
    for slot in range(BLOCKS_PER_EPOCH):
        slot_hash = hash(seed + slot)       # determinístico
        chosen = select_by_weight(slot_hash, validators, stakes)
        schedule[slot] = chosen
    return schedule
```

### Via API

```bash
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_getSlotSchedule","params":[],"id":1}'

# Resposta:
# {"slot_0": "0xAlice...", "slot_1": "0xBob...", "slot_2": "0xAlice..."}
```

### Ethereum real vs Este projeto

| Aspecto | Este projeto | Ethereum |
|---------|-------------|----------|
| Slots por epoch | 3 | 32 |
| Tempo por slot | manual | 12 segundos |
| Seed | hash do bloco anterior | RANDAO (acumulado) |
| Slot vazio | não implementado | se proposer não aparecer |

---

## 5. Enviar Transação

Quando alguém quer transferir moedas.

### O que acontece

```
Alice quer enviar 50 coins pra Bob
        │
        ▼
┌─────────────────────────────────────────┐
│  1. VALIDAÇÕES INICIAIS                 │
│     ├── Alice existe?              ✅   │
│     ├── Bob existe?                ✅   │
│     ├── Custo total:                    │
│     │   amount(50) + fee(0.01) + tip(1) │
│     │   = 51.01                         │
│     └── Alice tem 300 ≥ 51.01?     ✅   │
│                                         │
│  2. ASSINATURA (se tem wallet)          │
│     ├── Dados: {sender, receiver, 50}   │
│     ├── Assina com chave privada        │
│     └── Gera signature (prova que é a   │
│         Alice mesmo)                    │
│                                         │
│  3. CRIA TRANSAÇÃO                      │
│     ├── tx_id: "a1b2c3d4..."            │
│     ├── sender: 0xAlice                 │
│     ├── receiver: 0xBob                 │
│     ├── amount: 50                      │
│     ├── tip: 1 (prioridade)             │
│     ├── base_fee: 0.01 (queimada)       │
│     └── status: "pending"               │
│                                         │
│  4. ADICIONA NA MEMPOOL                 │
│     └── Ordenada por tip (maior = antes)│
│                                         │
│  5. GOSSIP                              │
│     └── Propaga tx pra todos os peers   │
└─────────────────────────────────────────┘
```

### Taxas explicadas

```
Custo total de uma transação:
┌──────────────────────────────────────┐
│  amount   = 50.00  → vai pro Bob     │
│  base_fee =  0.01  → QUEIMADA 🔥     │
│  tip      =  1.00  → vai pro validador│
│  ─────────────────────                │
│  total    = 51.01  → debitado da Alice│
└──────────────────────────────────────┘

Base fee queimada = reduz supply total (deflação, estilo EIP-1559)
Tip = incentivo pro validador incluir sua tx primeiro
```

### IMPORTANTE: a transação NÃO é executada agora

```
Neste momento:
  ✅ Tx foi CRIADA e validada superficialmente
  ✅ Tx está na MEMPOOL esperando
  ❌ Saldo de Alice NÃO foi debitado ainda
  ❌ Bob NÃO recebeu nada ainda

A execução real acontece quando o PROPOSER inclui a tx num bloco.
```

---

## 6. Mempool (fila de espera)

A mempool é onde as transações ficam esperando para serem incluídas num bloco.

### Como funciona

```
Mempool (ordenada por tip — maior prioridade primeiro)
┌─────────────────────────────────────────────┐
│  Posição 1: Tx "d4e5f6" tip=5.0  ← PRIMEIRO│
│  Posição 2: Tx "a1b2c3" tip=1.0            │
│  Posição 3: Tx "g7h8i9" tip=0.5            │
│  Posição 4: Tx "j0k1l2" tip=0.1            │
│  Posição 5: Tx "m3n4o5" tip=0.0  ← ÚLTIMO  │
└─────────────────────────────────────────────┘
        │
        ▼  Proposer pega batch (máx 10 txs)
┌─────────────────────────────────────────────┐
│  Bloco vai conter as 5 txs acima            │
│  (ou até MAX_TXN_PER_BLOCK = 10)            │
└─────────────────────────────────────────────┘
```

### Por que tip importa?

```
Rede congestionada (muitas txs, poucos slots):

  Tx com tip=10  → entra no próximo bloco ✅
  Tx com tip=0.1 → pode esperar vários blocos ⏳
  Tx com tip=0   → pode nunca ser incluída ❌

O validador quer maximizar seu lucro → prioriza txs com tip maior.
```

### Cada nó tem sua própria mempool

```
Node-SP mempool: [tx1, tx2, tx3, tx4]
Node-RJ mempool: [tx1, tx2, tx3]       ← pode ser diferente
Node-MG mempool: [tx1, tx2, tx3, tx4]

Via gossip, as txs se propagam, mas pode haver diferenças temporárias.
```

