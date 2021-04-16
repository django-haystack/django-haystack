import hashlib


def get_identifier_method(key):
    """
    Custom get_identifier method used for testing the
    setting HAYSTACK_IDENTIFIER_MODULE
    """

    if hasattr(key, "get_custom_haystack_id"):
        return key.get_custom_haystack_id()
    else:
        key_bytes = key.encode("utf-8")
        return hashlib.md5(key_bytes).hexdigest()
