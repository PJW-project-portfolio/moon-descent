// three.js 장면 구성: 지형 메시(높이 그리드 공유), 초록 패드, 별, 조명,
// 착륙선 모델(프리미티브 조합), 메인 엔진 화염 / RCS 분사 이펙트

import * as THREE from "../vendor/three.module.min.js";
import {
  TERRAIN_SIZE,
  TERRAIN_SEGMENTS,
  PAD_CENTER,
  PAD_RADIUS,
  LEG_OFFSETS,
} from "./constants.js";

export function createScene(field) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x050510);
  scene.fog = new THREE.Fog(0x050510, 250, 600);

  scene.add(new THREE.AmbientLight(0x223344, 1.2));
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.0);
  sun.position.set(-150, 220, 100);
  scene.add(sun);

  scene.add(buildTerrain(field));
  const padRing = buildPadRing(field);
  scene.add(padRing);
  const beacon = new THREE.PointLight(0x33ff77, 30, 80);
  beacon.position.set(PAD_CENTER.x, field.padHeight + 4, PAD_CENTER.z);
  scene.add(beacon);
  scene.add(buildStars());

  const lander = buildLander();
  scene.add(lander.group);

  let beaconTime = 0;
  return {
    scene,
    lander,
    syncLander(state) {
      lander.group.position.set(state.pos.x, state.pos.y, state.pos.z);
      lander.group.quaternion.set(
        state.quat.x,
        state.quat.y,
        state.quat.z,
        state.quat.w,
      );
      lander.flame.visible = state.mainOn;
      if (state.mainOn) {
        lander.flame.scale.y = 0.8 + Math.random() * 0.5;
      }
      lander.rcs.forEach((p) => {
        p.mesh.visible = state.rcsActive[p.axis] === p.sign;
      });
    },
    setLanderVisible(v) {
      lander.group.visible = v;
    },
    tick(dt) {
      beaconTime += dt;
      beacon.intensity = 15 + 15 * Math.sin(beaconTime * 5);
      padRing.material.opacity = 0.55 + 0.35 * Math.sin(beaconTime * 5);
    },
  };
}

function buildTerrain(field) {
  const n = TERRAIN_SEGMENTS;
  const verts = n + 1;
  const geo = new THREE.BufferGeometry();
  const positions = new Float32Array(verts * verts * 3);
  const colors = new Float32Array(verts * verts * 3);
  const gray = new THREE.Color(0x8a8a8a);
  const green = new THREE.Color(0x22dd55);

  let minH = Infinity;
  let maxH = -Infinity;
  for (let i = 0; i < field.heights.length; i++) {
    minH = Math.min(minH, field.heights[i]);
    maxH = Math.max(maxH, field.heights[i]);
  }

  for (let iz = 0; iz < verts; iz++) {
    for (let ix = 0; ix < verts; ix++) {
      const i = iz * verts + ix;
      const x = (ix / n) * TERRAIN_SIZE - TERRAIN_SIZE / 2;
      const z = (iz / n) * TERRAIN_SIZE - TERRAIN_SIZE / 2;
      const h = field.heights[i];
      positions[i * 3] = x;
      positions[i * 3 + 1] = h;
      positions[i * 3 + 2] = z;
      // 고도에 따라 살짝 밝기 차이를 주고, 패드 안은 초록으로
      const shade = 0.75 + (0.5 * (h - minH)) / Math.max(maxH - minH, 1e-6);
      const c = field.isOnPad(x, z) ? green : gray.clone().multiplyScalar(shade);
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
  }

  const index = [];
  for (let iz = 0; iz < n; iz++) {
    for (let ix = 0; ix < n; ix++) {
      const a = iz * verts + ix;
      const b = a + 1;
      const c = a + verts;
      const d = c + 1;
      index.push(a, c, b, b, c, d);
    }
  }

  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geo.setIndex(index);
  geo.computeVertexNormals();
  return new THREE.Mesh(
    geo,
    new THREE.MeshLambertMaterial({ vertexColors: true }),
  );
}

function buildPadRing(field) {
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(PAD_RADIUS - 1, PAD_RADIUS, 48),
    new THREE.MeshBasicMaterial({
      color: 0x33ff77,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide,
    }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.set(PAD_CENTER.x, field.padHeight + 0.1, PAD_CENTER.z);
  return ring;
}

function buildStars() {
  const count = 1200;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    // 상반구 돔에 균일 분포
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(Math.random());
    const r = 500;
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = Math.abs(r * Math.cos(phi)) + 5;
    positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  return new THREE.Points(
    geo,
    new THREE.PointsMaterial({ color: 0xccccdd, size: 1.4, sizeAttenuation: false, fog: false }),
  );
}

function buildLander() {
  const group = new THREE.Group();
  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0xb8b0a0,
    metalness: 0.4,
    roughness: 0.6,
  });
  const goldMat = new THREE.MeshStandardMaterial({
    color: 0xc9a227,
    metalness: 0.7,
    roughness: 0.4,
  });

  const body = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.1, 1.4, 8), goldMat);
  body.position.y = -0.3;
  group.add(body);

  const cabin = new THREE.Mesh(new THREE.SphereGeometry(0.85, 12, 8), bodyMat);
  cabin.position.y = 0.75;
  group.add(cabin);

  const bell = new THREE.Mesh(
    new THREE.CylinderGeometry(0.25, 0.55, 0.6, 10, 1, true),
    new THREE.MeshStandardMaterial({
      color: 0x555555,
      metalness: 0.8,
      roughness: 0.3,
      side: THREE.DoubleSide,
    }),
  );
  bell.position.y = -1.2;
  group.add(bell);

  const legMat = new THREE.MeshStandardMaterial({ color: 0x888888 });
  for (const leg of LEG_OFFSETS) {
    const start = new THREE.Vector3(leg.x * 0.45, -0.7, leg.z * 0.45);
    const end = new THREE.Vector3(leg.x, leg.y, leg.z);
    const dir = end.clone().sub(start);
    const strut = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, dir.length(), 6),
      legMat,
    );
    strut.position.copy(start.clone().add(end).multiplyScalar(0.5));
    strut.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      dir.clone().normalize(),
    );
    group.add(strut);
    const foot = new THREE.Mesh(
      new THREE.CylinderGeometry(0.22, 0.22, 0.08, 10),
      legMat,
    );
    foot.position.copy(end);
    group.add(foot);
  }

  // 메인 엔진 화염 (아래 방향 원뿔, 가산 블렌딩)
  const flame = new THREE.Mesh(
    new THREE.ConeGeometry(0.4, 2.2, 10),
    new THREE.MeshBasicMaterial({
      color: 0xff9933,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
  );
  flame.rotation.x = Math.PI; // 꼭짓점이 아래로
  flame.position.y = -2.4;
  flame.visible = false;
  flame.layers.set(1); // 하방 카메라(레이어 0 전용)의 시야를 가리지 않도록 분리
  group.add(flame);

  // RCS 분사 표시: 회전 축·방향별 작은 청록 원뿔 (동체 상단 주변)
  const rcs = [];
  const rcsMat = new THREE.MeshBasicMaterial({
    color: 0x66eeff,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const addPuff = (axis, sign, pos, rotation) => {
    const puff = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.6, 6), rcsMat);
    puff.position.copy(pos);
    puff.rotation.copy(rotation);
    puff.visible = false;
    group.add(puff);
    rcs.push({ axis, sign, mesh: puff });
  };
  // 피치(x축): 앞뒤 노즐이 위/아래로 분사하는 형태를 단순화해 표시
  addPuff("x", 1, new THREE.Vector3(0, 1.2, -1.1), new THREE.Euler(0, 0, 0));
  addPuff("x", -1, new THREE.Vector3(0, 1.2, 1.1), new THREE.Euler(0, 0, 0));
  // 롤(z축): 좌/우
  addPuff("z", 1, new THREE.Vector3(1.1, 1.2, 0), new THREE.Euler(0, 0, 0));
  addPuff("z", -1, new THREE.Vector3(-1.1, 1.2, 0), new THREE.Euler(0, 0, 0));
  // 요(y축): 측면 수평 분사
  addPuff("y", 1, new THREE.Vector3(1.1, 0.4, 0), new THREE.Euler(Math.PI / 2, 0, 0));
  addPuff("y", -1, new THREE.Vector3(-1.1, 0.4, 0), new THREE.Euler(-Math.PI / 2, 0, 0));

  return { group, flame, rcs };
}
