import random
import string
import time
import jwt
import hashlib


def generate_temporary_password(length=12):
    """
    Generate a temporary password with mixed case letters, numbers and special characters
    Default length is 12 characters
    """
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"

    # Ensure at least one character from each set
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special),
    ]

    # Fill remaining length with random characters from all sets
    all_chars = lowercase + uppercase + digits + special
    for i in range(length - 4):
        password.append(random.choice(all_chars))

    # Shuffle the password characters
    random.shuffle(password)

    # Join into final string
    return "".join(password)


def generate_otp(length=6):
    """
    Generate a random OTP (One Time Password) of specified length
    Default length is 6 digits
    """
    # Generate OTP using only digits
    digits = string.digits
    otp = "".join(random.choice(digits) for i in range(length))
    return otp


def generate_apple_client_secret(client_id, team_id, key_id, private_key):
    """
    Generates a JWT signed with the Apple Private Key to be used as the client_secret.
    """
    now = int(time.time())

    # Header claims
    header = {"alg": "ES256", "kid": key_id}  # Apple requires ES256 algorithm

    # Payload claims
    payload = {
        "iss": team_id,
        "iat": now,
        "exp": now + 86400 * 180,  # Expires in 180 days (max is 6 months)
        "aud": "https://appleid.apple.com",
        "sub": client_id,
    }

    # Encode and sign the JWT
    return jwt.encode(header, payload, private_key)


def generate_team_code():
    """
    Generate a unique uppercase alphanumeric team code
    """
    # Generate 8 character random string of uppercase letters and numbers
    chars = string.ascii_uppercase + string.digits
    team_code = "".join(random.choice(chars) for _ in range(8))
    return team_code


def derive_key_from_string(secret_string: str, key_length: int) -> bytes:
    """
    Derives a cryptographically strong, fixed-length key from a text string
    using PBKDF2 with a unique salt.

    Args:
        secret_string: The human-readable string (e.g., your SECRET_KEY).
        key_length: The desired length of the output key in bytes (e.g., 16 for 128-bit).

    Returns:
        A bytes object of the specified length.
    """
    # 1. Use a unique salt: Essential for security. In a real app, this salt
    # should be stored securely alongside the key settings.
    # For JOSE encryption, you might use a fixed salt derived from your app name.
    # For this example, we'll use a constant one for deterministic results:
    salt = "brain-bridge-app-salt".encode("utf-8")

    # 2. Key Derivation using PBKDF2-HMAC-SHA256
    # The string must be encoded to bytes first.
    key_bytes = hashlib.pbkdf2_hmac(
        hash_name="sha256",  # Algorithm used
        password=secret_string.encode("utf-8"),  # The key string, encoded
        salt=salt,  # Unique salt bytes
        iterations=480000,  # High iteration count for security
        dklen=key_length,  # Desired key length (e.g., 16 bytes)
    )

    return key_bytes
