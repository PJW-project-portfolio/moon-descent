// DOM 오버레이 HUD: 계기판(고도/속도/연료/기울기), 패드 방향 화살표, 상태 배너

import {
  SAFE_VSPEED,
  SAFE_HSPEED,
  SAFE_TILT_DEG,
  FUEL_CAPACITY,
  STARTING_LIVES,
} from "./constants.js";
import { tiltDeg } from "./physics.js";
import { GameState } from "./game.js";

export function createHud() {
  const el = (id) => document.getElementById(id);
  const refs = {
    alt: el("hud-alt"),
    vspd: el("hud-vspd"),
    hspd: el("hud-hspd"),
    fuelBar: el("hud-fuel-bar"),
    fuelText: el("hud-fuel-text"),
    lives: el("hud-lives"),
    tilt: el("hud-tilt"),
    sas: el("hud-sas"),
    engine: el("hud-engine"),
    padDist: el("hud-pad-dist"),
    padArrow: el("hud-pad-arrow"),
    banner: el("banner"),
    bannerTitle: el("banner-title"),
    bannerBody: el("banner-body"),
    camMode: el("hud-cam-mode"),
  };

  function colorClass(value, safe) {
    if (value <= safe * 0.7) return "ok";
    if (value <= safe) return "warn";
    return "danger";
  }

  function setStat(node, text, cls) {
    node.textContent = text;
    node.className = "value " + (cls || "");
  }

  return {
    update(game, inputs) {
      const s = game.lander;
      const alt = Math.max(0, game.altitudeAGL());
      const vDown = -s.vel.y;
      const hSpeed = Math.hypot(s.vel.x, s.vel.z);
      const tilt = tiltDeg(s.quat);
      const pad = game.padDistance();

      setStat(refs.alt, alt.toFixed(1) + " m");
      setStat(
        refs.vspd,
        (vDown >= 0 ? "-" : "+") + Math.abs(vDown).toFixed(1) + " m/s",
        colorClass(vDown, SAFE_VSPEED),
      );
      setStat(refs.hspd, hSpeed.toFixed(1) + " m/s", colorClass(hSpeed, SAFE_HSPEED));
      setStat(refs.tilt, tilt.toFixed(0) + "°", colorClass(tilt, SAFE_TILT_DEG));

      const fuelPct = (s.fuel / FUEL_CAPACITY) * 100;
      refs.fuelBar.style.width = fuelPct + "%";
      refs.fuelBar.className = fuelPct < 20 ? "bar danger" : "bar";
      refs.fuelText.textContent = s.fuel.toFixed(0);

      refs.lives.textContent =
        "♥".repeat(game.lives) + "♡".repeat(STARTING_LIVES - game.lives);

      refs.sas.textContent = inputs.sas ? "SAS ON" : "SAS OFF";
      refs.sas.className = "indicator " + (inputs.sas ? "on" : "off");
      refs.engine.textContent = s.mainOn ? "ENGINE" : "engine";
      refs.engine.className = "indicator " + (s.mainOn ? "burn" : "off");

      refs.padDist.textContent = pad.dist.toFixed(0) + " m";
      // 체이스 카메라는 -z를 바라보므로 화면 기준 방위각 = atan2(dx, -dz)
      const bearing = Math.atan2(pad.dx, -pad.dz);
      refs.padArrow.style.transform = `rotate(${bearing}rad)`;
    },
    setCameraMode(mode) {
      refs.camMode.textContent = mode === "chase" ? "CHASE CAM" : "PAD CAM";
    },
    showBanner(state, game) {
      refs.banner.classList.remove("hidden", "landed", "crashed", "emergency");
      if (state === GameState.READY) {
        refs.bannerTitle.textContent = "MOON DESCENT 3D";
        refs.bannerBody.innerHTML =
          "초록색 패드에 착륙하세요 — 패드 밖이라도 평탄한 곳이면 비상 착륙 가능<br>" +
          "W/S 피치 · A/D 롤 · Q/E 요 · Space 메인 엔진<br>" +
          "X SAS 토글 · C 카메라 전환 · R 재시작<br>" +
          `남은 기회 <strong>${game.lives}</strong><br><br>` +
          "<strong>Enter</strong> 를 눌러 시작";
      } else if (state === GameState.LANDED) {
        refs.banner.classList.add("landed");
        refs.bannerTitle.textContent = "착륙 성공!";
        refs.bannerBody.innerHTML =
          `점수 <strong>${game.score}</strong> · 남은 연료 ${game.lander.fuel.toFixed(0)}<br>` +
          "<strong>R</strong> 새 지형으로 새 게임";
      } else if (state === GameState.EMERGENCY_LANDED) {
        refs.banner.classList.add("emergency");
        refs.bannerTitle.textContent = "비상 착륙";
        refs.bannerBody.innerHTML =
          "패드 밖 평탄 지형에 착륙했습니다 (기본 점수만 지급)<br>" +
          `점수 <strong>${game.score}</strong><br>` +
          "<strong>R</strong> 새 지형으로 새 게임";
      } else if (state === GameState.CRASHED) {
        refs.banner.classList.add("crashed");
        refs.bannerTitle.textContent = "착륙 실패";
        refs.bannerBody.innerHTML =
          `${game.crashReason}<br>` +
          `남은 기회 <strong>${game.lives}</strong><br>` +
          "<strong>R</strong> 같은 지형에서 재도전";
      } else if (state === GameState.GAME_OVER) {
        refs.banner.classList.add("crashed");
        refs.bannerTitle.textContent = "임무 종료";
        refs.bannerBody.innerHTML =
          `${game.crashReason}<br>` +
          `최종 점수 <strong>${game.finalScore}</strong><br>` +
          "<strong>R</strong> 새 게임";
      }
    },
    hideBanner() {
      refs.banner.classList.add("hidden");
    },
  };
}
