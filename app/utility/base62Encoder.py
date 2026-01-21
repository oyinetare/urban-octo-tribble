import string


class Base62Encoder:
    """Encoder for converting integers to/from base62 strings."""

    ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
    BASE = len(ALPHABET)

    @classmethod
    def encode(cls, num: int) -> str:
        """Encode an integer to base62 string."""
        if num == 0:
            return cls.ALPHABET[0]

        result = []
        while num:
            result.append(cls.ALPHABET[num % cls.BASE])
            num //= cls.BASE

        return "".join(reversed(result))

    @classmethod
    def decode(cls, s: str) -> int:
        """Decode a base62 string to integer."""
        num = 0
        for char in s:
            num = num * cls.BASE + cls.ALPHABET.index(char)
        return num


# Initialize once
base62_encoder = Base62Encoder()
