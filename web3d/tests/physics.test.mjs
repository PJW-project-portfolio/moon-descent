import test from "node:test";
import assert from "node:assert/strict";
import {
  createState,
  step,
  tiltDeg,
  upVector,
  bodyToWorld,
  quatFromAxisAngle,
} from "../src/physics.js";
import {
  GRAVITY,
  MAIN_THRUST_ACCEL,
  MAIN_BURN_RATE,
  FUEL_CAPACITY,
} from "../src/constants.js";

const IDLE = { pitch: 0, roll: 0, yaw: 0, mainEngine: false, sas: false };

test("자유 낙하 2초는 ½gt²와 일치", () => {
  const s = createState();
  s.pos.y = 100;
  for (let i = 0; i < 200; i++) step(s, IDLE, 0.01);
  const expected = 100 - 0.5 * GRAVITY * 4;
  assert.ok(Math.abs(s.pos.y - expected) < 0.1, `${s.pos.y} vs ${expected}`);
});

test("직립 풀스로틀은 (추력-중력)만큼 상승 가속", () => {
  const s = createState();
  const inputs = { ...IDLE, mainEngine: true };
  for (let i = 0; i < 100; i++) step(s, inputs, 0.01);
  const expected = (MAIN_THRUST_ACCEL - GRAVITY) * 1.0;
  assert.ok(Math.abs(s.vel.y - expected) < 0.05, `${s.vel.y} vs ${expected}`);
});

test("연료는 정확한 속도로 소모되고 0에서 추력 정지", () => {
  const s = createState();
  const inputs = { ...IDLE, mainEngine: true };
  step(s, inputs, 1.0);
  assert.ok(Math.abs(s.fuel - (FUEL_CAPACITY - MAIN_BURN_RATE)) < 1e-6);
  const totalBurnTime = FUEL_CAPACITY / MAIN_BURN_RATE;
  for (let t = 1.0; t < totalBurnTime + 5; t += 0.5) step(s, inputs, 0.5);
  assert.equal(s.fuel, 0);
  assert.equal(s.mainOn, false);
  // 총 Δv = 추력가속 × 총연소시간 - 중력 손실
  const elapsed = Math.ceil((totalBurnTime + 5 - 1.0) / 0.5) * 0.5 + 1.0;
  const expectedVy = MAIN_THRUST_ACCEL * totalBurnTime - GRAVITY * elapsed;
  assert.ok(Math.abs(s.vel.y - expectedVy) < 0.05, `${s.vel.y} vs ${expectedVy}`);
});

test("10초 회전 후에도 쿼터니언 노름은 1 유지", () => {
  const s = createState();
  const inputs = { ...IDLE, pitch: 1, yaw: -1, roll: 1 };
  for (let i = 0; i < 1000; i++) step(s, inputs, 0.01);
  const q = s.quat;
  const norm = Math.hypot(q.x, q.y, q.z, q.w);
  assert.ok(Math.abs(norm - 1) < 1e-9);
});

test("요(yaw) 회전은 기체 상방 벡터를 바꾸지 않는다", () => {
  const s = createState();
  const inputs = { ...IDLE, yaw: 1 };
  for (let i = 0; i < 300; i++) step(s, inputs, 0.01);
  const up = upVector(s.quat);
  assert.ok(Math.abs(up.y - 1) < 1e-6, `up.y=${up.y}`);
  assert.ok(tiltDeg(s.quat) < 0.01);
  // 전방 벡터는 회전했어야 함
  const fwd = bodyToWorld(s.quat, { x: 0, y: 0, z: -1 });
  assert.ok(Math.abs(fwd.z + 1) > 0.01, "전방이 회전하지 않았음");
});

test("SAS는 입력이 없으면 각속도를 정확히 0으로 감쇠", () => {
  const s = createState();
  s.angVel = { x: 0.6, y: -0.4, z: 0.2 };
  const inputs = { ...IDLE, sas: true };
  for (let i = 0; i < 300; i++) step(s, inputs, 0.01);
  assert.equal(s.angVel.x, 0);
  assert.equal(s.angVel.y, 0);
  assert.equal(s.angVel.z, 0);
});

test("기울인 상태의 추력은 수평 성분을 만든다", () => {
  const s = createState();
  // z축(롤) 기준 30° 기울임 → 상방 벡터가 x 성분을 가짐
  s.quat = quatFromAxisAngle({ x: 0, y: 0, z: 1 }, Math.PI / 6);
  const inputs = { ...IDLE, mainEngine: true };
  for (let i = 0; i < 100; i++) step(s, inputs, 0.01);
  assert.ok(Math.abs(s.vel.x) > 0.5, `vel.x=${s.vel.x}`);
});
