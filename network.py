"""
Rede P2P simulada.
Multiplos nos rodando blockchains independentes,
sincronizando entre si (consenso por cadeia mais longa + valida).
"""

from core import Blockchain


class Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.blockchain = Blockchain(node_id=node_id)
        self.peers = []  # outros nodes

    def connect(self, other_node):
        if other_node not in self.peers:
            self.peers.append(other_node)
            other_node.peers.append(self)

    def broadcast_tx(self, sender, receiver, amount, tip=0, wallet=None):
        """Envia transacao pra todos os peers."""
        self.blockchain.send(sender, receiver, amount, tip, wallet)
        for peer in self.peers:
            peer.blockchain.send(sender, receiver, amount, tip, wallet)

    def sync(self):
        """Sincroniza: adota a cadeia mais longa e valida."""
        my_len = len(self.blockchain.chain)
        best_chain = None
        best_len = my_len

        for peer in self.peers:
            peer_len = len(peer.blockchain.chain)
            if peer_len > best_len:
                valid, _ = peer.blockchain.is_valid()
                if valid:
                    best_len = peer_len
                    best_chain = peer.blockchain.chain

        if best_chain:
            self.blockchain.chain = best_chain
            self.blockchain._log(f"SYNC: adotou cadeia do peer ({best_len} blocos)")
            return True, f"Sincronizado: {best_len} blocos"
        return False, "Ja esta atualizado"

    def __repr__(self):
        return f"Node({self.node_id}) blocos={len(self.blockchain.chain)} peers={len(self.peers)}"


class Network:
    """Rede de nodes."""
    def __init__(self):
        self.nodes = {}

    def add_node(self, node_id):
        node = Node(node_id)
        self.nodes[node_id] = node
        return node

    def connect_all(self):
        """Conecta todos os nodes entre si."""
        node_list = list(self.nodes.values())
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                node_list[i].connect(node_list[j])

    def sync_all(self):
        """Sincroniza todos os nodes."""
        for node in self.nodes.values():
            node.sync()

    def print_status(self):
        print("\n  REDE P2P:")
        print("  " + "-" * 50)
        for nid, node in self.nodes.items():
            bc = node.blockchain
            print(f"  {nid}: {len(bc.chain)} blocos | "
                  f"epoch {bc.current_epoch} | "
                  f"mempool {bc.mempool.size()} | "
                  f"peers {len(node.peers)}")
