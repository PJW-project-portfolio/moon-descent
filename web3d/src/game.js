// 게임 상태 머신 + 스폰 + 접촉/착륙 판정. three/DOM 비의존.
// 2D(game_state.py)와 같은 규칙: 서브스텝 단위 접지 판정, 하강 중 접지만 인정,
// 목숨 3개 + 게임 오버, 추락 시 같은 지형 재도전, 평탄 지형 비상 착륙.

import {
  SUBSTEP,
  PAD_CENTER,
  PAD_RADIUS,
  BELLY_OFFSET,
  REST_HEIGHT,
  SAFE_VSPEED,
  SAFE_HSPEED,
  SAFE_TILT_DEG,
  SAFE_ANG_VEL,
  SPAWN_OFFSET,
  SPAWN_VEL,
  SPAWN_TILT_MAX_DEG,
  STARTING_LIVES,
  EMERGENCY_FLATNESS,
} from "./constants.js";
import {
  createState,
  step,
  tiltDeg,
  footWorldPositions,
  quatFromAxisAngle,
} from "./physics.js";
import { createHeightfield } from "./heightfield.js";
import { mulberry32 } from "./rng.js";

export const GameState = {
  READY: "READY",
  FLYING: "FLYING",
  LANDED: "LANDED",
  EMERGENCY_LANDED: "EMERGENCY_LANDED",
  CRASHED: "CRASHED",
  GAME_OVER: "GAME_OVER",
};

export function createGame(seed) {
  const game = {
    seed,
    state: GameState.READY,
    field: null,
    lander: null,
    crashReason: null,
    score: 0,
    finalScore: 0,
    lives: STARTING_LIVES,
    reset,
    retry,
    start,
    update,
    altitudeAGL,
    padDistance,
  };

  // 완전 새 게임: 새 지형, 목숨/점수 초기화
  function reset(newSeed) {
    game.seed = newSeed;
    game.field = createHeightfield(newSeed);
    game.lives = STARTING_LIVES;
    game.score = 0;
    game.finalScore = 0;
    respawn();
  }

  // 같은 지형 재도전: 목숨은 그대로, 착륙선만 재배치 (2D의 재시도 규칙)
  function retry() {
    if (game.state !== GameState.CRASHED) return;
    respawn();
  }

  function respawn() {
    game.lander = spawnLander(game.seed, game.field);
    game.state = GameState.READY;
    game.crashReason = null;
  }

  function start() {
    if (game.state === GameState.READY) game.state = GameState.FLYING;
  }

  // 2D와 동일하게 10ms 서브스텝마다 접지를 검사해, 접촉 순간의
  // 속도/자세로 판정하고 지형 관통(터널링)을 막는다.
  function update(dt, inputs) {
    if (game.state !== GameState.FLYING) return;
    let remaining = Math.max(0, dt);
    while (remaining > 1e-9 && game.state === GameState.FLYING) {
      const h = Math.min(remaining, SUBSTEP);
      remaining -= h;
      step(game.lander, inputs, h);
      checkContact();
    }
  }

  // 발 4곳 + 동체 중심 아래 지형의 고저차 — 비상 착륙용 평탄도 (2D의 surface span)
  function surfaceSpanUnder(feet) {
    const s = game.lander;
    const heights = feet.map((f) => game.field.sample(f.x, f.z));
    heights.push(game.field.sample(s.pos.x, s.pos.z));
    return Math.max(...heights) - Math.min(...heights);
  }

  function checkContact() {
    const s = game.lander;
    const feet = footWorldPositions(s);
    const feetContact = feet.some((f) => f.y <= game.field.sample(f.x, f.z));
    const bellyContact =
      s.pos.y - BELLY_OFFSET <= game.field.sample(s.pos.x, s.pos.z);
    if (!feetContact && !bellyContact) return;

    const descending = s.vel.y <= 0;
    const vDown = -s.vel.y;
    const hSpeed = Math.hypot(s.vel.x, s.vel.z);
    const tilt = tiltDeg(s.quat);
    const spin = Math.hypot(s.angVel.x, s.angVel.y, s.angVel.z);
    const allOnPad = feet.every(
      (f) => Math.hypot(f.x - PAD_CENTER.x, f.z - PAD_CENTER.z) <= PAD_RADIUS,
    );
    const flatEnough = surfaceSpanUnder(feet) <= EMERGENCY_FLATNESS;

    let reason = null;
    if (!descending) reason = "상승 중에 지형과 충돌했습니다";
    else if (vDown > SAFE_VSPEED) reason = "하강 속도가 너무 빠릅니다";
    else if (hSpeed > SAFE_HSPEED) reason = "수평 속도가 너무 빠릅니다";
    else if (tilt > SAFE_TILT_DEG) reason = "기체가 너무 기울었습니다";
    else if (spin > SAFE_ANG_VEL) reason = "회전이 멈추지 않았습니다";
    else if (!allOnPad && !flatEnough)
      reason = "패드 밖 험한 지형에 부딪혔습니다";

    if (reason) {
      game.crashReason = reason;
      game.lives = Math.max(0, game.lives - 1);
      if (game.lives === 0) {
        game.finalScore = game.score;
        game.state = GameState.GAME_OVER;
      } else {
        game.state = GameState.CRASHED;
      }
      return;
    }

    // 착륙: 패드 안이면 정식 착륙(연료 보너스 포함), 패드 밖 평탄 지형이면
    // 비상 착륙(기본 점수만 — 2D와 동일한 규칙)
    game.state = allOnPad ? GameState.LANDED : GameState.EMERGENCY_LANDED;
    s.pos.y = game.field.sample(s.pos.x, s.pos.z) + REST_HEIGHT;
    s.vel = { x: 0, y: 0, z: 0 };
    s.angVel = { x: 0, y: 0, z: 0 };
    s.mainOn = false;
    const softness = 1 - Math.min(vDown / SAFE_VSPEED, 1);
    const base = 100 + softness * 100;
    game.score =
      game.state === GameState.LANDED
        ? Math.round(base + s.fuel)
        : Math.round(base);
    game.finalScore = game.score;
  }

  function altitudeAGL() {
    const s = game.lander;
    return s.pos.y - game.field.sample(s.pos.x, s.pos.z) - REST_HEIGHT;
  }

  function padDistance() {
    const s = game.lander;
    const dx = PAD_CENTER.x - s.pos.x;
    const dz = PAD_CENTER.z - s.pos.z;
    return { dx, dz, dist: Math.hypot(dx, dz) };
  }

  reset(seed);
  return game;
}

function spawnLander(seed, field) {
  const rand = mulberry32(seed ^ 0x5eed);
  const s = createState();
  s.pos = {
    x: PAD_CENTER.x + SPAWN_OFFSET.x,
    y: field.padHeight + SPAWN_OFFSET.y,
    z: PAD_CENTER.z + SPAWN_OFFSET.z,
  };
  s.vel = { ...SPAWN_VEL };
  // 무작위 수평축 기준 살짝 기울어진 채 시작 (같은 시드면 같은 스폰)
  const theta = rand() * Math.PI * 2;
  const tilt = ((rand() * SPAWN_TILT_MAX_DEG) * Math.PI) / 180;
  s.quat = quatFromAxisAngle(
    { x: Math.cos(theta), y: 0, z: Math.sin(theta) },
    tilt,
  );
  return s;
}
