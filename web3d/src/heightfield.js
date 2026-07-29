// 지형 높이 그리드: 다중 옥타브 값 노이즈 + 패드 평탄화 + bilinear 샘플링.
// 물리 충돌과 렌더 메시가 같은 그리드를 공유하므로 시각과 판정이 항상 일치한다.

import {
  TERRAIN_SIZE,
  TERRAIN_SEGMENTS,
  PAD_CENTER,
  PAD_RADIUS,
  PAD_BLEND,
} from "./constants.js";
import { mulberry32 } from "./rng.js";

const OCTAVES = [
  { lattice: 8, amplitude: 6.0 },
  { lattice: 16, amplitude: 3.0 },
  { lattice: 32, amplitude: 1.5 },
];

function smoothstep(t) {
  return t * t * (3 - 2 * t);
}

// 격자 크기 n×n의 시드 랜덤 격자를 (u,v)∈[0,1]²에서 bilinear 보간
function latticeSampler(rand, n) {
  const values = new Float32Array((n + 1) * (n + 1));
  for (let i = 0; i < values.length; i++) values[i] = rand() * 2 - 1;
  return (u, v) => {
    const fx = Math.min(u, 0.999999) * n;
    const fy = Math.min(v, 0.999999) * n;
    const ix = Math.floor(fx);
    const iy = Math.floor(fy);
    const tx = smoothstep(fx - ix);
    const ty = smoothstep(fy - iy);
    const i00 = values[iy * (n + 1) + ix];
    const i10 = values[iy * (n + 1) + ix + 1];
    const i01 = values[(iy + 1) * (n + 1) + ix];
    const i11 = values[(iy + 1) * (n + 1) + ix + 1];
    return (
      i00 * (1 - tx) * (1 - ty) +
      i10 * tx * (1 - ty) +
      i01 * (1 - tx) * ty +
      i11 * tx * ty
    );
  };
}

export function createHeightfield(seed) {
  const rand = mulberry32(seed);
  const n = TERRAIN_SEGMENTS;
  const verts = n + 1;
  const heights = new Float32Array(verts * verts);
  const samplers = OCTAVES.map((o) => ({
    sample: latticeSampler(rand, o.lattice),
    amplitude: o.amplitude,
  }));

  for (let iz = 0; iz < verts; iz++) {
    for (let ix = 0; ix < verts; ix++) {
      const u = ix / n;
      const v = iz / n;
      let h = 0;
      for (const s of samplers) h += s.sample(u, v) * s.amplitude;
      heights[iz * verts + ix] = h;
    }
  }

  // 패드 평탄화: 패드 중심의 생성 높이를 기준으로 반경 내부는 평탄,
  // 블렌드 링에서는 smoothstep으로 주변 지형과 이어붙인다.
  const gridOf = (w) => ((w + TERRAIN_SIZE / 2) / TERRAIN_SIZE) * n;
  const rawSample = (x, z) => bilinear(heights, verts, gridOf(x), gridOf(z));
  const padHeight = rawSample(PAD_CENTER.x, PAD_CENTER.z);

  for (let iz = 0; iz < verts; iz++) {
    for (let ix = 0; ix < verts; ix++) {
      const wx = (ix / n) * TERRAIN_SIZE - TERRAIN_SIZE / 2;
      const wz = (iz / n) * TERRAIN_SIZE - TERRAIN_SIZE / 2;
      const d = Math.hypot(wx - PAD_CENTER.x, wz - PAD_CENTER.z);
      if (d <= PAD_RADIUS) {
        heights[iz * verts + ix] = padHeight;
      } else if (d <= PAD_RADIUS + PAD_BLEND) {
        const t = smoothstep((d - PAD_RADIUS) / PAD_BLEND);
        heights[iz * verts + ix] =
          padHeight * (1 - t) + heights[iz * verts + ix] * t;
      }
    }
  }

  return {
    heights,
    size: TERRAIN_SIZE,
    segments: n,
    padHeight,
    sample(x, z) {
      return bilinear(heights, verts, gridOf(x), gridOf(z));
    },
    isOnPad(x, z) {
      return Math.hypot(x - PAD_CENTER.x, z - PAD_CENTER.z) <= PAD_RADIUS;
    },
  };
}

function bilinear(heights, verts, gx, gz) {
  const cx = Math.min(Math.max(gx, 0), verts - 1);
  const cz = Math.min(Math.max(gz, 0), verts - 1);
  const ix = Math.min(Math.floor(cx), verts - 2);
  const iz = Math.min(Math.floor(cz), verts - 2);
  const tx = cx - ix;
  const tz = cz - iz;
  const h00 = heights[iz * verts + ix];
  const h10 = heights[iz * verts + ix + 1];
  const h01 = heights[(iz + 1) * verts + ix];
  const h11 = heights[(iz + 1) * verts + ix + 1];
  return (
    h00 * (1 - tx) * (1 - tz) +
    h10 * tx * (1 - tz) +
    h01 * (1 - tx) * tz +
    h11 * tx * tz
  );
}
