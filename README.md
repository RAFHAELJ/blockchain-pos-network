<p align="center">
  <h1 align="center">⛓️ Blockchain PoS Network</h1>
  <p align="center">
    Implementação completa de uma blockchain Proof-of-Stake em Python com API JSON-RPC 2.0, smart contracts, protocolo gossip e suporte a múltiplos nós em rede.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/protocolo-JSON--RPC%202.0-orange" alt="JSON-RPC">
  <img src="https://img.shields.io/badge/consenso-Proof%20of%20Stake-green" alt="PoS">
  <img src="https://img.shields.io/badge/licença-MIT-lightgrey" alt="Licença">
</p>

---

## 📋 Visão Geral

Blockchain educacional construída do zero implementando conceitos encontrados em redes de produção como Ethereum 2.0:

| Funcionalidade | Descrição |
|----------------|-----------|
| **Proof of Stake** | Seleção ponderada de validadores, staking/unstaking, slashing |
| **JSON-RPC 2.0** | API compatível com Ethereum (`eth_*`, `net_*`, `web3_*`) + métodos customizados `pos_*` |
| **Protocolo Gossip** | Propagação de mensagens peer-to-peer com TTL e deduplicação |
| **Smart Contracts** | Token ERC-20, NFT (ERC-721), Crowdfunding, DEX (AMM), Votação |
| **Epochs e Finalidade** | Produção de blocos por epoch com finalidade baseada em attestations |
| **Mempool** | Fila de prioridade ordenada por tip (taxa de prioridade) |
| **Queima de Taxas** | Taxa base queimada em cada transação (estilo EIP-1559) |
| **Carteiras** | Geração de par de chaves, derivação de endereço, assinatura de transações |
| **Persistência** | Salvar/carregar estado da blockchain em disco (JSON) |
| **Multi-Nó** | Rode 3+ nós independentes que sincronizam via gossip |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                   JSON-RPC 2.0 API                  │
│              (Flask - POST / endpoint)              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ Carteira  │  │  Mempool  │  │  Smart Contracts  │ │
│  │  (ECDSA)  │  │ (por tip) │  │ Token/NFT/DEX/.. │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              Blockchain Core                  │   │
│  │  Blocos · Validadores · Staking · Slashing    │   │
│  │  Epochs · Finalidade · Queima de Taxas        │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │           Protocolo Gossip (P2P)              │   │
│  │  Propagação de TX · Sync de blocos · Estado   │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘

  Node-SP (:8545) ←──gossip──→ Node-RJ (:8546)
       ↕                            ↕
  Node-MG (:8547) ←──gossip──→ Node-RJ (:8546)
```

---

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.10+
- pip

### Instalação

```bash
git clone https://github.com/<seu-usuario>/blockchain-pos-network.git
cd blockchain-pos-network
pip install -r requirements.txt
```

### Rodar um Nó

```bash
python rpc_server.py --port 8545 --node node-SP
```

### Rodar Rede com 3 Nós

**Windows:**
```bash
start_rpc_network.bat
```

**Linux/macOS:**
```bash
chmod +x start_rpc_network.sh
./start_rpc_network.sh
```

Isso sobe 3 nós interconectados:

| Nó | Porta | URL |
|----|-------|-----|
| node-SP | 8545 | http://localhost:8545 |
| node-RJ | 8546 | http://localhost:8546 |
| node-MG | 8547 | http://localhost:8547 |

### Rodar Testes

```bash
# Suite completa de testes RPC (precisa de pelo menos 1 nó rodando)
python test_rpc.py

# Verificar sincronização entre nós (precisa dos 3 nós rodando)
python check_nodes.py
```

### Simulação Offline (sem servidor)

```bash
python main.py
```

---

## 📡 API JSON-RPC

Todas as chamadas seguem a spec [JSON-RPC 2.0](https://www.jsonrpc.org/specification) via `POST /`:

```bash
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Métodos Padrão Ethereum

| Método | Descrição |
|--------|-----------|
| `eth_blockNumber` | Número do último bloco (hex) |
| `eth_getBlockByNumber` | Bloco por número |
| `eth_getBlockByHash` | Bloco por hash |
| `eth_getTransactionByHash` | Transação por ID |
| `eth_getBalance` | Saldo da conta (hex wei) |
| `eth_sendTransaction` | Enviar transação |
| `eth_getTransactionCount` | Nonce / contagem de txns |
| `eth_gasPrice` | Taxa base (hex wei) |
| `eth_chainId` | ID da chain (`0x539` = 1337) |
| `eth_accounts` | Listar contas |
| `eth_mining` | Status de validação |
| `eth_syncing` | Status de sincronização |
| `net_version` | Versão da rede |
| `net_peerCount` | Peers conectados |
| `net_listening` | Status de escuta |
| `web3_clientVersion` | Versão do cliente |

### Métodos Customizados (PoS)

| Método | Parâmetros | Descrição |
|--------|------------|-----------|
| `pos_createWallet` | `{name, balance}` | Criar carteira com par de chaves |
| `pos_createAccount` | `{address, balance}` | Criar conta |
| `pos_stake` | `{address, amount}` | Fazer stake (mín: 32) |
| `pos_unstake` | `{address, amount}` | Desfazer stake |
| `pos_getValidators` | — | Listar validadores |
| `pos_produceBlock` | — | Produzir próximo bloco |
| `pos_slash` | `{address, reason}` | Penalizar validador |
| `pos_deployContract` | `{creator, id, type, state?}` | Deploy de smart contract |
| `pos_callContract` | `{caller, id, params}` | Chamar smart contract |
| `pos_getContracts` | — | Listar contratos deployados |
| `pos_getMempool` | — | Transações pendentes |
| `pos_getStats` | — | Estatísticas do nó |
| `pos_getStaked` | `address` | Valor em stake |
| `pos_addPeer` | `url` | Registrar nó peer |
| `pos_getPeers` | — | Listar peers |
| `pos_getLog` | `n?` | Log de eventos (últimos n) |
| `pos_save` | — | Persistir em disco |
| `pos_validate` | — | Validar integridade da cadeia |

### Requisições em Batch

```json
[
  {"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1},
  {"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":2},
  {"jsonrpc":"2.0","method":"net_version","params":[],"id":3}
]
```

---

## 📜 Smart Contracts

Deploy via `pos_deployContract` com um dos tipos disponíveis:

| Tipo | Contrato | Ações |
|------|----------|-------|
| `token` | Token ERC-20 | `mint`, `transfer`, `balance_of`, `info` |
| `nft` | NFT ERC-721 | `mint`, `transfer`, `owner_of`, `list` |
| `crowdfunding` | Vaquinha | `contribute`, `status`, `refund` |
| `dex` | DEX (AMM) | `swap_a_to_b`, `swap_b_to_a`, `pool_info` |
| `voting` | Votação | `create_proposal`, `vote`, `results` |

**Exemplo — Deploy e uso de um token:**

```bash
# Deploy
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_deployContract","params":[{"creator":"0x...","id":"MeuToken","type":"token","state":{"name":"MeuToken","symbol":"MTK"}}],"id":1}'

# Mint
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_callContract","params":[{"caller":"0x...","id":"MeuToken","params":{"action":"mint","amount":10000,"to":"0x..."}}],"id":2}'
```

---

## 🔄 Protocolo Gossip

Os nós propagam mudanças de estado pela rede automaticamente:

```
Usuário envia TX pro Node-SP
  → Node-SP adiciona na mempool
  → Node-SP fofoca pro Node-RJ e Node-MG
  → Node-RJ recebe, processa, re-fofoca
  → Node-MG recebe dos dois, deduplica (set de mensagens já vistas)
```

**Eventos propagados:** transações, blocos, contas, stakes, deploys de contratos, slashing.

Cada mensagem gossip tem:
- **ID único** — evita loops infinitos
- **TTL** — limita número de saltos (padrão: 5)
- **Origin** — identificador do nó de origem

---

## 📁 Estrutura do Projeto

```
blockchain-pos-network/
├── core.py                 # Engine da blockchain (Block, Transaction, Mempool, Validator, Staking, Slashing)
├── wallet.py               # Carteira com geração de chaves e assinatura de transações
├── contracts.py            # Implementações de smart contracts (Token, NFT, DEX, Crowdfunding, Votação)
├── rpc_server.py           # Servidor JSON-RPC 2.0 (Flask) com protocolo gossip
├── network.py              # Simulação de rede P2P (modo offline)
├── main.py                 # Demo completa offline
├── test_rpc.py             # Suite de testes RPC
├── check_nodes.py          # Verificação de sincronização entre nós
├── start_rpc_network.bat   # Iniciar 3 nós (Windows)
├── start_rpc_network.sh    # Iniciar 3 nós (Linux/macOS)
├── requirements.txt        # Dependências Python
├── data/                   # Persistência da blockchain (gerado em runtime)
├── LICENSE
└── README.md
```

---

## ⚙️ Configuração

Constantes em `core.py` — classe `Blockchain`:

| Constante | Padrão | Descrição |
|-----------|--------|-----------|
| `BASE_REWARD` | 5 | Recompensa por bloco para o validador |
| `MIN_STAKE` | 32 | Stake mínimo para virar validador |
| `SLASH_PENALTY` | 0.5 | Fração do stake perdida no slash (50%) |
| `BASE_FEE` | 0.01 | Taxa queimada por transação |
| `BLOCKS_PER_EPOCH` | 3 | Blocos por epoch |
| `FINALITY_THRESHOLD` | 0.66 | Proporção de attestations para finalidade (66%) |
| `MAX_TXN_PER_BLOCK` | 10 | Máximo de transações por bloco |

---

## 🧪 Exemplo de Uso

```python
import requests

URL = "http://localhost:8545"

def rpc(method, params=None):
    r = requests.post(URL, json={"jsonrpc":"2.0","method":method,"params":params or [],"id":1})
    return r.json()["result"]

# Criar carteiras
alice = rpc("pos_createWallet", [{"name": "Alice", "balance": 500}])
bob   = rpc("pos_createWallet", [{"name": "Bob",   "balance": 300}])

# Fazer stake
rpc("pos_stake", [{"address": alice["address"], "amount": 200}])
rpc("pos_stake", [{"address": bob["address"],   "amount": 100}])

# Enviar transação
rpc("eth_sendTransaction", [{"from": alice["address"], "to": bob["address"], "value": 50, "tip": 0.5}])

# Produzir bloco
bloco = rpc("pos_produceBlock")
print(f"Bloco #{int(bloco['blockNumber'], 16)} por {bloco['validator'][:16]}...")

# Deploy de token
rpc("pos_deployContract", [{"creator": alice["address"], "id": "MeuToken", "type": "token"}])
rpc("pos_callContract", [{"caller": alice["address"], "id": "MeuToken", "params": {"action": "mint", "amount": 10000}}])
```

---

## 📄 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).

---

<p align="center">
  Feito para aprendizado. Inspirado no Ethereum 2.0. 🚀
</p>
