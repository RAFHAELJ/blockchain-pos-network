<p align="center">
  <h1 align="center">⛓️ Blockchain PoS Network</h1>
  <p align="center">
    A full-featured Proof-of-Stake blockchain implementation in Python with JSON-RPC 2.0 API, smart contracts, gossip protocol, and multi-node network support.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/protocol-JSON--RPC%202.0-orange" alt="JSON-RPC">
  <img src="https://img.shields.io/badge/consensus-Proof%20of%20Stake-green" alt="PoS">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

---

## 📋 Overview

Educational blockchain built from scratch implementing core concepts found in production networks like Ethereum 2.0:

| Feature | Description |
|---------|-------------|
| **Proof of Stake** | Weighted validator selection, staking/unstaking, slashing |
| **JSON-RPC 2.0** | Ethereum-compatible API (`eth_*`, `net_*`, `web3_*`) + custom `pos_*` methods |
| **Gossip Protocol** | Peer-to-peer message propagation with TTL and deduplication |
| **Smart Contracts** | ERC-20 Token, NFT (ERC-721), Crowdfunding, DEX (AMM), Voting |
| **Epochs & Finality** | Epoch-based block production with attestation-based finality |
| **Mempool** | Priority queue ordered by tip (gas priority fee) |
| **Fee Burning** | Base fee burned on every transaction (EIP-1559 style) |
| **Wallets** | Key pair generation, address derivation, transaction signing |
| **Persistence** | Save/load blockchain state to disk (JSON) |
| **Multi-Node** | Run 3+ independent nodes that sync via gossip |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   JSON-RPC 2.0 API                  │
│              (Flask - POST / endpoint)              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │  Wallet   │  │  Mempool  │  │  Smart Contracts  │ │
│  │ (ECDSA)   │  │ (by tip)  │  │ Token/NFT/DEX/.. │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              Blockchain Core                  │   │
│  │  Blocks · Validators · Staking · Slashing     │   │
│  │  Epochs · Finality · Fee Burning              │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │           Gossip Protocol (P2P)               │   │
│  │  TX propagation · Block sync · State sync     │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘

  Node-SP (:8545) ←──gossip──→ Node-RJ (:8546)
       ↕                            ↕
  Node-MG (:8547) ←──gossip──→ Node-RJ (:8546)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/<your-username>/blockchain-pos-network.git
cd blockchain-pos-network
pip install -r requirements.txt
```

### Run Single Node

```bash
python rpc_server.py --port 8545 --node node-SP
```

### Run 3-Node Network

**Windows:**
```bash
start_rpc_network.bat
```

**Linux/macOS:**
```bash
chmod +x start_rpc_network.sh
./start_rpc_network.sh
```

This starts 3 interconnected nodes:

| Node | Port | URL |
|------|------|-----|
| node-SP | 8545 | http://localhost:8545 |
| node-RJ | 8546 | http://localhost:8546 |
| node-MG | 8547 | http://localhost:8547 |

### Run Tests

```bash
# Full RPC test suite (requires at least 1 node running)
python test_rpc.py

# Check node synchronization (requires 3 nodes running)
python check_nodes.py
```

### Run Offline Simulation (no server needed)

```bash
python main.py
```

---

## 📡 JSON-RPC API

All calls follow the [JSON-RPC 2.0](https://www.jsonrpc.org/specification) spec via `POST /`:

```bash
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Ethereum Standard Methods

| Method | Description |
|--------|-------------|
| `eth_blockNumber` | Latest block number (hex) |
| `eth_getBlockByNumber` | Block by number |
| `eth_getBlockByHash` | Block by hash |
| `eth_getTransactionByHash` | Transaction by ID |
| `eth_getBalance` | Account balance (hex wei) |
| `eth_sendTransaction` | Send transaction |
| `eth_getTransactionCount` | Nonce / tx count |
| `eth_gasPrice` | Base fee (hex wei) |
| `eth_chainId` | Chain ID (`0x539` = 1337) |
| `eth_accounts` | List accounts |
| `eth_mining` | Validator status |
| `eth_syncing` | Sync status |
| `net_version` | Network version |
| `net_peerCount` | Connected peers |
| `net_listening` | Listening status |
| `web3_clientVersion` | Client version string |

### Custom PoS Methods

| Method | Params | Description |
|--------|--------|-------------|
| `pos_createWallet` | `{name, balance}` | Create wallet with keypair |
| `pos_createAccount` | `{address, balance}` | Create account |
| `pos_stake` | `{address, amount}` | Stake coins (min: 32) |
| `pos_unstake` | `{address, amount}` | Unstake coins |
| `pos_getValidators` | — | List all validators |
| `pos_produceBlock` | — | Produce next block |
| `pos_slash` | `{address, reason}` | Slash a validator |
| `pos_deployContract` | `{creator, id, type, state?}` | Deploy smart contract |
| `pos_callContract` | `{caller, id, params}` | Call smart contract |
| `pos_getContracts` | — | List deployed contracts |
| `pos_getMempool` | — | Pending transactions |
| `pos_getStats` | — | Node statistics |
| `pos_getStaked` | `address` | Staked amount |
| `pos_addPeer` | `url` | Register peer node |
| `pos_getPeers` | — | List peers |
| `pos_getLog` | `n?` | Event log (last n) |
| `pos_save` | — | Persist to disk |
| `pos_validate` | — | Validate chain integrity |

### Batch Requests

```json
[
  {"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1},
  {"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":2},
  {"jsonrpc":"2.0","method":"net_version","params":[],"id":3}
]
```

---

## 📜 Smart Contracts

Deploy via `pos_deployContract` with one of the available types:

| Type | Contract | Description |
|------|----------|-------------|
| `token` | ERC-20 Token | `mint`, `transfer`, `balance_of`, `info` |
| `nft` | ERC-721 NFT | `mint`, `transfer`, `owner_of`, `list` |
| `crowdfunding` | Crowdfunding | `contribute`, `status`, `refund` |
| `dex` | DEX (AMM) | `swap_a_to_b`, `swap_b_to_a`, `pool_info` |
| `voting` | Voting | `create_proposal`, `vote`, `results` |

**Example — Deploy and use a token:**

```bash
# Deploy
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_deployContract","params":[{"creator":"0x...","id":"MyToken","type":"token","state":{"name":"MyToken","symbol":"MTK"}}],"id":1}'

# Mint
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"pos_callContract","params":[{"caller":"0x...","id":"MyToken","params":{"action":"mint","amount":10000,"to":"0x..."}}],"id":2}'
```

---

## 🔄 Gossip Protocol

Nodes propagate state changes across the network automatically:

```
User sends TX to Node-SP
  → Node-SP adds to mempool
  → Node-SP gossips to Node-RJ and Node-MG
  → Node-RJ receives, processes, re-gossips
  → Node-MG receives from both, deduplicates (seen_gossip set)
```

**Propagated events:** transactions, blocks, accounts, stakes, contract deploys, slashing.

Each gossip message has:
- **Unique ID** — prevents infinite loops
- **TTL** — limits hop count (default: 5)
- **Origin** — source node identifier

---

## 📁 Project Structure

```
blockchain-pos-network/
├── core.py                 # Blockchain engine (Block, Transaction, Mempool, Validator, Staking, Slashing)
├── wallet.py               # Wallet with key generation and transaction signing
├── contracts.py            # Smart contract implementations (Token, NFT, DEX, Crowdfunding, Voting)
├── rpc_server.py           # JSON-RPC 2.0 server (Flask) with gossip protocol
├── network.py              # P2P network simulation (for offline mode)
├── main.py                 # Full offline simulation demo
├── test_rpc.py             # RPC test suite
├── check_nodes.py          # Multi-node sync verification
├── start_rpc_network.bat   # Start 3 nodes (Windows)
├── start_rpc_network.sh    # Start 3 nodes (Linux/macOS)
├── requirements.txt        # Python dependencies
├── data/                   # Blockchain persistence (auto-generated)
├── LICENSE
└── README.md
```

---

## ⚙️ Configuration

Constants in `core.py` — `Blockchain` class:

| Constant | Default | Description |
|----------|---------|-------------|
| `BASE_REWARD` | 5 | Block reward for validator |
| `MIN_STAKE` | 32 | Minimum stake to become validator |
| `SLASH_PENALTY` | 0.5 | Fraction of stake lost on slash (50%) |
| `BASE_FEE` | 0.01 | Fee burned per transaction |
| `BLOCKS_PER_EPOCH` | 3 | Blocks per epoch |
| `FINALITY_THRESHOLD` | 0.66 | Attestation ratio for finality (66%) |
| `MAX_TXN_PER_BLOCK` | 10 | Max transactions per block |

---

## 🧪 Example Session

```python
import requests, json

URL = "http://localhost:8545"

def rpc(method, params=None):
    r = requests.post(URL, json={"jsonrpc":"2.0","method":method,"params":params or [],"id":1})
    return r.json()["result"]

# Create wallets
alice = rpc("pos_createWallet", [{"name": "Alice", "balance": 500}])
bob   = rpc("pos_createWallet", [{"name": "Bob",   "balance": 300}])

# Stake
rpc("pos_stake", [{"address": alice["address"], "amount": 200}])
rpc("pos_stake", [{"address": bob["address"],   "amount": 100}])

# Send transaction
rpc("eth_sendTransaction", [{"from": alice["address"], "to": bob["address"], "value": 50, "tip": 0.5}])

# Produce block
block = rpc("pos_produceBlock")
print(f"Block #{int(block['blockNumber'], 16)} by {block['validator'][:16]}...")

# Deploy token
rpc("pos_deployContract", [{"creator": alice["address"], "id": "MyToken", "type": "token"}])
rpc("pos_callContract", [{"caller": alice["address"], "id": "MyToken", "params": {"action": "mint", "amount": 10000}}])
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built for learning. Inspired by Ethereum 2.0. 🚀
</p>
