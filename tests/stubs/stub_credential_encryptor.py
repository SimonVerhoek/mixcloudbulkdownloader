"""Stub CredentialEncryptor for testing."""


class StubCredentialEncryptor:
    """Minimal stub that encrypts/decrypts deterministically without platform dependencies."""

    def encrypt(self, plaintext: str) -> str:
        """Stub encryption — returns a tagged version of the plaintext."""
        return f"enc:{plaintext}"

    def decrypt(self, encrypted_data: str) -> str:
        """Stub decryption — removes the enc: tag."""
        return encrypted_data.removeprefix("enc:")

    def test_encryption_cycle(self) -> bool:
        """Stub cycle test — always succeeds."""
        return True
