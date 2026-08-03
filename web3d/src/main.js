// 부트스트랩 + 메인 루프: 게임 로직(10ms 서브스텝) ↔ 렌더링(rAF) 연결

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

function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight, false);
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
    hud.setCameraMode(cameras.mainMode);
  }
  hud.showBanner(GameState.READY, game);
});

input.on("cycleCamera", () => {
  hud.setCameraMode(cameras.cycleMain());
});

hud.showBanner(GameState.READY, game);
hud.setCameraMode(cameras.mainMode);

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
