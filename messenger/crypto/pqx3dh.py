from __future__ import annotations

from typing import Optional, Tuple
import base64

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

import oqs

from .ratchet import DoubleRatchet


# ======================
# Base64 helpers
# ======================
def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


# ======================
# Crypto helpers
# ======================
def hkdf32(ikm: bytes, salt: bytes, info: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info
    ).derive(ikm)


def dh(priv: x25519.X25519PrivateKey, pub: x25519.X25519PublicKey) -> bytes:
    return priv.exchange(pub)


def derive_root_key(x3dh_secret: bytes, kyber_ss: bytes) -> bytes:
    return hkdf32(
        x3dh_secret + kyber_ss,
        salt=b"PQX3DH-salt",
        info=b"PQX3DH-root",
    )


# ======================
# PQX3DH Initiator
# ======================
def pqx3dh_initiate(
    *,
    my_ik_priv: x25519.X25519PrivateKey,
    their_ik_pub: x25519.X25519PublicKey,
    their_spk_pub: x25519.X25519PublicKey,
    their_opk_pub: Optional[x25519.X25519PublicKey],
    their_kyber_pub: bytes,
) -> Tuple[bytes, x25519.X25519PrivateKey, bytes, Optional[bytes]]:

    ek = x25519.X25519PrivateKey.generate()

    dh1 = dh(my_ik_priv, their_spk_pub)
    dh2 = dh(ek, their_ik_pub)
    dh3 = dh(ek, their_spk_pub)

    x3dh_secret = dh1 + dh2 + dh3

    if their_opk_pub is not None:
        x3dh_secret += dh(ek, their_opk_pub)

    # Kyber encapsulation (always supported)
    with oqs.KeyEncapsulation("Kyber512") as kem:
        kyber_ct, ky_ss = kem.encap_secret(their_kyber_pub)

    rk = derive_root_key(x3dh_secret, ky_ss)

    opk_used = (
        their_opk_pub.public_bytes_raw()
        if their_opk_pub is not None
        else None
    )

    return rk, ek, kyber_ct, opk_used


# ======================
# PQX3DH Responder
# ======================
def pqx3dh_respond(
    *,
    my_ik_priv: x25519.X25519PrivateKey,
    my_spk_priv: x25519.X25519PrivateKey,
    my_opk_priv: Optional[x25519.X25519PrivateKey],
    my_kyber_priv: bytes,
    their_ik_pub: x25519.X25519PublicKey,
    ek_pub_bytes: bytes,
    kyber_ct: bytes,
) -> bytes:

    ek_pub = x25519.X25519PublicKey.from_public_bytes(ek_pub_bytes)

    dh1 = dh(my_spk_priv, their_ik_pub)
    dh2 = dh(my_ik_priv, ek_pub)
    dh3 = dh(my_spk_priv, ek_pub)

    x3dh_secret = dh1 + dh2 + dh3

    if my_opk_priv is not None:
        x3dh_secret += dh(my_opk_priv, ek_pub)

    # ----------------------
    # Kyber decapsulation
    # (API-compatible with all oqs versions)
    # ----------------------
    ky_ss: bytes

    with oqs.KeyEncapsulation("Kyber512") as kem:
        if hasattr(kem, "import_secret_key"):
            # Newer oqs-python
            kem.import_secret_key(my_kyber_priv)
            ky_ss = kem.decap_secret(kyber_ct)

        elif hasattr(kem, "set_secret_key"):
            # Some intermediate versions
            kem.set_secret_key(my_kyber_priv)
            ky_ss = kem.decap_secret(kyber_ct)

        else:
            # Older bindings: secret key via constructor
            try:
                kem2 = oqs.KeyEncapsulation(
                    "Kyber512",
                    secret_key=my_kyber_priv
                )
                ky_ss = kem2.decap_secret(kyber_ct)
                kem2.free()
            except Exception as e:
                raise RuntimeError(
                    "Kyber secret key import not supported by this oqs build. "
                    "Please upgrade liboqs / oqs-python."
                ) from e

    rk = derive_root_key(x3dh_secret, ky_ss)
    return rk


# ======================
# Double Ratchet builders
# ======================
def build_initiator_ratchet(
    root_key: bytes,
    ek_priv: x25519.X25519PrivateKey,
    their_spk_pub: x25519.X25519PublicKey,
) -> DoubleRatchet:
    return DoubleRatchet(
        root_key,
        my_priv=ek_priv,
        their_pub=their_spk_pub,
        is_initiator=True,
    )


def build_responder_ratchet(
    root_key: bytes,
    my_spk_priv: x25519.X25519PrivateKey,
    ek_pub_bytes: bytes,
) -> DoubleRatchet:
    ek_pub = x25519.X25519PublicKey.from_public_bytes(ek_pub_bytes)
    return DoubleRatchet(
        root_key,
        my_priv=my_spk_priv,
        their_pub=ek_pub,
        is_initiator=False,
    )

