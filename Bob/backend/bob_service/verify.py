from zaslon_shared.participant import verify_received_document as _verify_received_document


def verify_received_document(*, document: bytes, signature: dict):
    return _verify_received_document(
        document=document, signature=signature, verifier_id="Bob"
    )

__all__ = ["verify_received_document"]
