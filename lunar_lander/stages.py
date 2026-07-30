"""Stage definitions: real celestial bodies with true surface gravity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StageConfig:
    name: str                    # HUD 표기용 (영문 대문자)
    gravity_ms2: float           # 실제 표면 중력 (m/s^2)
    fuel_burn_per_second: float  # 스테이지별 연료 소모율 (밸런스 튜닝값)


STAGES = (
    StageConfig("MOON", 1.62, 15.0),
    StageConfig("MARS", 3.71, 13.0),
    StageConfig("VENUS", 8.87, 10.0),
    StageConfig("EUROPA", 1.31, 15.0),
    StageConfig("TITAN", 1.35, 15.0),
)
