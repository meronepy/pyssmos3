"""AES-CCM cipher utilities for SSM authentication.

This module defines a function to generate a CMAC-based token and
a CipherManager class for AES-CCM encryption/decryption with a rolling counter.
"""

from Crypto.Cipher import AES
from Crypto.Hash import CMAC


def generate_token(secret_key: bytes, random_code: bytes) -> bytes:
    """Generates a CMAC-based token using AES.

    This function creates a CMAC object with the given secret key and updates it
    with the provided random code, returning the resulting digest as an authentication token.

    Args:
        secret_key (bytes): The AES key used for CMAC generation.
        random_code (bytes): The random code to update into the CMAC.

    Returns:
        bytes: The generated CMAC digest as a token.
    """
    cobj = CMAC.new(secret_key, ciphermod=AES)
    cobj.update(random_code)
    token = cobj.digest()
    return token


class CipherManager:
    """Manages AES-CCM encryption and decryption with a rolling counter.

    The CipherManager uses a fixed random code and CMAC-derived token for
    constructing nonces and performing authenticated encryption and decryption
    with AES-CCM mode. Each call to encrypt() or decrypt() increments its
    respective counter to ensure nonce uniqueness.
    """

    def __init__(self, random_code: bytes, token: bytes) -> None:
        """Initializes the CipherManager with a random code and CMAC token.

        Args:
            random_code (bytes): A random sequence used in nonce construction.
            token (bytes): A CMAC-derived token used as the AES key for CCM mode.
        """
        self._random_code: bytes = random_code
        self._token: bytes = token
        self._encrypt_counter: int = 0
        self._decrypt_counter: int = 0

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt plaintext data using AES-CCM with a rolling counter in the nonce.

        Constructs a nonce from the current encrypt counter and random code, then
        performs AES-CCM encryption with a 4-byte authentication tag.

        Args:
            data (bytes): Plaintext bytes to encrypt.

        Returns:
            bytes: Ciphertext concatenated with a 4-byte authentication tag.

        Raises:
            ValueError: If the provided key or nonce length is invalid.
        """
        nonce = (
            self._encrypt_counter.to_bytes(8, "little") + b"\x00" + self._random_code
        )
        cipher = AES.new(self._token, AES.MODE_CCM, nonce=nonce, mac_len=4)
        cipher.update(b"\x00")
        ciphertext, tag = cipher.encrypt_and_digest(data)
        self._encrypt_counter += 1
        return ciphertext + tag

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data encrypted by this manager, verifying authenticity.

        Constructs a nonce from the current decrypt counter and random code, then
        uses AES-CCM to decrypt and verify the authentication tag.

        Args:
            data (bytes): Ciphertext concatenated with a 4-byte authentication tag.

        Returns:
            bytes: The decrypted plaintext bytes.

        Raises:
            ValueError: If authentication tag verification fails or data is malformed.
        """
        nonce = (
            self._decrypt_counter.to_bytes(8, "little") + b"\x00" + self._random_code
        )
        cipher = AES.new(self._token, AES.MODE_CCM, nonce=nonce, mac_len=4)
        cipher.update(b"\x00")
        plaintext = cipher.decrypt_and_verify(data[:-4], data[-4:])
        self._decrypt_counter += 1
        return plaintext
