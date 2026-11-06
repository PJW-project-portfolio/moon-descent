// 달 표토(레골리스) 질감: 실행 시점에 절차적으로 생성하는 반복 타일 텍스처.
// 알베도(색) 맵과 노멀(미세 요철) 맵 한 쌍을 만들며, 경계가 이어지도록
// 모든 노이즈와 스탬프를 주기적으로(래핑) 계산한다. 이미지 파일이 필요 없다.
// 요철은 범프맵이 아니라 노멀맵으로 준다: 범프맵은 화면 공간 미분을 쓰기 때문에
// 멀리 비스듬히 보이는 경사면에서 줄무늬가 생기지만, 노멀맵은 밉맵으로 고르게 흐려진다.

import * as THREE from "../vendor/three.module.min.js";
import { mulberry32 } from "./rng.js";

const SIZE = 512; // px, 한 타일
export const TILE_METERS = 12; // 타일 한 장이 덮는 지면 크기

let cached = null;

export function getRegolithTextures(maxAnisotropy = 1) {
  if (!cached) cached = buildTextures();
  cached.map.anisotropy = maxAnisotropy;
  cached.normalMap.anisotropy = maxAnisotropy;
  return cached;
}

function smooth(t) {
  return t * t * (3 - 2 * t);
}

// 주기 lattice × lattice 격자 값 노이즈 (타일 경계에서 이어짐), 출력 0..1
function periodicNoise(rand, lattice) {
  const v = new Float32Array(lattice * lattice);
  for (let i = 0; i < v.length; i++) v[i] = rand();
  return (x, y) => {
    const fx = (x / SIZE) * lattice;
    const fy = (y / SIZE) * lattice;
    const ix = Math.floor(fx);
    const iy = Math.floor(fy);
    const tx = smooth(fx - ix);
    const ty = smooth(fy - iy);
    const x0 = ((ix % lattice) + lattice) % lattice;
    const y0 = ((iy % lattice) + lattice) % lattice;
    const x1 = (x0 + 1) % lattice;
    const y1 = (y0 + 1) % lattice;
    const a = v[y0 * lattice + x0];
    const b = v[y0 * lattice + x1];
    const c = v[y1 * lattice + x0];
    const d = v[y1 * lattice + x1];
    return a * (1 - tx) * (1 - ty) + b * tx * (1 - ty) + c * (1 - tx) * ty + d * tx * ty;
  };
}

// 원형 스탬프를 타일 경계를 넘어 래핑해서 적용
function stamp(cx, cy, radius, fn) {
  const r = Math.ceil(radius);
  for (let dy = -r; dy <= r; dy++) {
    for (let dx = -r; dx <= r; dx++) {
      const t = Math.hypot(dx, dy) / radius;
      if (t > 1) continue;
      const px = (((Math.round(cx) + dx) % SIZE) + SIZE) % SIZE;
      const py = (((Math.round(cy) + dy) % SIZE) + SIZE) % SIZE;
      fn(py * SIZE + px, t);
    }
  }
}

function buildTextures() {
  const rand = mulberry32(0x4d4f4f4e);
  const height = new Float32Array(SIZE * SIZE);
  const albedo = new Float32Array(SIZE * SIZE);

  const relief = [
    [4, 1.0],
    [8, 0.55],
    [16, 0.3],
    [32, 0.18],
    [64, 0.1],
    [128, 0.06],
  ].map(([lattice, amp]) => ({ f: periodicNoise(rand, lattice), amp }));
  const tone = [
    [3, 0.16],
    [12, 0.1],
    [48, 0.08],
  ].map(([lattice, amp]) => ({ f: periodicNoise(rand, lattice), amp }));

  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const i = y * SIZE + x;
      let h = 0;
      for (const o of relief) h += o.f(x, y) * o.amp;
      height[i] = h;
      let a = 0.62;
      for (const o of tone) a += (o.f(x, y) - 0.5) * o.amp;
      albedo[i] = a;
    }
  }

  // 작은 충돌구: 오목한 바닥 + 밝은 테두리
  for (let k = 0; k < 55; k++) {
    const radius = 3 + 26 * Math.pow(rand(), 2.5);
    const cx = rand() * SIZE;
    const cy = rand() * SIZE;
    const depth = radius * 0.025;
    stamp(cx, cy, radius * 1.6, (i, t16) => {
      const t = t16 * 1.6;
      if (t < 1) {
        height[i] += depth * (t * t - 1) + depth * 0.3 * t ** 4;
        albedo[i] -= 0.015 * (1 - t);
      } else {
        const u = (t - 1) / 0.6;
        height[i] += depth * 0.3 * Math.exp(-u * u);
        albedo[i] += 0.025 * Math.exp(-u * u);
      }
    });
  }

  // 자갈: 작은 돔 + 밝거나 어두운 반점
  for (let k = 0; k < 2600; k++) {
    const radius = 0.8 + 2.4 * rand();
    const lift = 0.05 + 0.08 * rand();
    const shade = (rand() - 0.4) * 0.22;
    stamp(rand() * SIZE, rand() * SIZE, radius, (i, t) => {
      const dome = Math.sqrt(1 - t * t);
      height[i] += lift * dome;
      albedo[i] += shade * dome;
    });
  }

  // 높이 기울기 (중앙 차분, 래핑). 상위 1% 기울기가 약 45°가 되도록 세기를 정한다.
  const at = (x, y) => height[(((y + SIZE) % SIZE) * SIZE) + ((x + SIZE) % SIZE)];
  const gx = new Float32Array(SIZE * SIZE);
  const gy = new Float32Array(SIZE * SIZE);
  const mags = new Float32Array(SIZE * SIZE);
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const i = y * SIZE + x;
      gx[i] = (at(x + 1, y) - at(x - 1, y)) / 2;
      gy[i] = (at(x, y + 1) - at(x, y - 1)) / 2;
      mags[i] = Math.hypot(gx[i], gy[i]);
    }
  }
  const sorted = Float32Array.from(mags).sort();
  const strength = 1 / Math.max(sorted[Math.floor(sorted.length * 0.99)], 1e-6);

  const mapCanvas = document.createElement("canvas");
  const normalCanvas = document.createElement("canvas");
  mapCanvas.width = mapCanvas.height = normalCanvas.width = normalCanvas.height = SIZE;
  const mapCtx = mapCanvas.getContext("2d");
  const normalCtx = normalCanvas.getContext("2d");
  const mapImg = mapCtx.createImageData(SIZE, SIZE);
  const normalImg = normalCtx.createImageData(SIZE, SIZE);

  for (let i = 0; i < SIZE * SIZE; i++) {
    const grain = (rand() - 0.5) * 0.07;
    const a = Math.min(Math.max(albedo[i] + grain, 0), 1) * 255;
    // 약간 따뜻한 회색 (달 표토는 완전한 무채색보다 미세하게 갈색 기운)
    mapImg.data[i * 4] = Math.min(255, a * 1.02);
    mapImg.data[i * 4 + 1] = a;
    mapImg.data[i * 4 + 2] = a * 0.95;
    mapImg.data[i * 4 + 3] = 255;
    // 접선 공간 노멀 (-dh/du, -dh/dv, 1). 캔버스는 flipY로 올라가므로
    // 캔버스 y가 커질수록 v가 작아진다 → dh/dv = -gy.
    const nx = -gx[i] * strength;
    const ny = gy[i] * strength;
    const len = Math.hypot(nx, ny, 1);
    normalImg.data[i * 4] = ((nx / len) * 0.5 + 0.5) * 255;
    normalImg.data[i * 4 + 1] = ((ny / len) * 0.5 + 0.5) * 255;
    normalImg.data[i * 4 + 2] = ((1 / len) * 0.5 + 0.5) * 255;
    normalImg.data[i * 4 + 3] = 255;
  }
  mapCtx.putImageData(mapImg, 0, 0);
  normalCtx.putImageData(normalImg, 0, 0);

  const map = new THREE.CanvasTexture(mapCanvas);
  map.colorSpace = THREE.SRGBColorSpace;
  const normalMap = new THREE.CanvasTexture(normalCanvas);
  for (const t of [map, normalMap]) {
    t.wrapS = THREE.RepeatWrapping;
    t.wrapT = THREE.RepeatWrapping;
  }
  return { map, normalMap };
}
