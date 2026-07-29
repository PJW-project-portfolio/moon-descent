// 키 입력 추적: keydown/keyup으로 눌린 키 Set 유지 → 프레임별 스냅샷 제공

export function createInput() {
  const held = new Set();
  const listeners = { start: [], restart: [], toggleSas: [], cycleCamera: [] };
  let sas = true;

  window.addEventListener("keydown", (e) => {
    if (e.repeat) return;
    if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.code)) {
      e.preventDefault();
    }
    held.add(e.code);
    if (e.code === "Enter") listeners.start.forEach((f) => f());
    if (e.code === "KeyR") listeners.restart.forEach((f) => f());
    if (e.code === "KeyX") {
      sas = !sas;
      listeners.toggleSas.forEach((f) => f(sas));
    }
    if (e.code === "KeyC") listeners.cycleCamera.forEach((f) => f());
  });
  window.addEventListener("keyup", (e) => held.delete(e.code));
  window.addEventListener("blur", () => held.clear());

  return {
    on(event, fn) {
      listeners[event].push(fn);
    },
    get sas() {
      return sas;
    },
    snapshot() {
      const axis = (neg, pos) =>
        (held.has(pos) ? 1 : 0) - (held.has(neg) ? 1 : 0);
      return {
        pitch: axis("KeyW", "KeyS") || axis("ArrowUp", "ArrowDown"),
        roll: axis("KeyD", "KeyA") || axis("ArrowRight", "ArrowLeft"),
        yaw: axis("KeyE", "KeyQ"),
        mainEngine: held.has("Space"),
        sas,
      };
    },
  };
}
