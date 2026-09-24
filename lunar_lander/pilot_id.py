"""Pilot ID entry: name initials (A-Z) + last four phone digits."""

from __future__ import annotations

import string


MIN_INITIALS = 2
MAX_INITIALS = 4
PHONE_DIGITS = 4


def apply_pilot_id_key(
    initials: str, phone: str, char: str
) -> tuple[str, str]:
    """Apply one key to (initials, phone digits) and return the new pair.

    Letters and digits go to their own field, so both can be typed in one
    pass. Backspace erases the phone digits first, then the initials.
    """
    if char == "\b":
        if phone:
            return initials, phone[:-1]
        return initials[:-1], phone
    if len(char) != 1:
        return initials, phone
    letter = char.upper()
    if letter in string.ascii_uppercase:
        if len(initials) < MAX_INITIALS:
            initials += letter
    elif char in string.digits and len(phone) < PHONE_DIGITS:
        phone += char
    return initials, phone


def is_valid_pilot_id(initials: str, phone: str) -> bool:
    return (
        MIN_INITIALS <= len(initials) <= MAX_INITIALS
        and all(char in string.ascii_uppercase for char in initials)
        and len(phone) == PHONE_DIGITS
        and all(char in string.digits for char in phone)
    )
