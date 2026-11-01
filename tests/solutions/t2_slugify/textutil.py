import re


def word_count(s):
    """공백으로 나눈 낱말 수."""
    return len(s.split())


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
