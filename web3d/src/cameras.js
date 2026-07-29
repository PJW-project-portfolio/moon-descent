// 카메라 4대 + setViewport/setScissor 멀티 뷰포트 렌더링.
// 메인 풀스크린(체이스 ↔ 패드 뷰 전환) + 하단 PIP 3개(하방/전방/패드 카메라).

import * as THREE from "../vendor/three.module.min.js";
import { PAD_CENTER } from "./constants.js";

const PIP_W = 240;
const PIP_H = 160;
const PIP_MARGIN = 12;

export function createCameras(field) {
  const chase = new THREE.PerspectiveCamera(60, 1, 0.1, 1200);
  const padView = new THREE.PerspectiveCamera(55, 1, 0.1, 1200);
  padView.position.set(PAD_CENTER.x, field.padHeight + 30, PAD_CENTER.z + 60);

  // 착륙선에 부착되는 카메라 — scene.js의 lander.group에 add해서 사용
  const downCam = new THREE.PerspectiveCamera(70, 1, 0.1, 1200);
  downCam.position.set(0, -1.55, 0); // 엔진 벨 아래 (기체 시야 가림 방지)
  downCam.rotation.set(-Math.PI / 2, 0, 0); // 기체 -Y 방향, 화면 위쪽 = 기체 전방

  const forwardCam = new THREE.PerspectiveCamera(65, 1, 0.1, 1200);
  forwardCam.position.set(0, 0.6, -1.2);
  forwardCam.rotation.set(0, 0, 0); // 기체 -Z 방향

  const padCam = new THREE.PerspectiveCamera(50, 1, 0.1, 1200);
  padCam.position.set(PAD_CENTER.x + 22, field.padHeight + 25, PAD_CENTER.z + 22);

  // 엔진 화염(레이어 1)은 하방 카메라를 제외한 모든 카메라에 보인다
  for (const cam of [chase, padView, forwardCam, padCam]) cam.layers.enable(1);

  let mainMode = "chase"; // "chase" | "pad"
  let chaseInitialized = false;

  return {
    downCam,
    forwardCam,
    cycleMain() {
      mainMode = mainMode === "chase" ? "pad" : "chase";
      return mainMode;
    },
    get mainMode() {
      return mainMode;
    },
    resetChase() {
      chaseInitialized = false;
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
      padView.lookAt(target);
      padCam.lookAt(target);
    },
    render(renderer, scene) {
      const canvas = renderer.domElement;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const main = mainMode === "chase" ? chase : padView;

      renderer.setScissorTest(true);

      renderer.setViewport(0, 0, w, h);
      renderer.setScissor(0, 0, w, h);
      setAspect(main, w / h);
      renderer.render(scene, main);

      const pips = [
        { cam: downCam, slot: 0 },
        { cam: forwardCam, slot: 1 },
        { cam: padCam, slot: 2 },
      ];
      for (const { cam, slot } of pips) {
        const x = PIP_MARGIN + slot * (PIP_W + PIP_MARGIN);
        const y = PIP_MARGIN; // setViewport의 y는 아래에서 위로
        renderer.setViewport(x, y, PIP_W, PIP_H);
        renderer.setScissor(x, y, PIP_W, PIP_H);
        setAspect(cam, PIP_W / PIP_H);
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

export const PIP_LAYOUT = { width: PIP_W, height: PIP_H, margin: PIP_MARGIN };
