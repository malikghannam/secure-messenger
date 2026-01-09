from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import base64

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from .crypto_utils import aead_encrypt_xchacha20poly1305, aead_decrypt_xchacha20poly1305


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

def b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def kdf_rk(rk: bytes, dh_out: bytes) -> Tuple[bytes, bytes]:
    out = hkdf(dh_out, salt=rk, info=b"DR-rk", length=64)
    return out[:32], out[32:]


def kdf_ck(ck: bytes) -> Tuple[bytes, bytes]:
    out = hkdf(b"\x01", salt=ck, info=b"DR-ck", length=64)
    return out[:32], out[32:]


@dataclass
class Header:
    dh_pub: str
    pn: int
    n: int


class DoubleRatchet:
    def __init__(
        self,
        root_key: bytes,
        *,
        my_priv: x25519.X25519PrivateKey,
        their_pub: Optional[x25519.X25519PublicKey],
        is_initiator: bool,
    ):
        self.RK = root_key
        self.DHs = my_priv
        self.DHr = their_pub
        self.is_initiator = is_initiator

        self.CKs: Optional[bytes] = None
        self.CKr: Optional[bytes] = None

        self.Ns = 0
        self.Nr = 0
        self.PN = 0

        self.skipped: Dict[str, Dict[int, bytes]] = {}

        if self.DHr is not None:
            self._initialize_chain()

    @staticmethod
    def gen_priv() -> x25519.X25519PrivateKey:
        return x25519.X25519PrivateKey.generate()

    @staticmethod
    def pub_bytes(pub: x25519.X25519PublicKey) -> bytes:
        return pub.public_bytes_raw()

    @staticmethod
    def priv_from_bytes(b: bytes) -> x25519.X25519PrivateKey:
        return x25519.X25519PrivateKey.from_private_bytes(b)

    @staticmethod
    def pub_from_bytes(b: bytes) -> x25519.X25519PublicKey:
        return x25519.X25519PublicKey.from_public_bytes(b)

    def _dh(self, priv: x25519.X25519PrivateKey, pub: x25519.X25519PublicKey) -> bytes:
        return priv.exchange(pub)

    def _initialize_chain(self) -> None:
        assert self.DHr is not None
        dh_out = self._dh(self.DHs, self.DHr)
        self.RK, ck = kdf_rk(self.RK, dh_out)
        if self.is_initiator:
            self.CKs = ck
            self.CKr = None
        else:
            self.CKr = ck
            self.CKs = None

    def _skip_message_keys(self, until: int) -> None:
        if self.CKr is None or self.DHr is None:
            return
        dh_id = b64e(self.pub_bytes(self.DHr))
        self.skipped.setdefault(dh_id, {})
        while self.Nr < until:
            self.CKr, mk = kdf_ck(self.CKr)
            self.skipped[dh_id][self.Nr] = mk
            self.Nr += 1

    def _try_skipped(self, header: Header, ciphertext: str) -> Optional[bytes]:
        dh_id = header.dh_pub
        if dh_id in self.skipped and header.n in self.skipped[dh_id]:
            mk = self.skipped[dh_id].pop(header.n)
            if not self.skipped[dh_id]:
                self.skipped.pop(dh_id, None)
            aad = (header.dh_pub + f"|{header.pn}|{header.n}").encode()
            return aead_decrypt_xchacha20poly1305(b64d(ciphertext), key=mk, aad=aad)
        return None

    def _dh_ratchet(self, header: Header) -> None:
        their_new = self.pub_from_bytes(b64d(header.dh_pub))

        self._skip_message_keys(header.pn)

        self.PN = self.Ns
        self.Ns = 0
        self.Nr = 0

        self.DHr = their_new
        dh_out = self._dh(self.DHs, self.DHr)
        self.RK, self.CKr = kdf_rk(self.RK, dh_out)

        self.DHs = self.gen_priv()
        dh_out2 = self._dh(self.DHs, self.DHr)
        self.RK, self.CKs = kdf_rk(self.RK, dh_out2)

    def encrypt(self, plaintext: bytes) -> Dict[str, Any]:
        if self.CKs is None:
            if self.DHr is None:
                raise RuntimeError("No DHr to start sending chain.")
            self.DHs = self.gen_priv()
            dh_out = self._dh(self.DHs, self.DHr)
            self.RK, self.CKs = kdf_rk(self.RK, dh_out)

        assert self.CKs is not None
        self.CKs, mk = kdf_ck(self.CKs)

        header = Header(
            dh_pub=b64e(self.pub_bytes(self.DHs.public_key())),
            pn=self.PN,
            n=self.Ns,
        )
        aad = (header.dh_pub + f"|{header.pn}|{header.n}").encode()
        ct = aead_encrypt_xchacha20poly1305(plaintext, key=mk, aad=aad)

        self.Ns += 1
        return {"header": {"dh_pub": header.dh_pub, "pn": header.pn, "n": header.n}, "ciphertext": b64e(ct)}

    def decrypt(self, msg: Dict[str, Any]) -> bytes:
        h = msg["header"]
        header = Header(dh_pub=h["dh_pub"], pn=int(h["pn"]), n=int(h["n"]))
        ciphertext = msg["ciphertext"]

        pt = self._try_skipped(header, ciphertext)
        if pt is not None:
            return pt

        if self.DHr is None or header.dh_pub != b64e(self.pub_bytes(self.DHr)):
            self._dh_ratchet(header)

        self._skip_message_keys(header.n)

        if self.CKr is None:
            raise RuntimeError("No receiving chain key.")
        self.CKr, mk = kdf_ck(self.CKr)

        aad = (header.dh_pub + f"|{header.pn}|{header.n}").encode()
        pt = aead_decrypt_xchacha20poly1305(b64d(ciphertext), key=mk, aad=aad)
        self.Nr += 1
        return pt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "RK": b64e(self.RK),
            "DHs": b64e(self.DHs.private_bytes_raw()),
            "DHr": b64e(self.pub_bytes(self.DHr)) if self.DHr is not None else None,
            "is_initiator": self.is_initiator,
            "CKs": b64e(self.CKs) if self.CKs is not None else None,
            "CKr": b64e(self.CKr) if self.CKr is not None else None,
            "Ns": self.Ns,
            "Nr": self.Nr,
            "PN": self.PN,
            "skipped": {k: {str(n): b64e(mk) for n, mk in v.items()} for k, v in self.skipped.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DoubleRatchet":
        obj = cls(
            root_key=b64d(d["RK"]),
            my_priv=cls.priv_from_bytes(b64d(d["DHs"])),
            their_pub=cls.pub_from_bytes(b64d(d["DHr"])) if d.get("DHr") else None,
            is_initiator=bool(d.get("is_initiator", True)),
        )
        obj.CKs = b64d(d["CKs"]) if d.get("CKs") else None
        obj.CKr = b64d(d["CKr"]) if d.get("CKr") else None
        obj.Ns = int(d.get("Ns", 0))
        obj.Nr = int(d.get("Nr", 0))
        obj.PN = int(d.get("PN", 0))
        obj.skipped = {
            k: {int(n): b64d(mk) for n, mk in v.items()}
            for k, v in (d.get("skipped") or {}).items()
        }
        return obj
