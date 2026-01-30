# utils/normalize.py

import re


def normalize_slot(slot):
    """
    Normalizes all slot formats to ONE canonical form.

    Examples handled:
    - "10.50-11.35"
    - "10.50_-_11.35"
    - "10.50 _ - _ 11.35"
    - "10:50-11:35"
    """

    if slot is None:
        return None

    s = str(slot).strip()

    # Replace ':' with '.'
    s = s.replace(":", ".")

    # Remove all spaces
    s = re.sub(r"\s+", "", s)

    # Replace any variant of '-' with '_-_'
    s = re.sub(r"[-–—]+", "_-_", s)

    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)

    # Final safety
    s = s.strip("_")

    return s


def normalize_subject(subject):
    """
    Normalizes subject names.
    Keeps slashes for parallel detection.
    """

    if subject is None:
        return None

    s = str(subject).strip()
    s = re.sub(r"\s+", " ", s)
    return s.upper()
