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



---

## 7. Proposer Monta o Bloco

O validador designado para o slot atual **propõe** o bloco.

### Fluxo completo

```
Slot 1 da Epoch 0 → Proposer designado: Bob
        │
        ▼
┌──────────────────────────────────────────────────┐
│  PASSO 1: Confirma que é o proposer              │
│  schedule = get_slot_schedule()                   │
│  schedule[slot_1] = "0xBob" → "sou eu!"          │
│                                                   │
│  PASSO 2: Pega transações da mempool              │
│  batch = mempool.get_batch(10)                    │
│  → [tx_alice_bob_50, tx_carol_dave_20, ...]       │
│                                                   │
│  PASSO 3: Executa cada transação                  │
│  ┌────────────────────────────────────────┐       │
│  │ tx_alice_bob_50:                       │       │
│  │   Alice: 300 - 51.01 = 248.99         │       │
│  │   Bob:   100 + 50.00 = 150.00         │       │
│  │   burned: +0.01 (base fee queimada)    │       │
│  │   tips:  +1.00 (pro proposer)          │       │
│  │   status: "confirmed" ✅               │       │
│  │                                        │       │
│  │ tx_carol_dave_20:                      │       │
│  │   Carol: 200 - 20.51 = 179.49         │       │
│  │   Dave:  50  + 20.00 = 70.00          │       │
│  │   burned: +0.01                        │       │
│  │   tips:  +0.50                         │       │
│  │   status: "confirmed" ✅               │       │
│  └────────────────────────────────────────┘       │
│                                                   │
│  PASSO 4: Adiciona transação de recompensa        │
│  reward = BASE_REWARD(5) + total_tips(1.50)       │
│  reward_tx: NETWORK → Bob: 6.50                   │
│  Bob: 150.00 + 6.50 = 156.50                     │
│                                                   │
│  PASSO 5: Calcula STATE ROOT                      │
│  state_root = hash(todas_as_contas_atualizadas)   │
│  → "ca38e87c3165c5f5..."                          │
│  (essa é a "prova" de que o estado está correto)  │
│                                                   │
│  PASSO 6: Monta o bloco                           │
│  ┌────────────────────────────────────────┐       │
│  │ Block #1                               │       │
│  │ ├── index: 1                           │       │
│  │ ├── epoch: 0                           │       │
│  │ ├── slot: 1                            │       │
│  │ ├── validator: 0xBob                   │       │
│  │ ├── previous_hash: hash(block_0)       │       │
│  │ ├── transactions: [tx1, tx2, reward]   │       │
│  │ ├── merkle_root: hash(todas_as_txs)    │       │
│  │ ├── state_root: "ca38e87c..."          │       │
│  │ ├── hash: hash(tudo_acima)             │       │
│  │ ├── attestations: [0xBob]              │       │
│  │ └── finalized: false                   │       │
│  └────────────────────────────────────────┘       │
│                                                   │
│  PASSO 7: Propaga via GOSSIP                      │
│  → Envia bloco pra Node-RJ e Node-MG             │
└──────────────────────────────────────────────────┘
```

### O que é o State Root?

```
State root = hash de TODAS as contas e saldos após executar o bloco

Antes do bloco:                    Depois do bloco:
  Alice: 300.00                      Alice: 248.99
  Bob:   100.00                      Bob:   156.50
  Carol: 200.00                      Carol: 179.49
  Dave:   50.00                      Dave:   70.00

state_root = SHA256({
  "0xAlice": 248.99,
  "0xBob": 156.50,
  "0xCarol": 179.49,
  "0xDave": 70.00
})
→ "ca38e87c3165c5f5..."

Se QUALQUER saldo estiver errado por 0.01, o hash muda completamente.
É assim que os validadores detectam trapaça.
```

### O que é o Merkle Root?

```
Merkle root = hash de todas as transações do bloco (árvore de hashes)

         merkle_root
          /        \
     hash(AB)    hash(CD)
      /    \      /    \
  hash(A) hash(B) hash(C) hash(reward)

Se alguém alterar UMA transação, o merkle root muda.
Serve pra provar que uma tx está no bloco sem baixar todas.
```

---

## 8. Validadores Re-executam e Atestam

Quando um nó recebe o bloco via gossip, ele **NÃO confia** no proposer. Ele refaz todo o trabalho.

### Fluxo no nó receptor

```
Node-RJ recebe bloco #1 via gossip
        │
        ▼
┌──────────────────────────────────────────────────┐
│  VERIFICAÇÃO 1: Encadeamento                     │
│  ├── previous_hash do bloco recebido             │
│  │   bate com o hash do meu último bloco?        │
│  └── "9faa21c7..." == "9faa21c7..." → ✅          │
│                                                   │
│  VERIFICAÇÃO 2: Proposer correto                  │
│  ├── Calculo a escala de slots localmente         │
│  │   schedule = get_slot_schedule(epoch=0)        │
│  │   slot_1 → 0xBob                              │
│  ├── Bloco diz validator = 0xBob                  │
│  └── Bate? → ✅                                    │
│                                                   │
│  VERIFICAÇÃO 3: Re-execução de transações         │
│  ├── Pego as MESMAS txs que estão no bloco        │
│  ├── Executo uma por uma sobre MEU estado local   │
│  │   ┌──────────────────────────────────┐         │
│  │   │ tx_alice_bob_50:                 │         │
│  │   │   Alice: 300 - 51.01 = 248.99   │         │
│  │   │   Bob:   100 + 50.00 = 150.00   │         │
│  │   │ tx_carol_dave_20:               │         │
│  │   │   Carol: 200 - 20.51 = 179.49   │         │
│  │   │   Dave:   50 + 20.00 = 70.00    │         │
│  │   │ reward:                          │         │
│  │   │   Bob: 150 + 6.50 = 156.50      │         │
│  │   └──────────────────────────────────┘         │
│  └── Calculo MEU state root                       │
│                                                   │
│  VERIFICAÇÃO 4: State root bate?                  │
│  ├── Meu cálculo:     "ca38e87c3165c5f5..."       │
│  ├── Proposer declarou: "ca38e87c3165c5f5..."     │
│  └── IGUAIS → ✅ BLOCO VÁLIDO!                     │
│                                                   │
│  RESULTADO: ACEITA o bloco                        │
│  ├── Aplica estado calculado LOCALMENTE           │
│  │   (não usa o estado que o proposer enviou)     │
│  ├── Adiciona bloco na chain                      │
│  └── Envia ATTESTATION (voto de aprovação)        │
└──────────────────────────────────────────────────┘
```

### E se o proposer tentar trapacear?

```
Proposer malicioso tenta:
  "Vou dizer que meu saldo é 999999"
        │
        ▼
┌──────────────────────────────────────────────────┐
│  Node-RJ re-executa as txs:                      │
│  ├── Calcula state root: "ca38e87c..."           │
│  ├── Proposer declarou:  "FAKE_ROOT..."          │
│  └── NÃO BATE → ❌ BLOCO REJEITADO!              │
│                                                   │
│  Log: "BLOCO #1 REJEITADO! State root NAO BATE!  │
│        proposer pode estar trapaceando"           │
│                                                   │
│  Node-RJ NÃO atesta, NÃO adiciona na chain.      │
└──────────────────────────────────────────────────┘
```

### Proposer errado tenta propor

```
Hacker tenta propor no slot do Bob:
        │
        ▼
┌──────────────────────────────────────────────────┐
│  Node-RJ verifica escala:                        │
│  ├── Slot 1 designado: 0xBob                    │
│  ├── Bloco diz validator: 0xHacker              │
│  └── NÃO BATE → ❌ BLOCO REJEITADO!              │
│                                                   │
│  Log: "Proposer invalido! Slot 1 designado=Bob   │
│        recebido=Hacker"                           │
└──────────────────────────────────────────────────┘
```

### Diagrama completo: Proposer → Validadores

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Node-SP    │         │  Node-RJ    │         │  Node-MG    │
│  (Proposer) │         │ (Validador) │         │ (Validador) │
│             │         │             │         │             │
│ Monta bloco │         │             │         │             │
│ Executa txs │         │             │         │             │
│ State root  │         │             │         │             │
│      │      │         │             │         │             │
│      ▼      │         │             │         │             │
│  GOSSIP ────────────→ │ Recebe      │         │             │
│             │    ────────────────────────────→ │ Recebe      │
│             │         │             │         │             │
│             │         │ Re-executa  │         │ Re-executa  │
│             │         │ txs         │         │ txs         │
│             │         │ Confere     │         │ Confere     │
│             │         │ state root  │         │ state root  │
│             │         │      │      │         │      │      │
│             │         │      ▼      │         │      ▼      │
│             │         │ Bate? ✅    │         │ Bate? ✅    │
│             │         │ ATESTA ─────────────→ │ ATESTA      │
│             │         │             │         │             │
│  Bloco tem  │         │             │         │             │
│  3 attest.  │ ←────── │             │ ←────── │             │
│  ≥ 66%      │         │             │         │             │
│  FINALIZADO!│         │             │         │             │
└─────────────┘         └─────────────┘         └─────────────┘
```



---

## 9. Finalidade (bloco vira irreversível)

Um bloco só é considerado **final** quando validadores suficientes atestaram.

### Fluxo

```
Bloco #1 proposto por Bob
├── Bob atesta (proposer sempre atesta o próprio)     → 1 attestation
├── Node-RJ valida e atesta                           → 2 attestations
├── Node-MG valida e atesta                           → 3 attestations
│
▼ Verifica finalidade:
  Validadores ativos: 3 (Alice, Bob, Carol)
  Attestations: 3
  Ratio: 3/3 = 100% ≥ 66% (FINALITY_THRESHOLD)
  → BLOCO FINALIZADO! ✅
```

### Status de uma transação

```
pending → confirmed → finalized

pending:    Está na mempool, esperando ser incluída num bloco
confirmed:  Foi incluída num bloco, mas bloco ainda não é final
finalized:  Bloco foi finalizado — IRREVERSÍVEL
```

### No código (`core.py`)

```python
def check_finality(self, block):
    active = [v for v in validators if v.is_active and not v.slashed]
    ratio = len(block.attestations) / len(active)
    if ratio >= 0.66:  # 66% dos validadores atestaram
        block.finalized = True
```

### Ethereum real

```
Neste projeto:  ≥ 66% attestations no bloco → finalizado
Ethereum real:  Casper FFG — precisa de 2 epochs inteiras:
                Epoch 0: blocos produzidos
                Epoch 1: validadores votam "justified"
                Epoch 2: epoch 0 vira "finalized"
                
                Reverter exigiria destruir ⅓ do stake total
                (bilhões de dólares)
```

---

## 10. Smart Contracts

Programas que rodam na blockchain. Cada nó executa localmente.

### Tipos disponíveis

```
┌─────────────────────────────────────────────────┐
│  token        │ ERC-20: mint, transfer, balance │
│  nft          │ ERC-721: mint, transfer, owner  │
│  crowdfunding │ Vaquinha: contribute, refund     │
│  dex          │ Exchange AMM: swap A↔B           │
│  voting       │ Votação: create, vote, results   │
└─────────────────────────────────────────────────┘
```

### Fluxo de deploy

```
Alice faz deploy do token "MeuToken"
        │
        ▼
┌──────────────────────────────────────────┐
│  1. Cria SmartContract                   │
│     ├── contract_id: "MeuToken"          │
│     ├── address: 0xC + hash("MeuToken")  │
│     ├── creator: 0xAlice                 │
│     ├── logic: token_erc20 (função)      │
│     └── state: {name, symbol, balances}  │
│                                          │
│  2. Registra na blockchain               │
│     contracts["MeuToken"] = contrato     │
│                                          │
│  3. Cria tx de deploy na mempool         │
│                                          │
│  4. Gossip propaga pra todos os nós      │
│     (cada nó cria o mesmo contrato)      │
└──────────────────────────────────────────┘
```

### Fluxo de chamada

```
Alice chama: mint 10000 tokens
        │
        ▼
┌──────────────────────────────────────────┐
│  contract.execute(caller, params, bc)    │
│                                          │
│  Dentro do token_erc20:                  │
│  ├── action = "mint"                     │
│  ├── state["balances"]["0xAlice"] += 10k │
│  ├── state["total_supply"] += 10000      │
│  └── return "Mint: 10000 MTK para Alice" │
└──────────────────────────────────────────┘
```

### Via API

```bash
# Deploy
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_deployContract",
       "params":[{"creator":"0xAlice...","id":"MeuToken","type":"token",
                  "state":{"name":"MeuToken","symbol":"MTK"}}],"id":1}'

# Mint
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_callContract",
       "params":[{"caller":"0xAlice...","id":"MeuToken",
                  "params":{"action":"mint","amount":10000}}],"id":2}'

# Consultar saldo
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_callContract",
       "params":[{"caller":"0xAlice...","id":"MeuToken",
                  "params":{"action":"balance_of"}}],"id":3}'
```

---

## 11. Protocolo Gossip (propagação na rede)

Como os nós se comunicam — fofoca peer-to-peer.

### Fluxo

```
Evento acontece no Node-SP (ex: nova transação)
        │
        ▼
┌──────────────────────────────────────────────────┐
│  1. Node-SP cria mensagem gossip                 │
│     ├── gossip_id: "a1b2c3d4" (único)            │
│     ├── ttl: 5 (máximo de saltos)                │
│     ├── origin: "node-SP"                        │
│     └── data: {from, to, value, tip}             │
│                                                   │
│  2. Envia HTTP POST pra cada peer                │
│     ├── → http://node-rj:8546  (thread separada) │
│     └── → http://node-mg:8547  (thread separada) │
└──────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────┐    ┌──────────────────┐
│  Node-RJ recebe  │    │  Node-MG recebe  │
│  ├── gossip_id   │    │  ├── gossip_id   │
│  │   já vi? NÃO  │    │  │   já vi? NÃO  │
│  ├── Processa    │    │  ├── Processa    │
│  ├── Marca como  │    │  ├── Marca como  │
│  │   "já visto"  │    │  │   "já visto"  │
│  └── Re-fofoca   │    │  └── Re-fofoca   │
│      ttl=4       │    │      ttl=4       │
│      │           │    │      │           │
│      ▼           │    │      ▼           │
│  → Node-MG      │    │  → Node-RJ      │
│    já viu!       │    │    já viu!       │
│    IGNORA ✅     │    │    IGNORA ✅     │
└──────────────────┘    └──────────────────┘
```

### Proteções contra loops

```
1. gossip_id único    → cada mensagem tem ID, se já viu, ignora
2. TTL (time to live) → decrementado a cada salto, morre em 0
3. seen_gossip set    → conjunto de IDs já processados
4. Limite de memória  → limpa set quando passa de 10.000 IDs
```

### Tipos de gossip

| Tipo | Quando | O que propaga |
|------|--------|---------------|
| `gossip_tx` | Nova transação | sender, receiver, amount, tip |
| `gossip_block` | Bloco produzido | bloco completo + estado |
| `gossip_account` | Nova conta | address, balance |
| `gossip_stake` | Novo stake | address, amount |
| `gossip_contract` | Deploy de contrato | creator, id, type, state |
| `gossip_slash` | Validador punido | address, reason |

---

## 12. Slashing (punição)

Validadores que agem mal perdem parte do stake.

### Quando acontece

```
Situações que levam a slashing:
├── Propor dois blocos diferentes pro mesmo slot (equivocação)
├── Atestar blocos conflitantes
├── Ficar offline por muito tempo (inatividade)
└── Qualquer comportamento que prejudique a rede
```

### Fluxo

```
Validador Alice agiu mal
        │
        ▼
┌──────────────────────────────────────────┐
│  slash("0xAlice", "double_proposal")     │
│                                          │
│  1. Calcula penalidade:                  │
│     penalty = stake(200) × 50% = 100     │
│                                          │
│  2. Aplica:                              │
│     ├── Alice stake: 200 → 100           │
│     ├── Alice slashed: true              │
│     ├── Alice is_active: false           │
│     └── burned += 100 (moedas destruídas)│
│                                          │
│  3. Gossip propaga slashing              │
│     → todos os nós aplicam a punição     │
│                                          │
│  Resultado:                              │
│  ├── Alice perde 100 coins (50% do stake)│
│  ├── Alice não pode mais validar         │
│  └── Moedas são QUEIMADAS (não vão pra   │
│      ninguém — saem de circulação)       │
└──────────────────────────────────────────┘
```

### Via API

```bash
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_slash",
       "params":[{"address":"0xAlice...","reason":"double_proposal"}],"id":1}'
```

---

## 13. Epochs e Ciclo Completo

Uma epoch é um ciclo de N blocos. Ao final, nova escala de slots é calculada.

### Ciclo visual

```
═══════════════════════════════════════════════════════════
  EPOCH 0 (blocos 0-2)
═══════════════════════════════════════════════════════════

  Slot 0 → Alice propõe Bloco #1
           ├── Txs executadas
           ├── RJ e MG validam e atestam
           └── Finalizado ✅

  Slot 1 → Bob propõe Bloco #2
           ├── Txs executadas
           ├── RJ e MG validam e atestam
           └── Finalizado ✅

  Slot 2 → Alice propõe Bloco #3
           ├── Txs executadas
           ├── RJ e MG validam e atestam
           └── Finalizado ✅

═══════════════════════════════════════════════════════════
  EPOCH 1 (blocos 3-5) — NOVA ESCALA!
═══════════════════════════════════════════════════════════

  Nova seed = hash(Bloco #3)  ← último bloco da epoch 0
  Nova escala calculada por todos os nós:
    Slot 0 → Bob
    Slot 1 → Alice
    Slot 2 → Bob

  Slot 0 → Bob propõe Bloco #4
           ...

═══════════════════════════════════════════════════════════
```

### Resumo do ciclo de vida completo

```
1. CARTEIRA    → Gera chaves (privada/pública/endereço)
2. CONTA       → Registra endereço na blockchain
3. STAKE       → Trava moedas, vira validador
4. ESCALA      → Todos calculam quem propõe em cada slot
5. TRANSAÇÃO   → Usuário envia, vai pra mempool
6. GOSSIP TX   → Mempool propaga pra todos os nós
7. PROPOSER    → Validador designado monta o bloco
                  ├── Pega txs da mempool
                  ├── Executa cada uma
                  ├── Calcula state root
                  └── Propaga bloco via gossip
8. VALIDAÇÃO   → Cada nó receptor:
                  ├── Confere hash anterior
                  ├── Confere proposer correto
                  ├── Re-executa TODAS as txs
                  ├── Confere state root
                  └── Se OK → atesta
9. FINALIDADE  → ≥ 66% atestaram → bloco finalizado
10. EPOCH      → Após N blocos, nova epoch, nova escala
11. REPEAT     → Volta pro passo 4
```



---

## 14. Comparação: Este Projeto vs Ethereum Real

### Tabela completa

| Aspecto | Este Projeto | Ethereum 2.0 |
|---------|-------------|---------------|
| **Carteira** | ECDSA simplificado (HMAC) | ECDSA secp256k1 real |
| **Endereço** | hash da public key | Keccak-256 da public key |
| **Stake mínimo** | 32 coins | 32 ETH (~US$80k+) |
| **Slots por epoch** | 3 | 32 |
| **Tempo por slot** | manual (API call) | 12 segundos (relógio) |
| **Seed do sorteio** | hash do último bloco | RANDAO (acumulado on-chain) |
| **Seleção de proposer** | determinística por hash+peso | determinística RANDAO+peso |
| **Committees** | todos validam | 128+ attesters por slot |
| **Re-execução** | ✅ validate_block() | ✅ EVM re-executa tudo |
| **State root** | SHA-256 do JSON de contas | Merkle Patricia Trie |
| **Attestations** | reais (após validação) | BLS signatures (agregáveis) |
| **Finalidade** | 66% attestations no bloco | Casper FFG (2 epochs) |
| **Slashing** | 50% do stake | variável (mín ~1 ETH) |
| **Smart contracts** | funções Python | EVM bytecode (Solidity) |
| **P2P** | HTTP gossip simples | libp2p gossipsub |
| **Clientes** | 1 (rpc_server.py) | 2 (consensus + execution) |
| **Persistência** | JSON em disco | LevelDB / RocksDB |
| **Rede** | 3 nós localhost | ~1 milhão de validadores |

### O que este projeto ensina corretamente

```
✅ Conceito de Proof of Stake (stake como garantia)
✅ Seleção determinística de proposers (todos calculam igual)
✅ Re-execução independente de transações (ninguém confia em ninguém)
✅ State root como prova de integridade
✅ Attestations reais (só atesta se validação passar)
✅ Rejeição de blocos inválidos
✅ Finalidade baseada em quórum de attestations
✅ Slashing como punição econômica
✅ Mempool com prioridade por tip
✅ Queima de base fee (deflação, estilo EIP-1559)
✅ Propagação gossip com deduplicação e TTL
✅ Smart contracts com estado persistente
✅ Epochs e rotação de validadores
```

### O que foi simplificado (e por quê)

```
⚡ Criptografia: HMAC em vez de ECDSA real
   → Conceito é o mesmo, implementação real é muito complexa

⚡ Tempo: slots manuais em vez de 12s automáticos
   → Permite estudar passo a passo sem esperar

⚡ Committees: todos validam em vez de subconjunto
   → Com 3 nós não faz sentido dividir em committees

⚡ Casper FFG: finalidade em 1 bloco em vez de 2 epochs
   → Simplifica sem perder o conceito

⚡ EVM: funções Python em vez de bytecode
   → Foco no conceito de contrato, não na VM

⚡ P2P: HTTP em vez de libp2p
   → Mais fácil de entender e debugar
```

---

## 🔄 Diagrama Final: Fluxo Completo

```
╔══════════════════════════════════════════════════════════════════╗
║                    FLUXO COMPLETO PoS                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  👤 USUÁRIO                                                      ║
║  │                                                               ║
║  ├─→ 1. Cria CARTEIRA (chave privada → pública → endereço)      ║
║  ├─→ 2. Cria CONTA (registra endereço + saldo na blockchain)    ║
║  ├─→ 3. Faz STAKE (trava moedas → vira validador)               ║
║  │                                                               ║
║  │   ┌─────────────────────────────────────────────┐             ║
║  │   │ EPOCH começa                                │             ║
║  │   │ Todos os nós calculam ESCALA DE SLOTS       │             ║
║  │   │ (mesma seed → mesmo resultado)              │             ║
║  │   │   Slot 0 → Alice                           │             ║
║  │   │   Slot 1 → Bob                             │             ║
║  │   │   Slot 2 → Alice                           │             ║
║  │   └─────────────────────────────────────────────┘             ║
║  │                                                               ║
║  ├─→ 4. Envia TRANSAÇÃO                                         ║
║  │      ├── Valida (saldo, assinatura)                           ║
║  │      ├── Adiciona na MEMPOOL (ordenada por tip)               ║
║  │      └── GOSSIP propaga tx pra todos os nós                   ║
║  │                                                               ║
║  │   ┌─────────────────────────────────────────────┐             ║
║  │   │ SLOT chega → PROPOSER designado age:        │             ║
║  │   │                                             │             ║
║  │   │  5. Pega txs da MEMPOOL                     │             ║
║  │   │  6. EXECUTA cada tx (debita/credita/queima) │             ║
║  │   │  7. Calcula STATE ROOT (hash do estado)     │             ║
║  │   │  8. Monta BLOCO (txs + hashes + metadata)   │             ║
║  │   │  9. GOSSIP propaga bloco pra rede           │             ║
║  │   └─────────────────────────────────────────────┘             ║
║  │                          │                                    ║
║  │                          ▼                                    ║
║  │   ┌─────────────────────────────────────────────┐             ║
║  │   │ Cada NÓ RECEPTOR (validador):               │             ║
║  │   │                                             │             ║
║  │   │  10. Confere HASH ANTERIOR                  │             ║
║  │   │  11. Confere PROPOSER correto (escala)      │             ║
║  │   │  12. RE-EXECUTA todas as txs                │             ║
║  │   │  13. Calcula STATE ROOT próprio             │             ║
║  │   │  14. Compara com o declarado pelo proposer  │             ║
║  │   │      ├── BATE → ACEITA + ATESTA ✅           │             ║
║  │   │      └── NÃO BATE → REJEITA ❌              │             ║
║  │   └─────────────────────────────────────────────┘             ║
║  │                          │                                    ║
║  │                          ▼                                    ║
║  │   ┌─────────────────────────────────────────────┐             ║
║  │   │ FINALIDADE:                                 │             ║
║  │   │  15. ≥ 66% dos validadores atestaram?       │             ║
║  │   │      ├── SIM → bloco FINALIZADO 🔒          │             ║
║  │   │      └── NÃO → bloco fica "pending"         │             ║
║  │   └─────────────────────────────────────────────┘             ║
║  │                          │                                    ║
║  │                          ▼                                    ║
║  │   ┌─────────────────────────────────────────────┐             ║
║  │   │ FIM DA EPOCH:                               │             ║
║  │   │  16. Nova seed = hash(último bloco)         │             ║
║  │   │  17. Nova escala de slots calculada          │             ║
║  │   │  18. Volta pro passo 4                      │             ║
║  │   └─────────────────────────────────────────────┘             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 📡 Endpoints da API (referência rápida)

### Fluxo básico via curl

```bash
# 1. Criar carteiras
alice=$(curl -s -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_createWallet","params":[{"name":"Alice","balance":500}],"id":1}')

bob=$(curl -s -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_createWallet","params":[{"name":"Bob","balance":300}],"id":2}')

# 2. Fazer stake
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_stake","params":[{"address":"<ALICE_ADDR>","amount":200}],"id":3}'

curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_stake","params":[{"address":"<BOB_ADDR>","amount":100}],"id":4}'

# 3. Ver escala de slots
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_getSlotSchedule","params":[],"id":5}'

# 4. Enviar transação
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_sendTransaction","params":[{"from":"<ALICE_ADDR>","to":"<BOB_ADDR>","value":50,"tip":1}],"id":6}'

# 5. Produzir bloco (proposer monta + peers validam via gossip)
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_produceBlock","params":[],"id":7}'

# 6. Ver logs (mostra validação real nos peers)
curl -X POST http://localhost:8546 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_getLog","params":[20],"id":8}'
```

---

<p align="center">
  <b>Feito para aprendizado. Inspirado no Ethereum 2.0. 🚀</b>
</p>
