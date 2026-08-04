import test from "node:test";
import assert from "node:assert/strict";
import { createGame, GameState } from "../src/game.js";
import { quatFromAxisAngle } from "../src/physics.js";
import {
  PAD_CENTER,
  PAD_RADIUS,
  PAD_BLEND,
  REST_HEIGHT,
  EMERGENCY_FLATNESS,
  STARTING_LIVES,
} from "../src/constants.js";

const IDLE = { pitch: 0, roll: 0, yaw: 0, mainEngine: false, sas: true };

function placeAt(game, x, z, { height = 1, vy = -1, vx = 0, tilt = 0 } = {}) {
  const s = game.lander;
  s.pos = {
    x,
    y: game.field.sample(x, z) + REST_HEIGHT + height,
    z,
  };
  s.vel = { x: vx, y: vy, z: 0 };
  s.quat = tilt
    ? quatFromAxisAngle({ x: 0, y: 0, z: 1 }, (tilt * Math.PI) / 180)
    : { x: 0, y: 0, z: 0, w: 1 };
  s.angVel = { x: 0, y: 0, z: 0 };
  game.start();
}

function placeAbovePad(game, opts = {}) {
  placeAt(game, PAD_CENTER.x, PAD_CENTER.z, opts);
}

function runUntilSettled(game, maxSeconds = 30) {
  for (let t = 0; t < maxSeconds && game.state === GameState.FLYING; t += 0.01) {
    game.update(0.01, IDLE);
  }
}

// 발 4곳 + 중심 아래 지형 고저차 (game.js의 surfaceSpanUnder와 동일 기준)
function surfaceSpanAt(field, x, z) {
  const pts = [
    [1.6, 1.6],
    [1.6, -1.6],
    [-1.6, 1.6],
    [-1.6, -1.6],
    [0, 0],
  ];
  const hs = pts.map(([dx, dz]) => field.sample(x + dx, z + dz));
  return Math.max(...hs) - Math.min(...hs);
}

// 패드 영향권 밖에서 조건을 만족하는 지점 탐색
function findOffPadSpot(field, predicate) {
  for (let x = -180; x <= 180; x += 4) {
    for (let z = -180; z <= 180; z += 4) {
      const d = Math.hypot(x - PAD_CENTER.x, z - PAD_CENTER.z);
      if (d < PAD_RADIUS + PAD_BLEND + 6) continue;
      if (predicate(surfaceSpanAt(field, x, z))) return { x, z };
    }
  }
  return null;
}

test("패드 중앙 연착륙 → LANDED + 점수", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 1, vy: -1 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.LANDED);
  assert.ok(game.score > 100, `score=${game.score}`);
  assert.ok(Math.abs(game.altitudeAGL()) < 0.01);
});

test("접지 판정은 서브스텝 단위 — 긴 프레임 하나로도 접촉 순간 속도로 판정", () => {
  const game = createGame(1);
  // 접촉 직전 안전 속도로 배치한 뒤 0.5초짜리 프레임 한 번에 전달.
  // 프레임 끝 속도(-3.7 m/s)가 아니라 접촉 순간 속도로 판정되어야 착륙 성공.
  placeAbovePad(game, { height: 0.05, vy: -2.9 });
  game.update(0.5, IDLE);
  assert.equal(game.state, GameState.LANDED);
});

test("상승 중 접지는 착륙으로 인정하지 않음", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: -0.2, vy: 1 });
  game.update(0.05, IDLE);
  assert.equal(game.state, GameState.CRASHED);
  assert.match(game.crashReason, /상승/);
});

test("패드 밖 평탄 지형 연착륙 → 비상 착륙 (기본 점수만)", () => {
  const game = createGame(1);
  const spot = findOffPadSpot(game.field, (span) => span <= EMERGENCY_FLATNESS * 0.5);
  assert.ok(spot, "시드 1 지형에서 평탄한 지점을 찾지 못함");
  placeAt(game, spot.x, spot.z, { height: 1, vy: -1 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.EMERGENCY_LANDED);
  // 기본 점수만: 연료 보너스(100)가 빠져 정식 착륙보다 낮아야 함
  assert.ok(game.score > 0 && game.score <= 200, `score=${game.score}`);
});

test("패드 밖 험한 지형 착지 → CRASHED (지형)", () => {
  const game = createGame(1);
  const spot = findOffPadSpot(game.field, (span) => span > EMERGENCY_FLATNESS * 1.5);
  assert.ok(spot, "시드 1 지형에서 험한 지점을 찾지 못함");
  placeAt(game, spot.x, spot.z, { height: 1, vy: -1 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  assert.match(game.crashReason, /지형/);
});

test("급강하 착지 → CRASHED (하강 속도)", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 10, vy: -12 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  assert.match(game.crashReason, /하강 속도/);
});

test("수평 속도 과다 → CRASHED (수평 속도)", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 1.5, vy: -0.5, vx: 4 });
  runUntilSettled(game, 5);
  assert.equal(game.state, GameState.CRASHED);
  assert.match(game.crashReason, /수평 속도/);
});

test("20° 기울어진 착지 → CRASHED (기울기)", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 1, vy: -1, tilt: 20 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  assert.match(game.crashReason, /기울/);
});

test("추락 시 retry는 같은 지형 유지 + 목숨 차감", () => {
  const game = createGame(3);
  const fieldRef = game.field;
  placeAbovePad(game, { height: 10, vy: -12 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  assert.equal(game.lives, STARTING_LIVES - 1);
  game.retry();
  assert.equal(game.state, GameState.READY);
  assert.equal(game.field, fieldRef, "지형이 바뀌면 안 됨");
  assert.equal(game.lives, STARTING_LIVES - 1, "재도전은 목숨을 복구하지 않음");
  assert.equal(game.lander.fuel, 100);
  assert.equal(game.crashReason, null);
});

test("3번째 추락 → GAME_OVER + 최종 점수 확정", () => {
  const game = createGame(3);
  for (let i = 0; i < STARTING_LIVES; i++) {
    placeAbovePad(game, { height: 10, vy: -12 });
    runUntilSettled(game);
    if (i < STARTING_LIVES - 1) {
      assert.equal(game.state, GameState.CRASHED);
      game.retry();
    }
  }
  assert.equal(game.state, GameState.GAME_OVER);
  assert.equal(game.lives, 0);
  assert.equal(game.finalScore, game.score);
  // GAME_OVER 상태에서는 retry 불가 (새 게임만 가능)
  game.retry();
  assert.equal(game.state, GameState.GAME_OVER);
});

test("reset은 새 시드 + 목숨/점수 초기화", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 10, vy: -12 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  game.reset(2);
  assert.equal(game.state, GameState.READY);
  assert.equal(game.crashReason, null);
  assert.equal(game.lives, STARTING_LIVES);
  assert.equal(game.score, 0);
  assert.equal(game.lander.fuel, 100);
});

test("스폰 위치는 지형보다 충분히 높다", () => {
  for (const seed of [1, 2, 42, 999]) {
    const game = createGame(seed);
    assert.ok(game.altitudeAGL() > 50, `seed=${seed} alt=${game.altitudeAGL()}`);
  }
});
