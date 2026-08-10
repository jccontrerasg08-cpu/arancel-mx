(function () {
  "use strict";

  const maxTravel = 9;
  const eyeSelector = ".assistant-layer .comex-eye, .comex-bot .comex-eye";
  let pointer = null;
  let ticking = false;
  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function updateEyes() {
    ticking = false;
    const eyes = document.querySelectorAll(eyeSelector);
    eyes.forEach((eye) => {
      if (!pointer || reduceMotion) {
        eye.style.setProperty("--eye-x", "0px");
        eye.style.setProperty("--eye-y", "0px");
        return;
      }
      const rect = eye.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const dx = pointer.x - centerX;
      const dy = pointer.y - centerY;
      const distance = Math.max(Math.hypot(dx, dy), 1);
      const travel = clamp(distance / 18, 0, maxTravel);
      eye.style.setProperty("--eye-x", `${(dx / distance) * travel}px`);
      eye.style.setProperty("--eye-y", `${(dy / distance) * travel}px`);
    });
  }

  function requestUpdate() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(updateEyes);
    }
  }

  window.addEventListener("pointermove", (event) => {
    pointer = { x: event.clientX, y: event.clientY };
    requestUpdate();
  }, { passive: true });

  window.addEventListener("pointerleave", () => {
    pointer = null;
    requestUpdate();
  }, { passive: true });

  window.addEventListener("pointercancel", () => {
    pointer = null;
    requestUpdate();
  }, { passive: true });

  window.addEventListener("blur", () => {
    pointer = null;
    requestUpdate();
  });

  const observer = new MutationObserver(requestUpdate);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["class", "style"],
  });
  document.addEventListener("DOMContentLoaded", requestUpdate);
  window.addEventListener("load", requestUpdate);
})();
