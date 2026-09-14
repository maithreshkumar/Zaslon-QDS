from alice_service.sign import sign_document as alice_sign
from alice_service.verify import verify_received_document as alice_verify
from bob_service.sign import sign_document as bob_sign
from bob_service.verify import verify_received_document as bob_verify


def test_alice_signs_and_bob_verifies():
    created = alice_sign(document=b"alice payload", filename="a.txt", signer_id="Alice",
                         verifier_id="Bob", seed=1, encryption_passphrase=None, noise={})
    assert bob_verify(document=b"alice payload", signature=created["signature"])["status"] == "VALID"


def test_bob_signs_and_alice_verifies():
    created = bob_sign(document=b"bob payload", filename="b.txt", signer_id="Bob",
                       verifier_id="Alice", seed=2, encryption_passphrase=None, noise={})
    assert alice_verify(document=b"bob payload", signature=created["signature"])["status"] == "VALID"

