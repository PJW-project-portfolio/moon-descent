// 게임 상태 머신 + 스폰 + 접촉/착륙 판정. three/DOM 비의존.

import {
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
  CRASHED: "CRASHED",
};

export function createGame(seed) {
  const game = {
    seed,
    state: GameState.READY,
    field: null,
    lander: null,
    crashReason: null,
    score: 0,
    reset,
    start,
    update,
    altitudeAGL,
    padDistance,
  };

  function reset(newSeed) {
    game.seed = newSeed;
    game.field = createHeightfield(newSeed);
    game.lander = spawnLander(newSeed, game.field);
    game.state = GameState.READY;
    game.crashReason = null;
    game.score = 0;
  }

  function start() {
    if (game.state === GameState.READY) game.state = GameState.FLYING;
  }

  function update(dt, inputs) {
    if (game.state !== GameState.FLYING) return;
    step(game.lander, inputs, dt);
    checkContact();
  }

  function checkContact() {
    const s = game.lander;
    const feet = footWorldPositions(s);
    const feetContact = feet.some((f) => f.y <= game.field.sample(f.x, f.z));
    const bellyContact =
      s.pos.y - BELLY_OFFSET <= game.field.sample(s.pos.x, s.pos.z);
    if (!feetContact && !bellyContact) return;

    const vDown = -s.vel.y;
    const hSpeed = Math.hypot(s.vel.x, s.vel.z);
    const tilt = tiltDeg(s.quat);
    const spin = Math.hypot(s.angVel.x, s.angVel.y, s.angVel.z);
    const allOnPad = feet.every(
      (f) => Math.hypot(f.x - PAD_CENTER.x, f.z - PAD_CENTER.z) <= PAD_RADIUS,
    );

    let reason = null;
    if (!allOnPad) reason = "착륙 패드를 벗어났습니다";
    else if (vDown > SAFE_VSPEED) reason = "하강 속도가 너무 빠릅니다";
    else if (hSpeed > SAFE_HSPEED) reason = "수평 속도가 너무 빠릅니다";
    else if (tilt > SAFE_TILT_DEG) reason = "기체가 너무 기울었습니다";
    else if (spin > SAFE_ANG_VEL) reason = "회전이 멈추지 않았습니다";

    if (reason) {
      game.state = GameState.CRASHED;
      game.crashReason = reason;
      return;
    }

    game.state = GameState.LANDED;
    s.pos.y = game.field.padHeight + REST_HEIGHT;
    s.vel = { x: 0, y: 0, z: 0 };
    s.angVel = { x: 0, y: 0, z: 0 };
    s.mainOn = false;
    // 점수 = 남은 연료 + 부드러운 착륙 보너스
    const softness = 1 - Math.min(vDown / SAFE_VSPEED, 1);
    game.score = Math.round(s.fuel + softness * 100);
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
  // 무작위 수평축 기준 살짝 기울어진 채 시작
  const theta = rand() * Math.PI * 2;
  const tilt = ((rand() * SPAWN_TILT_MAX_DEG) * Math.PI) / 180;
  s.quat = quatFromAxisAngle(
    { x: Math.cos(theta), y: 0, z: Math.sin(theta) },
    tilt,
  );
  return s;
}
