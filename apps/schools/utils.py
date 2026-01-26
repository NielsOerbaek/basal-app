import secrets
import string

CONSONANTS = "bdfgklmnprstvz"
VOWELS = "aeiou"


def generate_pronounceable_password(segments=4):
    """Generate a pronounceable password like 'babe.dula.kibe.popy'.

    Args:
        segments: Number of 4-char segments (default 4 = 19 chars with dots)

    Returns:
        Lowercase pronounceable password with period delimiters
    """
    parts = []
    for _ in range(segments):
        # Each segment is 2 syllables (4 chars): e.g., "babe"
        segment = ""
        for _ in range(2):
            segment += secrets.choice(CONSONANTS)
            segment += secrets.choice(VOWELS)
        parts.append(segment)
    return ".".join(parts)


def generate_signup_token(length=32):
    """Generate a random alphanumeric token for URL-based auth.

    Args:
        length: Token length (default 32)

    Returns:
        Alphanumeric token string
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
