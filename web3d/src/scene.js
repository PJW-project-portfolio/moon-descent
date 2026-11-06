// three.js 장면 구성: 지형 메시(높이 그리드 공유, 표토 텍스처 + 범프),
// 초록 패드, 자갈, 별, 낮은 태양 + 실시간 그림자, 착륙선 모델(프리미티브 조합),
// 메인 엔진 화염 / RCS 분사 이펙트

import * as THREE from "../vendor/three.module.min.js";
import {
  TERRAIN_SIZE,
  TERRAIN_SEGMENTS,
  PAD_CENTER,
  PAD_RADIUS,
  LEG_OFFSETS,
} from "./constants.js";
import { getRegolithTextures, TILE_METERS } from "./surface.js";
import { mulberry32 } from "./rng.js";

// 낮은 고도(약 24°)의 태양을 스폰 지점 뒤쪽에 둔다. 아폴로 착륙처럼 그림자가
// 길게 늘어져 크레이터 요철이 드러나고, 착륙선 그림자가 진행 방향 앞에 떨어진다.
const SUN_DIR = new THREE.Vector3(-0.707, 0.407, 0.579).normalize();

export function createScene(field, { maxAnisotropy = 1 } = {}) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x050510);
  scene.fog = new THREE.Fog(0x050510, 250, 600);

  // 대기가 없어 그늘은 매우 어둡지만, 조종이 가능하도록 약한 보조광을 둔다
  scene.add(new THREE.HemisphereLight(0x8090a8, 0x2a2622, 0.35));
  scene.add(new THREE.AmbientLight(0x404858, 0.25));
  scene.add(buildSun());

  scene.add(buildTerrain(field, maxAnisotropy));
  const rocks = buildRocks(field);
  scene.add(rocks.object);
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
      rocks.update(state.pos);
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
    // 새 게임으로 장면을 갈아끼울 때 GPU 자원 해제 (표토 텍스처는 공유 캐시라 유지)
    dispose() {
      scene.traverse((obj) => {
        if (obj.isLight && obj.dispose) obj.dispose(); // 그림자 맵(4096²) 해제
        if (obj.geometry) obj.geometry.dispose();
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        for (const m of mats) if (m) m.dispose();
      });
    },
    tick(dt) {
      beaconTime += dt;
      beacon.intensity = 15 + 15 * Math.sin(beaconTime * 5);
      padRing.material.opacity = 0.55 + 0.35 * Math.sin(beaconTime * 5);
    },
  };
}

// 지형 한 장에 걸친 그림자 맵. 착륙선·자갈·크레이터 테두리가 모두 그림자를 드리운다.
function buildSun() {
  const sun = new THREE.DirectionalLight(0xfff6e8, 3.2);
  sun.position.copy(SUN_DIR).multiplyScalar(500);
  // 타깃을 태양의 자식으로 두어 장면에 따로 추가하지 않아도 원점을 겨누게 한다
  sun.add(sun.target);
  sun.target.position.copy(SUN_DIR).multiplyScalar(-500);
  sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096);
  const half = TERRAIN_SIZE * 0.72;
  Object.assign(sun.shadow.camera, {
    left: -half,
    right: half,
    top: half,
    bottom: -half,
    near: 100,
    far: 900,
  });
  sun.shadow.camera.updateProjectionMatrix();
  // 낮은 태양각에서 경사면에 생기는 줄무늬(shadow acne) 방지
  sun.shadow.bias = -0.0015;
  sun.shadow.normalBias = 0.25;
  return sun;
}

function buildTerrain(field, maxAnisotropy) {
  const n = TERRAIN_SEGMENTS;
  const verts = n + 1;
  const geo = new THREE.BufferGeometry();
  const positions = new Float32Array(verts * verts * 3);
  const colors = new Float32Array(verts * verts * 3);
  const uvs = new Float32Array(verts * verts * 2);
  const green = new THREE.Color(0x3dff6e);

  // 넓은 범위의 밝기 얼룩 (타일 반복이 눈에 띄지 않도록 텍스처 위에 곱해짐)
  const blotch = valueNoise2D(mulberry32(field.padHeight * 1000 + 7), 10);
  const fine = valueNoise2D(mulberry32(field.padHeight * 1000 + 11), 40);

  for (let iz = 0; iz < verts; iz++) {
    for (let ix = 0; ix < verts; ix++) {
      const i = iz * verts + ix;
      const u = ix / n;
      const v = iz / n;
      const x = u * TERRAIN_SIZE - TERRAIN_SIZE / 2;
      const z = v * TERRAIN_SIZE - TERRAIN_SIZE / 2;
      positions[i * 3] = x;
      positions[i * 3 + 1] = field.heights[i];
      positions[i * 3 + 2] = z;
      uvs[i * 2] = x / TILE_METERS;
      uvs[i * 2 + 1] = z / TILE_METERS;

      if (field.isOnPad(x, z)) {
        colors[i * 3] = green.r;
        colors[i * 3 + 1] = green.g;
        colors[i * 3 + 2] = green.b;
        continue;
      }
      let shade = 0.82 + 0.22 * blotch(u, v) + 0.1 * fine(u, v);
      // 최근 크레이터 주변의 밝은 분출물 띠
      for (const c of field.craters) {
        const t = Math.hypot(x - c.x, z - c.z) / c.r;
        if (t > 0.85 && t < 1.9) shade += 0.12 * Math.exp(-(((t - 1.15) / 0.35) ** 2));
      }
      colors[i * 3] = colors[i * 3 + 1] = colors[i * 3 + 2] = shade;
    }
  }

  const index = new Uint32Array(n * n * 6);
  let k = 0;
  for (let iz = 0; iz < n; iz++) {
    for (let ix = 0; ix < n; ix++) {
      const a = iz * verts + ix;
      const b = a + 1;
      const c = a + verts;
      const d = c + 1;
      index[k++] = a;
      index[k++] = c;
      index[k++] = b;
      index[k++] = b;
      index[k++] = c;
      index[k++] = d;
    }
  }

  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geo.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
  geo.setIndex(new THREE.BufferAttribute(index, 1));
  geo.computeVertexNormals();

  const { map, normalMap } = getRegolithTextures(maxAnisotropy);
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      vertexColors: true,
      map,
      normalMap,
      normalScale: new THREE.Vector2(1.0, 1.0),
      roughness: 1,
      metalness: 0,
    }),
  );
  mesh.receiveShadow = true;
  mesh.castShadow = true;
  return mesh;
}

// 크기 0.1~0.5 m의 자갈을 흩뿌려 지면 가까이에서 거리감을 준다. 시각 전용
// (충돌 판정 없음)이므로 착륙 패드 위에는 놓지 않는다. 멀리 있는 자갈은 화면에서
// 1~2픽셀에 불과하므로, 지형을 구역으로 나눠 착륙선 주변 구역만 그린다.
const ROCK_COUNT = 7000;
const ROCK_CHUNKS = 10; // 한 변 구역 수 (구역 한 변 40 m)
const ROCK_VIEW_RADIUS = 90; // m, 이 거리 안의 구역만 표시

function buildRocks(field) {
  const rand = mulberry32(Math.floor(field.padHeight * 1000) + 3);
  const chunkSize = TERRAIN_SIZE / ROCK_CHUNKS;
  const buckets = Array.from({ length: ROCK_CHUNKS * ROCK_CHUNKS }, () => []);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Euler();
  const pos = new THREE.Vector3();
  const scale = new THREE.Vector3();
  let placed = 0;
  while (placed < ROCK_COUNT) {
    const x = (rand() - 0.5) * TERRAIN_SIZE * 0.96;
    const z = (rand() - 0.5) * TERRAIN_SIZE * 0.96;
    if (Math.hypot(x - PAD_CENTER.x, z - PAD_CENTER.z) < PAD_RADIUS + 1.5) continue;
    const size = 0.1 + 0.4 * Math.pow(rand(), 2.5);
    scale.set(size * (0.8 + 0.5 * rand()), size * (0.5 + 0.4 * rand()), size * (0.8 + 0.5 * rand()));
    pos.set(x, field.sample(x, z) - scale.y * 0.3, z);
    q.setFromEuler(e.set(rand() * 0.6, rand() * Math.PI * 2, rand() * 0.6));
    const cx = Math.min(ROCK_CHUNKS - 1, Math.floor((x + TERRAIN_SIZE / 2) / chunkSize));
    const cz = Math.min(ROCK_CHUNKS - 1, Math.floor((z + TERRAIN_SIZE / 2) / chunkSize));
    buckets[cz * ROCK_CHUNKS + cx].push(m.compose(pos, q, scale).clone());
    placed++;
  }

  const geometry = new THREE.IcosahedronGeometry(1, 0);
  const material = new THREE.MeshStandardMaterial({
    color: 0xaaa69c,
    roughness: 1,
    flatShading: true,
  });
  const group = new THREE.Group();
  const chunks = [];
  buckets.forEach((mats, i) => {
    if (mats.length === 0) return;
    const mesh = new THREE.InstancedMesh(geometry, material, mats.length);
    mats.forEach((mat, k) => mesh.setMatrixAt(k, mat));
    mesh.computeBoundingSphere();
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const center = new THREE.Vector3(
      ((i % ROCK_CHUNKS) + 0.5) * chunkSize - TERRAIN_SIZE / 2,
      0,
      (Math.floor(i / ROCK_CHUNKS) + 0.5) * chunkSize - TERRAIN_SIZE / 2,
    );
    chunks.push({ mesh, center });
    group.add(mesh);
  });

  // 구역 중심이 아니라 구역 사각형까지의 수평 거리로 판단 (가장자리 자갈 누락 방지)
  const reach = ROCK_VIEW_RADIUS + chunkSize * Math.SQRT1_2;
  return {
    object: group,
    update(landerPos) {
      for (const c of chunks) {
        c.mesh.visible =
          Math.hypot(c.center.x - landerPos.x, c.center.z - landerPos.z) < reach;
      }
    },
  };
}

// 비주기 값 노이즈, (u, v) ∈ [0,1]², 출력 -0.5..0.5
function valueNoise2D(rand, lattice) {
  const n = lattice + 1;
  const vals = new Float32Array(n * n);
  for (let i = 0; i < vals.length; i++) vals[i] = rand() - 0.5;
  return (u, v) => {
    const fx = Math.min(u, 0.999999) * lattice;
    const fy = Math.min(v, 0.999999) * lattice;
    const ix = Math.floor(fx);
    const iy = Math.floor(fy);
    const tx = fx - ix;
    const ty = fy - iy;
    const sx = tx * tx * (3 - 2 * tx);
    const sy = ty * ty * (3 - 2 * ty);
    return (
      vals[iy * n + ix] * (1 - sx) * (1 - sy) +
      vals[iy * n + ix + 1] * sx * (1 - sy) +
      vals[(iy + 1) * n + ix] * (1 - sx) * sy +
      vals[(iy + 1) * n + ix + 1] * sx * sy
    );
  };
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

  // 착륙 다리: 회색 지면과 대비되도록 금박 스트럿 + 밝은 은색 발판.
  // 약한 자체 발광을 줘서 그늘 속에서도 윤곽이 사라지지 않게 한다.
  const strutMat = new THREE.MeshStandardMaterial({
    color: 0xe0b23a,
    metalness: 0.55,
    roughness: 0.35,
    emissive: 0x2a1c00,
  });
  // 발판은 금속성 없이 밝은 흰색 (환경맵이 없어 금속 재질은 어둡게 보임)
  const footMat = new THREE.MeshStandardMaterial({
    color: 0xf6f6f0,
    metalness: 0,
    roughness: 0.45,
    emissive: 0x3a3a3a,
  });
  const addRod = (from, to, radius, mat) => {
    const dir = to.clone().sub(from);
    const rod = new THREE.Mesh(
      new THREE.CylinderGeometry(radius, radius, dir.length(), 8),
      mat,
    );
    rod.position.copy(from.clone().add(to).multiplyScalar(0.5));
    rod.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    group.add(rod);
  };
  for (const leg of LEG_OFFSETS) {
    const top = new THREE.Vector3(leg.x * 0.45, -0.7, leg.z * 0.45);
    const end = new THREE.Vector3(leg.x, leg.y, leg.z);
    addRod(top, end, 0.08, strutMat);
    // 보조 버팀대: 동체 하단에서 주 스트럿 아래쪽으로
    const brace = top.clone().lerp(end, 0.7);
    addRod(new THREE.Vector3(leg.x * 0.3, -1.0, leg.z * 0.3), brace, 0.045, strutMat);
    // 접시형 발판 (바닥면이 발끝 높이에 닿도록 배치)
    const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.3, 0.12, 16), footMat);
    foot.position.set(end.x, end.y + 0.06, end.z);
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

  // 화염·RCS(가산 블렌딩 MeshBasic)를 제외한 기체 부품만 그림자를 드리운다
  group.traverse((obj) => {
    if (obj.isMesh && !obj.material.isMeshBasicMaterial) obj.castShadow = true;
  });

  return { group, flame, rcs };
}
