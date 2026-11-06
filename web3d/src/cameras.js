// FNAF(프레디의 피자가게) 스타일 멀티뷰. 모든 카메라는 착륙선 외부에 장착되어
// 기체와 함께 움직인다 (외부 추적 카메라 없음). 기본은 전 카메라를 그리드로
// 한 화면에 표시하고, 숫자키/클릭으로 특정 카메라만 크게 확대한다.
// 확대 중에도 나머지 카메라는 하단 썸네일로 계속 보인다.

import * as THREE from "../vendor/three.module.min.js";

const GAP = 10; // 타일 사이 베젤(px)
const MAX_THUMB_W = 240;
const HORIZON_TILT = (15 * Math.PI) / 180; // 측면 카메라 하향 각도

// 기체 좌표계 장착 위치와 바라보는 지점. 그리드 배치 순서(3열):
//   [1 LEFT ] [2 FORWARD] [3 RIGHT]
//   [4 LEG  ] [5 DOWN   ] [6 AFT  ]
// 기체 전방 = -Z, 상방 = +Y. 동체 반경 약 1.1 m.
function horizonMount(dirX, dirZ) {
  const pos = new THREE.Vector3(dirX * 1.15, 0.2, dirZ * 1.15);
  const target = pos
    .clone()
    .add(new THREE.Vector3(dirX, -Math.tan(HORIZON_TILT), dirZ));
  return { pos, target, up: new THREE.Vector3(0, 1, 0) };
}

const MOUNTS = [
  { key: "left", label: "CAM 1 · LEFT", fov: 65, ...horizonMount(-1, 0) },
  { key: "forward", label: "CAM 2 · FORWARD", fov: 65, ...horizonMount(0, -1) },
  { key: "right", label: "CAM 3 · RIGHT", fov: 65, ...horizonMount(1, 0) },
  {
    // 동체 옆 붐에서 착륙 다리 발판과 그 아래 지면을 내려다봄 — 접지 순간 확인용
    key: "leg",
    label: "CAM 4 · LEG",
    fov: 60,
    pos: new THREE.Vector3(0.95, 0.35, 0.95),
    target: new THREE.Vector3(2.0, -2.6, 2.0),
    up: new THREE.Vector3(0, 1, 0),
  },
  {
    // 엔진 벨 아래, 기체 바로 아래를 수직으로 내려다봄. 화면 위쪽 = 기체 전방
    key: "down",
    label: "CAM 5 · DOWN",
    fov: 70,
    pos: new THREE.Vector3(0, -1.55, 0),
    target: new THREE.Vector3(0, -10, 0),
    up: new THREE.Vector3(0, 0, -1),
    hideFlame: true,
  },
  { key: "aft", label: "CAM 6 · AFT", fov: 65, ...horizonMount(0, 1) },
];

export function createCameras() {
  const cams = MOUNTS.map((m) => {
    const cam = new THREE.PerspectiveCamera(m.fov, 1, 0.1, 1200);
    cam.position.copy(m.pos);
    // 카메라는 로컬 -Z를 바라보므로 Matrix4.lookAt(eye, target, up)으로 자세 설정
    const look = new THREE.Matrix4().lookAt(m.pos, m.target, m.up);
    cam.quaternion.setFromRotationMatrix(look);
    // 엔진 화염(레이어 1)은 하방 카메라 시야를 가리지 않도록 제외
    if (!m.hideFlame) cam.layers.enable(1);
    return { key: m.key, label: m.label, cam };
  });

  const cols = Math.ceil(Math.sqrt(cams.length));
  const rows = Math.ceil(cams.length / cols);
  let focusIndex = null; // null = 그리드(전체 보기)

  // CSS 좌표(좌상단 원점) 기준 각 카메라 영역 계산.
  // 렌더링과 DOM 프레임 오버레이가 같은 값을 공유한다.
  function layoutRects(w, h) {
    if (focusIndex === null) {
      const cw = (w - GAP * (cols + 1)) / cols;
      const ch = (h - GAP * (rows + 1)) / rows;
      return cams.map((_, i) => ({
        index: i,
        x: GAP + (i % cols) * (cw + GAP),
        y: GAP + Math.floor(i / cols) * (ch + GAP),
        w: cw,
        h: ch,
        focused: false,
      }));
    }
    const thumbs = cams.length - 1;
    const thumbW = Math.min(MAX_THUMB_W, (w - GAP * (thumbs + 1)) / thumbs);
    const thumbH = (thumbW * 2) / 3;
    const stripH = thumbH + GAP * 2;
    const rects = [
      {
        index: focusIndex,
        x: GAP,
        y: GAP,
        w: w - GAP * 2,
        h: h - stripH - GAP,
        focused: true,
      },
    ];
    let slot = 0;
    for (let i = 0; i < cams.length; i++) {
      if (i === focusIndex) continue;
      rects.push({
        index: i,
        x: GAP + slot * (thumbW + GAP),
        y: h - GAP - thumbH,
        w: thumbW,
        h: thumbH,
        focused: false,
      });
      slot += 1;
    }
    return rects;
  }

  return {
    count: cams.length,
    // 착륙선 모델(group)에 모든 카메라를 장착
    mountOn(group) {
      for (const c of cams) group.add(c.cam);
    },
    labelOf(i) {
      return cams[i].label;
    },
    keyOf(i) {
      return cams[i].key;
    },
    get focusIndex() {
      return focusIndex;
    },
    // 같은 카메라를 다시 선택하면 그리드로 복귀
    toggleFocus(i) {
      focusIndex = focusIndex === i ? null : i;
    },
    // 그리드 → 1 → 2 → … → 마지막 → 그리드 순환
    cycle() {
      focusIndex =
        focusIndex === null ? 0 : focusIndex + 1 >= cams.length ? null : focusIndex + 1;
    },
    layout(w, h) {
      return layoutRects(w, h).map((r) => ({
        ...r,
        label: cams[r.index].label,
        key: cams[r.index].key,
      }));
    },
    render(renderer, scene) {
      const canvas = renderer.domElement;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;

      // 타일 사이 베젤을 검게 비운다 (이전 프레임 잔상 제거)
      renderer.setScissorTest(true);
      renderer.setViewport(0, 0, w, h);
      renderer.setScissor(0, 0, w, h);
      renderer.setClearColor(0x000000, 1);
      renderer.clear();
      renderer.shadowMap.needsUpdate = true; // 첫 뷰 렌더 때 한 번 갱신되고 해제됨

      for (const r of layoutRects(w, h)) {
        const glY = h - r.y - r.h; // setViewport의 y는 아래에서 위로
        renderer.setViewport(r.x, glY, r.w, r.h);
        renderer.setScissor(r.x, glY, r.w, r.h);
        const cam = cams[r.index].cam;
        setAspect(cam, r.w / r.h);
        renderer.render(scene, cam);
      }

      renderer.setScissorTest(false);
    },
  };
}

function setAspect(cam, aspect) {
  if (cam.aspect !== aspect) {
    cam.aspect = aspect;
    cam.updateProjectionMatrix();
  }
}
