"""Build the Hangul subset font that draws pilot IDs (초성) on screen.

DejaVu Sans Mono has no Hangul glyphs, so the game ships a small subset of
Noto Sans Mono CJK KR (SIL Open Font License 1.1) covering printable ASCII
and every Korean string in lunar_lander.pilot_id.KOREAN_UI_TEXT.
Re-run after changing any of those strings:

    python -m pip install fonttools
    python scripts/make_korean_font.py [path/to/NotoSansMonoCJKkr-Regular.otf]
"""

from pathlib import Path
import sys
import tempfile
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lunar_lander.pilot_id import KOREAN_UI_TEXT  # noqa: E402


SOURCE_URL = (
    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/"
    "Sans/Mono/NotoSansMonoCJKkr-Regular.otf"
)
OUTPUT = (
    PROJECT_ROOT
    / "lunar_lander"
    / "assets"
    / "fonts"
    / "NotoSansMonoCJKkr-Subset.otf"
)


def main() -> None:
    if len(sys.argv) > 1:
        source = Path(sys.argv[1])
    else:
        source = Path(tempfile.gettempdir()) / "NotoSansMonoCJKkr-Regular.otf"
        if not source.exists():
            print(f"다운로드: {SOURCE_URL}")
            urllib.request.urlretrieve(SOURCE_URL, source)

    ascii_text = "".join(chr(code) for code in range(0x20, 0x7F))
    options = subset.Options()
    options.name_IDs = ["*"]  # 저작권·OFL 라이선스 이름 레코드 유지
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=ascii_text + "".join(KOREAN_UI_TEXT))

    # recalcTimestamp=False: 같은 입력이면 매번 같은 바이트를 만든다.
    font = TTFont(source, recalcTimestamp=False)
    subsetter.subset(font)
    font.save(OUTPUT)
    print(f"생성 완료: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
