"""Stage definitions: real celestial bodies with true surface gravity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StageConfig:
    name: str                    # HUD 표기용 (영문 대문자)
    gravity_ms2: float           # 실제 표면 중력 (m/s^2)
    fuel_burn_per_second: float  # 스테이지별 연료 소모율 (밸런스 튜닝값)
    par_time_seconds: float      # 시간 보너스 기준 기록
    sky: tuple[int, int, int]
    terrain_color: tuple[int, int, int]
    ground_fill: tuple[int, int, int]
    star_color: tuple[int, int, int]
    star_count: int


STAGES = (
    StageConfig(
        "MOON",
        1.62,
        15.0,
        45.0,
        (4, 7, 9),
        (180, 255, 202),
        (8, 18, 16),
        (74, 110, 92),
        115,
    ),
    StageConfig(
        "MARS",
        3.71,
        13.0,
        50.0,
        (14, 6, 4),
        (255, 138, 84),
        (32, 11, 6),
        (110, 80, 66),
        70,
    ),
    StageConfig(
        "VENUS",
        8.87,
        10.0,
        60.0,
        (20, 15, 5),
        (236, 198, 108),
        (36, 27, 9),
        (0, 0, 0),
        0,
    ),
)
