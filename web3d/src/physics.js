// 6자유도 강체 물리. three/DOM 비의존 — node --test로 직접 검증 가능.
// 2D 게임(models.py)과 같은 10ms 서브스텝 + 연료 제한 추력 방식.

import {
  GRAVITY,
  MAIN_THRUST_ACCEL,
  RCS_ANG_ACCEL,
  MAX_ANG_VEL,
  SAS_DAMP_ACCEL,
  FUEL_CAPACITY,
  MAIN_BURN_RATE,
  RCS_BURN_RATE,
  SUBSTEP,
  LEG_OFFSETS,
} from "./constants.js";

export function createState() {
  return {
    pos: { x: 0, y: 0, z: 0 },
    vel: { x: 0, y: 0, z: 0 },
    quat: { x: 0, y: 0, z: 0, w: 1 }, // 기체→월드
    angVel: { x: 0, y: 0, z: 0 }, // 기체 좌표계 rad/s
    fuel: FUEL_CAPACITY,
    mainOn: false,
    rcsActive: { x: 0, y: 0, z: 0 }, // -1/0/1 (시각 효과용)
  };
}

export function quatMultiply(a, b) {
  return {
    x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
    y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
    z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
    w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
  };
}

export function quatNormalize(q) {
  const n = Math.hypot(q.x, q.y, q.z, q.w) || 1;
  q.x /= n;
  q.y /= n;
  q.z /= n;
  q.w /= n;
  return q;
}

export function quatFromAxisAngle(axis, angle) {
  const half = angle / 2;
  const s = Math.sin(half);
  return { x: axis.x * s, y: axis.y * s, z: axis.z * s, w: Math.cos(half) };
}

// 기체 좌표 벡터 v를 쿼터니언 q로 월드 좌표로 회전
export function bodyToWorld(q, v) {
  const qv = { x: v.x, y: v.y, z: v.z, w: 0 };
  const conj = { x: -q.x, y: -q.y, z: -q.z, w: q.w };
  const r = quatMultiply(quatMultiply(q, qv), conj);
  return { x: r.x, y: r.y, z: r.z };
}

export function upVector(q) {
  return bodyToWorld(q, { x: 0, y: 1, z: 0 });
}

export function tiltDeg(q) {
  const up = upVector(q);
  const dot = Math.min(Math.max(up.y, -1), 1);
  return (Math.acos(dot) * 180) / Math.PI;
}

export function footWorldPositions(state) {
  return LEG_OFFSETS.map((leg) => {
    const w = bodyToWorld(state.quat, leg);
    return {
      x: state.pos.x + w.x,
      y: state.pos.y + w.y,
      z: state.pos.z + w.z,
    };
  });
}

// inputs: { pitch, roll, yaw: -1|0|1, mainEngine: bool, sas: bool }
// 회전축 매핑(기체 좌표): pitch→x축, yaw→y축, roll→z축
export function step(state, inputs, dt) {
  let remaining = dt;
  while (remaining > 1e-9) {
    const h = Math.min(remaining, SUBSTEP);
    remaining -= h;
    substep(state, inputs, h);
  }
}

function substep(state, inputs, h) {
  const hasFuel = state.fuel > 0;
  const commands = {
    x: hasFuel ? inputs.pitch || 0 : 0,
    y: hasFuel ? inputs.yaw || 0 : 0,
    z: hasFuel ? inputs.roll || 0 : 0,
  };
  state.rcsActive = { ...commands };

  let activeAxes = 0;
  for (const axis of ["x", "y", "z"]) {
    const cmd = commands[axis];
    if (cmd !== 0) {
      activeAxes += 1;
      state.angVel[axis] += cmd * RCS_ANG_ACCEL * h;
    } else if (inputs.sas && state.angVel[axis] !== 0) {
      // SAS: 남은 각속도를 정확히 0까지만 감쇠 (오버슛/떨림 없음)
      const brake = Math.min(SAS_DAMP_ACCEL * h, Math.abs(state.angVel[axis]));
      state.angVel[axis] -= Math.sign(state.angVel[axis]) * brake;
    }
    state.angVel[axis] = Math.min(
      Math.max(state.angVel[axis], -MAX_ANG_VEL),
      MAX_ANG_VEL,
    );
  }
  if (activeAxes > 0) {
    state.fuel = Math.max(0, state.fuel - RCS_BURN_RATE * activeAxes * h);
  }

  // 쿼터니언 적분: q̇ = ½·q⊗ω (ω는 기체 좌표계)
  const w = state.angVel;
  if (w.x !== 0 || w.y !== 0 || w.z !== 0) {
    const dq = quatMultiply(state.quat, { x: w.x, y: w.y, z: w.z, w: 0 });
    state.quat.x += 0.5 * dq.x * h;
    state.quat.y += 0.5 * dq.y * h;
    state.quat.z += 0.5 * dq.z * h;
    state.quat.w += 0.5 * dq.w * h;
    quatNormalize(state.quat);
  }

  state.vel.y -= GRAVITY * h;

  state.mainOn = false;
  if (inputs.mainEngine && state.fuel > 0) {
    // 연료가 부족하면 마지막 서브스텝에서 탈 수 있는 만큼만 연소
    const burnTime = Math.min(h, state.fuel / MAIN_BURN_RATE);
    state.fuel = Math.max(0, state.fuel - MAIN_BURN_RATE * burnTime);
    const dv = MAIN_THRUST_ACCEL * burnTime;
    const dir = upVector(state.quat);
    state.vel.x += dir.x * dv;
    state.vel.y += dir.y * dv;
    state.vel.z += dir.z * dv;
    state.mainOn = true;
  }

  state.pos.x += state.vel.x * h;
  state.pos.y += state.vel.y * h;
  state.pos.z += state.vel.z * h;
}
