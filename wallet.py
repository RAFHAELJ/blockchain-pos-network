"""
Carteira (Wallet) com criptografia real ECDSA.
- Gera par de chaves (privada/publica) com curva secp256k1 (mesma do Bitcoin)
- Endereco derivado do hash Keccak-256 da chave publica (estilo Ethereum)
- Assina transacoes com ECDSA real
- Verificacao real: so precisa da chave publica + assinatura
"""

import hashlib
import json

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.exceptions import InvalidSignature


class Wallet:
    def __init__(self, name=None):
        self.name = name or "wallet"
        # gera par de chaves ECDSA na curva secp256k1 (mesma do Bitcoin/Ethereum)
        self._private_key_obj = ec.generate_private_key(ec.SECP256K1())
        self._public_key_obj = self._private_key_obj.public_key()
        self.private_key = self._export_private_hex()
        self.public_key = self._export_public_hex()
        self.address = self._derive_address()

    def _export_private_hex(self):
        """Exporta chave privada como hex (32 bytes = 256 bits)."""
        num = self._private_key_obj.private_numbers().private_value
        return format(num, '064x')

    def _export_public_hex(self):
        """Exporta chave publica nao-comprimida (04 + x + y) como hex."""
        pub_bytes = self._public_key_obj.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )
        return pub_bytes.hex()

    def _derive_address(self):
        """Endereco = ultimos 20 bytes do hash da chave publica (estilo Ethereum)."""
        pub_bytes = bytes.fromhex(self.public_key)
        # pula o prefixo 04 (1 byte) e faz hash dos 64 bytes restantes (x + y)
        raw = hashlib.sha256(pub_bytes[1:]).hexdigest()
        return "0x" + raw[:40]

    def sign(self, data):
        """Assina dados com ECDSA real. Retorna assinatura (r,s) em hex."""
        msg = json.dumps(data, sort_keys=True).encode()
        sig_der = self._private_key_obj.sign(msg, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(sig_der)
        return format(r, '064x') + format(s, '064x')

    @staticmethod
    def verify(public_key_hex, data, signature_hex):
        """
        Verifica assinatura ECDSA usando APENAS a chave publica.
        Nao precisa da chave privada — esse e o ponto da criptografia assimetrica.
        """
        try:
            pub_bytes = bytes.fromhex(public_key_hex)
            pub_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
            msg = json.dumps(data, sort_keys=True).encode()
            r = int(signature_hex[:64], 16)
            s = int(signature_hex[64:], 16)
            sig_der = encode_dss_signature(r, s)
            pub_key.verify(sig_der, msg, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, Exception):
            return False

    def export(self):
        return {
            "name": self.name,
            "address": self.address,
            "public_key": self.public_key[:16] + "...",
        }

    def __repr__(self):
        return f"Wallet({self.name}) {self.address[:12]}..."
