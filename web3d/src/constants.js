// 모든 튜닝 상수. 단위: 미터 / 초 / 라디안 (2D 게임의 settings.py 역할)

export const GRAVITY = 1.62; // 실제 달 중력 m/s²
export const MAIN_THRUST_ACCEL = 4.5; // m/s² (TWR ≈ 2.8)
export const RCS_ANG_ACCEL = 0.8; // rad/s² (축당)
export const MAX_ANG_VEL = 1.5; // rad/s (축당 클램프)
export const SAS_DAMP_ACCEL = 1.2; // rad/s² (SAS 감쇠)

export const FUEL_CAPACITY = 100;
export const MAIN_BURN_RATE = 4.0; // 연료/s
export const RCS_BURN_RATE = 0.3; // 연료/s (활성 회전축당)

export const SUBSTEP = 0.01; // 물리 서브스텝 10ms
export const MAX_FRAME_DT = 0.1; // 탭 전환 등 긴 프레임 클램프

export const TERRAIN_SIZE = 400; // 400×400 m, 원점 중심
export const TERRAIN_SEGMENTS = 128; // 129×129 높이 그리드
export const PAD_CENTER = { x: 60, z: -45 };
export const PAD_RADIUS = 15; // 이 반경 안은 평탄 + 초록
export const PAD_BLEND = 14; // 평탄 지대 바깥 블렌딩 링 폭

// 기체 좌표계 다리 발끝 위치 (동체 중심 기준)
export const LEG_OFFSETS = [
  { x: 1.6, y: -1.9, z: 1.6 },
  { x: 1.6, y: -1.9, z: -1.6 },
  { x: -1.6, y: -1.9, z: 1.6 },
  { x: -1.6, y: -1.9, z: -1.6 },
];
export const BELLY_OFFSET = 1.2; // 동체 하부 여유 (전복 충돌 감지용)
export const REST_HEIGHT = 1.9; // 착지 시 동체 중심의 지면 위 높이

export const SAFE_VSPEED = 3.0; // m/s 최대 하강 속도
export const SAFE_HSPEED = 2.0; // m/s 최대 수평 속도
export const SAFE_TILT_DEG = 12; // 최대 기울기 (2D와 동일)
export const SAFE_ANG_VEL = 0.35; // rad/s 최대 회전 속도

export const SPAWN_OFFSET = { x: -85, y: 90, z: 70 }; // 패드 기준 스폰 위치
export const SPAWN_VEL = { x: 5, y: -2, z: -3 };
export const SPAWN_TILT_MAX_DEG = 6;

export const STARTING_LIVES = 3; // 게임 전체 목숨 (2D와 동일)
export const EMERGENCY_FLATNESS = 0.8; // m — 비상 착륙 허용 지형 고저차 (2D와 동일 기준)
