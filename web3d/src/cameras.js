// FNAF(프레디의 피자가게) 스타일 멀티뷰: 기본은 카메라 4대를 2×2 그리드로
// 한 화면에 모두 표시하고, 숫자키/클릭으로 특정 카메라만 크게 확대한다.
// 확대 중에도 나머지 카메라는 하단 썸네일로 계속 보인다.
// 매 프레임 setViewport/setScissor로 각 영역을 렌더링한다.

import * as THREE from "../vendor/three.module.min.js";
import { PAD_CENTER } from "./constants.js";

const GAP = 10; // 타일 사이 베젤(px)
const THUMB_W = 240;
const THUMB_H = 160;

export function createCameras(field) {
  const chase = new THREE.PerspectiveCamera(60, 1, 0.1, 1200);

  // 착륙선에 부착되는 카메라 — main.js에서 lander.group에 add해서 사용
  const downCam = new THREE.PerspectiveCamera(70, 1, 0.1, 1200);
  downCam.position.set(0, -1.55, 0); // 엔진 벨 아래 (기체 시야 가림 방지)
  downCam.rotation.set(-Math.PI / 2, 0, 0); // 기체 -Y 방향, 화면 위쪽 = 기체 전방

  const forwardCam = new THREE.PerspectiveCamera(65, 1, 0.1, 1200);
  forwardCam.position.set(0, 0.6, -1.2); // 기체 -Z 방향

  const padCam = new THREE.PerspectiveCamera(50, 1, 0.1, 1200);
  padCam.position.set(PAD_CENTER.x + 22, field.padHeight + 25, PAD_CENTER.z + 22);

  // 엔진 화염(레이어 1)은 하방 카메라를 제외한 모든 카메라에 보인다
  for (const cam of [chase, forwardCam, padCam]) cam.layers.enable(1);

  const cams = [
    { key: "chase", label: "CAM 1 · CHASE", cam: chase },
    { key: "down", label: "CAM 2 · DOWN", cam: downCam },
    { key: "forward", label: "CAM 3 · FORWARD", cam: forwardCam },
    { key: "pad", label: "CAM 4 · PAD", cam: padCam },
  ];

  let focusIndex = null; // null = 그리드(전체 보기)
  let chaseInitialized = false;

  // CSS 좌표(좌상단 원점) 기준 각 카메라 영역 계산.
  // 렌더링과 DOM 프레임 오버레이가 같은 값을 공유한다.
  function layoutRects(w, h) {
    if (focusIndex === null) {
      const cw = (w - GAP * 3) / 2;
      const ch = (h - GAP * 3) / 2;
      return cams.map((_, i) => ({
        index: i,
        x: GAP + (i % 2) * (cw + GAP),
        y: GAP + Math.floor(i / 2) * (ch + GAP),
        w: cw,
        h: ch,
        focused: false,
      }));
    }
    const stripH = THUMB_H + GAP * 2;
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
        x: GAP + slot * (THUMB_W + GAP),
        y: h - GAP - THUMB_H,
        w: THUMB_W,
        h: THUMB_H,
        focused: false,
      });
      slot += 1;
    }
    return rects;
  }

  return {
    downCam,
    forwardCam,
    count: cams.length,
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
    // 그리드 → 1 → 2 → 3 → 4 → 그리드 순환
    cycle() {
      focusIndex =
        focusIndex === null ? 0 : focusIndex + 1 >= cams.length ? null : focusIndex + 1;
    },
    resetChase() {
      chaseInitialized = false;
    },
    layout(w, h) {
      return layoutRects(w, h).map((r) => ({
        ...r,
        label: cams[r.index].label,
        key: cams[r.index].key,
      }));
    },
    update(landerPos, dt) {
      const target = new THREE.Vector3(landerPos.x, landerPos.y, landerPos.z);
      const desired = target.clone().add(new THREE.Vector3(0, 9, 24));
      if (!chaseInitialized) {
        chase.position.copy(desired);
        chaseInitialized = true;
      } else {
        chase.position.lerp(desired, 1 - Math.exp(-4 * dt));
      }
      chase.lookAt(target);
      padCam.lookAt(target);
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
