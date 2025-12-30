from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.setting import settings
import error
import json
from fastapi.security import HTTPBearer
from fastapi import Depends
from jose import jwe
from jose.constants import ALGORITHMS
import time
from uuid import UUID
from util.gen import derive_key_from_string
from service.redis import Redis

bearerschema = HTTPBearer()


def json_default_serializer(obj):
    """
    Custom JSON serializer for objects not serializable by default json code.
    Specifically handles UUID and datetime objects.
    """
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class TokenManager:
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], expires_in_minutes: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token
        """
        try:
            payload = data.copy()
            expiration_dt = datetime.now() + timedelta(minutes=expires_in_minutes)
            expiration_timestamp = int(expiration_dt.timestamp())
            payload.update({"exp": expiration_timestamp})
            # Convert dict payload to JSON string, then encode to bytes
            payload_bytes = json.dumps(payload, default=json_default_serializer).encode(
                "utf-8"
            )
            key_value = derive_key_from_string(settings.SECRET_KEY, 16)
            # Encrypt the payload bytes
            encrypted_jwe_bytes = jwe.encrypt(
                plaintext=payload_bytes,
                key=key_value,
                algorithm=ALGORITHMS.A128KW,
                encryption=ALGORITHMS.A128CBC_HS256,
            )

            return encrypted_jwe_bytes.decode("utf-8")

        except Exception as e:
            print(f"Encryption failed: {e}")
            raise error.ServerError("Login failed")

    @staticmethod
    def decode_token(token: str, check_expiry: bool = True) -> Dict[str, Any]:
        """
        Decrypts a JWE compact token string and returns the original Python dictionary.
        Optionally checks the 'exp' field against the current time.
        """
        try:
            # Decrypt the JWE token to get the original payload bytes
            key_value = derive_key_from_string(settings.SECRET_KEY, 16)
            decrypted_bytes = jwe.decrypt(token, key_value)

            # Decode bytes back to JSON string, and load into a Python dictionary
            decrypted_data = json.loads(decrypted_bytes.decode("utf-8"))

            # 🛑 Check for expiration if the flag is set
            if check_expiry and "exp" in decrypted_data:
                current_time = int(time.time())
                expiry_time = decrypted_data["exp"]

                if current_time > expiry_time:
                    raise error.InvalidRequestError(
                        f"Token expired at {datetime.fromtimestamp(expiry_time)}. Current time is {datetime.fromtimestamp(current_time)}."
                    )

            return decrypted_data

        except ValueError as ve:
            # Re-raise the expiration error specifically
            raise ve
        except Exception as e:
            print(f"Decryption failed or token tampered: {e}")
            raise error.ServerError("Invalid token")


def verify_access_token(token: str = Depends(bearerschema)) -> Dict[str, Any]:
    """
    Verify the access token and return the payload with caching
    """
    token_string = token.credentials

    # Create cache key from token (using hash for security)
    cache_key = f"token_payload:{hash(token_string)}"

    # Try to get from cache first
    redis_instance = Redis()
    cached_payload = redis_instance.get_json(cache_key)

    if cached_payload:
        return cached_payload

    # Decode token if not in cache
    payload = TokenManager.decode_token(token_string)

    # Cache the payload for 5 minutes (shorter than token expiry)
    redis_instance.set_json(cache_key, payload, expiry=300)

    return payload


def verify_access_token_ws(token: str) -> Dict[str, Any]:
    """
    Verify access token for WebSocket connections (without FastAPI dependency injection)
    """
    try:
        return TokenManager.decode_token(token)
    except Exception as e:
        raise error.AuthenticationError("Invalid WebSocket authentication token")
