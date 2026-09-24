"""Pilot ID entry: Korean initial consonants (초성) + last four phone digits."""

from __future__ import annotations


# 한글 호환 자모의 초성 19자. 리더보드와 기록 파일에는 이 문자 그대로 저장한다.
CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"

# 두벌식 자판에서 자음이 인쇄된 키. Shift는 된소리를 만들고, 된소리가 없는
# 자음은 Shift를 눌러도 같은 자음이 된다(표준 두벌식 동작과 동일).
_SINGLE_KEYS = {
    "q": "ㅂ",
    "w": "ㅈ",
    "e": "ㄷ",
    "r": "ㄱ",
    "t": "ㅅ",
    "a": "ㅁ",
    "s": "ㄴ",
    "d": "ㅇ",
    "f": "ㄹ",
    "g": "ㅎ",
    "z": "ㅋ",
    "x": "ㅌ",
    "c": "ㅊ",
    "v": "ㅍ",
}
_SHIFTED_KEYS = {"Q": "ㅃ", "W": "ㅉ", "E": "ㄸ", "R": "ㄲ", "T": "ㅆ"}
KEY_TO_CHOSEONG = {
    **_SINGLE_KEYS,
    **{key.upper(): consonant for key, consonant in _SINGLE_KEYS.items()},
    **_SHIFTED_KEYS,
}

MIN_INITIALS = 2
MAX_INITIALS = 4
PHONE_DIGITS = 4
_DIGITS = "0123456789"

INITIALS_LABEL = "초성"
PHONE_LABEL = f"전화번호 뒤 {PHONE_DIGITS}자리"
ENTRY_GUIDE = "한/영 전환 없이 자음 키를 그대로 누르세요"
ENTRY_ERROR = (
    f"초성 {MIN_INITIALS}~{MAX_INITIALS}자와 "
    f"전화번호 뒤 {PHONE_DIGITS}자리를 입력하세요"
)
KEYMAP_HINT = (
    "  ".join(f"{key.upper()} {_SINGLE_KEYS[key]}" for key in "qwertasdfg"),
    "  ".join(f"{key.upper()} {_SINGLE_KEYS[key]}" for key in "zxcv")
    + "   SHIFT+"
    + "  ".join(f"{key} {_SHIFTED_KEYS[key]}" for key in "QWERT"),
)
# scripts/make_korean_font.py는 이 문자열들로 한글 폰트 서브셋을 만든다.
KOREAN_UI_TEXT = (
    CHOSEONG,
    INITIALS_LABEL,
    PHONE_LABEL,
    ENTRY_GUIDE,
    ENTRY_ERROR,
    *KEYMAP_HINT,
)


def apply_pilot_id_key(
    initials: str, phone: str, char: str
) -> tuple[str, str]:
    """Apply one key to (initials, phone digits) and return the new pair.

    Consonant keys and digits go to their own field, so both can be typed
    in one pass. Backspace erases the phone digits first, then the initials.
    """
    if char == "\b":
        if phone:
            return initials, phone[:-1]
        return initials[:-1], phone
    if len(char) != 1:
        return initials, phone
    consonant = KEY_TO_CHOSEONG.get(char, char)
    if consonant in CHOSEONG:
        if len(initials) < MAX_INITIALS:
            initials += consonant
    elif char in _DIGITS and len(phone) < PHONE_DIGITS:
        phone += char
    return initials, phone


def is_valid_pilot_id(initials: str, phone: str) -> bool:
    return (
        MIN_INITIALS <= len(initials) <= MAX_INITIALS
        and all(char in CHOSEONG for char in initials)
        and len(phone) == PHONE_DIGITS
        and all(char in _DIGITS for char in phone)
    )
