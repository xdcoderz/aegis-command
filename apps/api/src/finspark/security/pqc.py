from __future__ import annotations

import base64
import importlib
import os
from dataclasses import dataclass
from types import ModuleType
from uuid import UUID, uuid4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from finspark.application.ports import AuditSigner


class PqcUnavailableError(RuntimeError):
    pass


class NullAuditSigner(AuditSigner):
    @property
    def algorithm(self) -> None:
        return None

    @property
    def available(self) -> bool:
        return False

    def sign(self, payload: bytes) -> None:
        del payload
        return None

    def verify(self, payload: bytes, signature: bytes) -> bool:
        del payload, signature
        return False


@dataclass(frozen=True, slots=True)
class VaultEnvelope:
    envelope_id: UUID
    algorithm: str
    encapsulated_key: bytes
    nonce: bytes
    ciphertext: bytes


class OqsRuntime(AuditSigner):
    """Process-local OQS key custody for the demo; production must use an HSM boundary."""

    def __init__(self, kem_algorithm: str, signature_algorithm: str) -> None:
        try:
            self._oqs: ModuleType = importlib.import_module("oqs")
        except ImportError as error:
            raise PqcUnavailableError("liboqs-python is not installed") from error
        self.kem_algorithm = kem_algorithm
        self.signature_algorithm = signature_algorithm
        with self._oqs.KeyEncapsulation(kem_algorithm) as kem:
            self._kem_public_key = kem.generate_keypair()
            self._kem_secret_key = kem.export_secret_key()
        with self._oqs.Signature(signature_algorithm) as signer:
            self._signature_public_key = signer.generate_keypair()
            self._signature_secret_key = signer.export_secret_key()

    @property
    def algorithm(self) -> str:
        return self.signature_algorithm

    @property
    def available(self) -> bool:
        return True

    def sign(self, payload: bytes) -> bytes:
        with self._oqs.Signature(self.signature_algorithm, self._signature_secret_key) as signer:
            return bytes(signer.sign(payload))

    def verify(self, payload: bytes, signature: bytes) -> bool:
        with self._oqs.Signature(self.signature_algorithm) as verifier:
            return bool(verifier.verify(payload, signature, self._signature_public_key))

    def encapsulate(self) -> tuple[bytes, bytes]:
        with self._oqs.KeyEncapsulation(self.kem_algorithm) as kem:
            encapsulated_key, shared_secret = kem.encap_secret(self._kem_public_key)
        return bytes(encapsulated_key), bytes(shared_secret)

    def decapsulate(self, encapsulated_key: bytes) -> bytes:
        with self._oqs.KeyEncapsulation(self.kem_algorithm, self._kem_secret_key) as kem:
            return bytes(kem.decap_secret(encapsulated_key))


class PqcVault:
    def __init__(self, runtime: OqsRuntime) -> None:
        self._runtime = runtime
        self._envelopes: dict[UUID, VaultEnvelope] = {}

    @staticmethod
    def _derive_key(shared_secret: bytes, envelope_id: UUID) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=envelope_id.bytes,
            info=b"finspark-pqc-vault-v1",
        ).derive(shared_secret)

    def store(self, plaintext: str) -> dict[str, str]:
        envelope_id = uuid4()
        encapsulated_key, shared_secret = self._runtime.encapsulate()
        key = self._derive_key(shared_secret, envelope_id)
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), envelope_id.bytes)
        envelope = VaultEnvelope(
            envelope_id=envelope_id,
            algorithm=f"{self._runtime.kem_algorithm}+HKDF-SHA256+AES-256-GCM",
            encapsulated_key=encapsulated_key,
            nonce=nonce,
            ciphertext=ciphertext,
        )
        self._envelopes[envelope_id] = envelope
        return {
            "envelope_id": str(envelope_id),
            "algorithm": envelope.algorithm,
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

    def retrieve(self, envelope_id: UUID) -> str | None:
        envelope = self._envelopes.get(envelope_id)
        if envelope is None:
            return None
        shared_secret = self._runtime.decapsulate(envelope.encapsulated_key)
        key = self._derive_key(shared_secret, envelope_id)
        plaintext = AESGCM(key).decrypt(
            envelope.nonce, envelope.ciphertext, envelope.envelope_id.bytes
        )
        return plaintext.decode("utf-8")

