import secrets
import string

CONSONANTS = "bdfgklmnprstvz"
VOWELS = "aeiou"


def generate_pronounceable_password(syllables=4):
    """Generate a pronounceable password like 'bafimoku'.

    Args:
        syllables: Number of consonant-vowel pairs (default 4 = 8 chars)

    Returns:
        Lowercase pronounceable password
    """
    password = ""
    for _ in range(syllables):
        password += secrets.choice(CONSONANTS)
        password += secrets.choice(VOWELS)
    return password


def generate_signup_token(length=32):
    """Generate a random alphanumeric token for URL-based auth.

    Args:
        length: Token length (default 32)

    Returns:
        Alphanumeric token string
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
