import test from "node:test";
import assert from "node:assert/strict";
import { createGame, GameState } from "../src/game.js";
import { quatFromAxisAngle } from "../src/physics.js";
import { PAD_CENTER, REST_HEIGHT } from "../src/constants.js";

const IDLE = { pitch: 0, roll: 0, yaw: 0, mainEngine: false, sas: true };

function placeAbovePad(game, { height = 5, vy = -1, vx = 0, offsetX = 0, tilt = 0 } = {}) {
  const s = game.lander;
  s.pos = {
    x: PAD_CENTER.x + offsetX,
    y: game.field.padHeight + REST_HEIGHT + height,
    z: PAD_CENTER.z,
  };
  s.vel = { x: vx, y: vy, z: 0 };
  s.quat = tilt
    ? quatFromAxisAngle({ x: 0, y: 0, z: 1 }, (tilt * Math.PI) / 180)
    : { x: 0, y: 0, z: 0, w: 1 };
  s.angVel = { x: 0, y: 0, z: 0 };
  game.start();
}

function runUntilSettled(game, maxSeconds = 30) {
  for (let t = 0; t < maxSeconds && game.state === GameState.FLYING; t += 0.01) {
    game.update(0.01, IDLE);
  }
}

test("패드 중앙 연착륙 → LANDED + 점수", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 1, vy: -1 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.LANDED);
  assert.ok(game.score > 0);
  assert.ok(Math.abs(game.altitudeAGL()) < 0.01);
});

test("패드에서 20m 벗어난 착지 → CRASHED (패드 이탈)", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 1, vy: -1, offsetX: 20 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  assert.match(game.crashReason, /패드/);
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

test("reset은 새 시드로 READY 상태 복귀", () => {
  const game = createGame(1);
  placeAbovePad(game, { height: 3, vy: -12 });
  runUntilSettled(game);
  assert.equal(game.state, GameState.CRASHED);
  game.reset(2);
  assert.equal(game.state, GameState.READY);
  assert.equal(game.crashReason, null);
  assert.equal(game.lander.fuel, 100);
});

test("스폰 위치는 지형보다 충분히 높다", () => {
  for (const seed of [1, 2, 42, 999]) {
    const game = createGame(seed);
    assert.ok(game.altitudeAGL() > 50, `seed=${seed} alt=${game.altitudeAGL()}`);
  }
});
