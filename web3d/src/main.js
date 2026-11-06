// 부트스트랩 + 메인 루프: 게임 로직(10ms 서브스텝) ↔ 렌더링(rAF) 연결.
// 화면 구성은 FNAF 스타일 멀티뷰: 기본 2×2 그리드, 숫자키/클릭으로 확대.

import * as THREE from "../vendor/three.module.min.js";
import { MAX_FRAME_DT } from "./constants.js";
import { createGame, GameState } from "./game.js";
import { createScene } from "./scene.js";
import { createCameras } from "./cameras.js";
import { createInput } from "./input.js";
import { createHud } from "./hud.js";

function initialSeed() {
  const param = new URLSearchParams(location.search).get("seed");
  if (param !== null && Number.isFinite(Number(param))) return Number(param) >>> 0;
  return (Date.now() % 0xffffffff) >>> 0;
}

const canvas = document.getElementById("game-canvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

let game = createGame(initialSeed());
let view = createScene(game.field);
let cameras = createCameras(game.field);
// 하방/전방 카메라는 착륙선에 부착
view.lander.group.add(cameras.downCam);
view.lander.group.add(cameras.forwardCam);

const input = createInput();
const hud = createHud();

// 카메라 프레임 오버레이(라벨 + 테두리 + 하방캠 크로스헤어) 생성
const frameContainer = document.getElementById("cam-frames");
const frameEls = [];
for (let i = 0; i < cameras.count; i++) {
  const frame = document.createElement("div");
  frame.className = "pip-frame";
  const label = document.createElement("span");
  label.className = "pip-label";
  label.textContent = cameras.labelOf(i);
  frame.appendChild(label);
  if (cameras.keyOf(i) === "down") {
    const crosshair = document.createElement("span");
    crosshair.className = "crosshair";
    crosshair.textContent = "+";
    frame.appendChild(crosshair);
  }
  frameContainer.appendChild(frame);
  frameEls.push(frame);
}

function syncCamFrames() {
  const rects = cameras.layout(window.innerWidth, window.innerHeight);
  for (const r of rects) {
    const el = frameEls[r.index];
    el.style.left = r.x + "px";
    el.style.top = r.y + "px";
    el.style.width = r.w + "px";
    el.style.height = r.h + "px";
    el.classList.toggle("focused", r.focused);
  }
  hud.setCameraMode(
    cameras.focusIndex === null ? "GRID VIEW" : cameras.labelOf(cameras.focusIndex),
  );
}

function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  syncCamFrames();
}
window.addEventListener("resize", resize);
resize();

input.on("start", () => {
  if (game.state === GameState.READY) {
    game.start();
    hud.hideBanner();
  }
});

input.on("restart", () => {
  if (game.state === GameState.CRASHED) {
    // 목숨이 남아 있으면 같은 지형에서 재도전 (지형/장면 재사용)
    game.retry();
    view.setLanderVisible(true);
    cameras.resetChase();
  } else {
    // 새 게임: 새 지형이므로 장면과 카메라를 다시 구성
    const newSeed = (Math.random() * 0xffffffff) >>> 0;
    game.reset(newSeed);
    view = createScene(game.field);
    cameras = createCameras(game.field);
    view.lander.group.add(cameras.downCam);
    view.lander.group.add(cameras.forwardCam);
    syncCamFrames();
  }
  hud.showBanner(GameState.READY, game);
});

input.on("selectCam", (i) => {
  if (i < cameras.count) {
    cameras.toggleFocus(i);
    syncCamFrames();
  }
});

input.on("cycleCamera", () => {
  cameras.cycle();
  syncCamFrames();
});

// 카메라 타일 클릭: 그리드에서 클릭하면 확대, 확대된 타일을 다시 클릭하면 복귀
canvas.addEventListener("click", (e) => {
  const rects = cameras.layout(window.innerWidth, window.innerHeight);
  for (const r of rects) {
    if (
      e.clientX >= r.x &&
      e.clientX <= r.x + r.w &&
      e.clientY >= r.y &&
      e.clientY <= r.y + r.h
    ) {
      cameras.toggleFocus(r.index);
      syncCamFrames();
      return;
    }
  }
});

hud.showBanner(GameState.READY, game);
syncCamFrames();

let last = performance.now();
let bannerShownFor = GameState.READY;

function frame(now) {
  const dt = Math.min((now - last) / 1000, MAX_FRAME_DT);
  last = now;

  const snapshot = input.snapshot();
  if (game.state === GameState.FLYING) {
    game.update(dt, snapshot);
    if (
      game.state === GameState.CRASHED ||
      game.state === GameState.GAME_OVER
    ) {
      view.setLanderVisible(false);
      document.body.classList.add("crash-flash");
      setTimeout(() => document.body.classList.remove("crash-flash"), 600);
    }
  }

  if (game.state !== bannerShownFor) {
    bannerShownFor = game.state;
    if (game.state !== GameState.READY && game.state !== GameState.FLYING) {
      hud.showBanner(game.state, game);
    }
  }

  view.syncLander(game.lander);
  view.tick(dt);
  cameras.update(game.lander.pos, dt);
  cameras.render(renderer, view.scene);
  hud.update(game, snapshot);

  requestAnimationFrame(frame);
}

requestAnimationFrame(frame);
