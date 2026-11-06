import test from "node:test";
import assert from "node:assert/strict";
import { createHeightfield } from "../src/heightfield.js";
import {
  TERRAIN_SIZE,
  TERRAIN_SEGMENTS,
  PAD_CENTER,
  PAD_RADIUS,
} from "../src/constants.js";

test("그리드 정점에서의 샘플은 저장된 높이와 일치", () => {
  const f = createHeightfield(42);
  const verts = TERRAIN_SEGMENTS + 1;
  const cell = TERRAIN_SIZE / TERRAIN_SEGMENTS;
  for (const [ix, iz] of [[0, 0], [10, 20], [64, 64], [128, 128]]) {
    const x = ix * cell - TERRAIN_SIZE / 2;
    const z = iz * cell - TERRAIN_SIZE / 2;
    assert.ok(
      Math.abs(f.sample(x, z) - f.heights[iz * verts + ix]) < 1e-4,
      `vertex (${ix},${iz})`,
    );
  }
});

test("셀 중앙 샘플은 네 꼭짓점의 bilinear 평균", () => {
  const f = createHeightfield(7);
  const verts = TERRAIN_SEGMENTS + 1;
  const cell = TERRAIN_SIZE / TERRAIN_SEGMENTS;
  const ix = 30;
  const iz = 40;
  const x = (ix + 0.5) * cell - TERRAIN_SIZE / 2;
  const z = (iz + 0.5) * cell - TERRAIN_SIZE / 2;
  const avg =
    (f.heights[iz * verts + ix] +
      f.heights[iz * verts + ix + 1] +
      f.heights[(iz + 1) * verts + ix] +
      f.heights[(iz + 1) * verts + ix + 1]) /
    4;
  assert.ok(Math.abs(f.sample(x, z) - avg) < 1e-4);
});

test("패드 반경 내부는 어디서나 padHeight로 평탄", () => {
  const f = createHeightfield(123);
  for (let i = 0; i < 200; i++) {
    const angle = (i / 200) * Math.PI * 2;
    const r = (i % 10) / 10 * (PAD_RADIUS - 2.5); // 그리드 한 칸 여유
    const x = PAD_CENTER.x + Math.cos(angle) * r;
    const z = PAD_CENTER.z + Math.sin(angle) * r;
    assert.ok(
      Math.abs(f.sample(x, z) - f.padHeight) < 1e-3,
      `r=${r.toFixed(1)} angle=${angle.toFixed(2)}`,
    );
    assert.ok(f.isOnPad(x, z));
  }
});

test("경계 밖 샘플은 가장자리 값으로 클램프되고 유한", () => {
  const f = createHeightfield(9);
  for (const [x, z] of [[-1000, 0], [1000, 0], [0, -1000], [1000, 1000]]) {
    assert.ok(Number.isFinite(f.sample(x, z)));
  }
  const edge = TERRAIN_SIZE / 2;
  assert.equal(f.sample(edge + 500, 0), f.sample(edge, 0));
});

test("같은 시드는 같은 지형, 다른 시드는 다른 지형", () => {
  const a = createHeightfield(555);
  const b = createHeightfield(555);
  const c = createHeightfield(556);
  assert.deepEqual(Array.from(a.heights.slice(0, 50)), Array.from(b.heights.slice(0, 50)));
  assert.notDeepEqual(
    Array.from(a.heights.slice(0, 50)),
    Array.from(c.heights.slice(0, 50)),
  );
});

test("크레이터: 중심이 테두리보다 낮고 패드 영향권 밖에만 생성", () => {
  const f = createHeightfield(42);
  assert.ok(f.craters.length > 0);
  let checked = 0;
  for (const c of f.craters) {
    assert.ok(
      Math.hypot(c.x - PAD_CENTER.x, c.z - PAD_CENTER.z) > PAD_RADIUS,
      "크레이터가 패드와 겹침",
    );
    if (c.r < 8 || Math.abs(c.x) > 150 || Math.abs(c.z) > 150) continue;
    const center = f.sample(c.x, c.z);
    const rims = [0, 1, 2, 3].map((k) => {
      const a = (k * Math.PI) / 2;
      return f.sample(c.x + Math.cos(a) * c.r, c.z + Math.sin(a) * c.r);
    });
    const rimAvg = rims.reduce((s, h) => s + h, 0) / rims.length;
    assert.ok(center < rimAvg - c.r * 0.1, `r=${c.r.toFixed(1)} 중심 ${center.toFixed(2)} 테두리 ${rimAvg.toFixed(2)}`);
    checked++;
  }
  assert.ok(checked > 0, "검사할 큰 크레이터가 없음");
});
