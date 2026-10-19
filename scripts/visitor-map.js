// Initialize in a visible, sized container; preserve the existing ClustrMaps ID.
(() => {
  const container = document.getElementById('visitor-map');
  const status = document.getElementById('visitor-map-status');
  const message = document.getElementById('visitor-map-message');
  const retry = document.getElementById('visitor-map-retry');
  if (!container || !status || !message || !retry) return;
  let observer;
  let timeout;
  let attempt = 0;
  let checkRendered = () => {};

  function loadMap() {
    const current = ++attempt;
    observer?.disconnect();
    clearTimeout(timeout);
    container.replaceChildren();
    status.hidden = false;
    retry.hidden = true;
    message.textContent = 'Loading visitor map…';

    function rendered() {
      const media = [...container.querySelectorAll('canvas, img, iframe, object, embed')];
      const visible = media.some(element => {
        const box = element.getBoundingClientRect();
        return box.width > 1 && box.height > 1 &&
          (element.tagName !== 'IMG' || element.complete && element.naturalWidth > 0);
      });
      if (current === attempt && visible) {
        clearTimeout(timeout);
        observer.disconnect();
        status.hidden = true;
      }
    }

    function unavailable() {
      if (current !== attempt || status.hidden) return;
      clearTimeout(timeout);
      message.textContent = 'The visitor map is temporarily unavailable or blocked by your browser.';
      retry.hidden = false;
    }

    observer = new MutationObserver(rendered);
    observer.observe(container, { childList: true, subtree: true, attributes: true });
    checkRendered = rendered;
    const script = document.createElement('script');
    script.id = 'clstr_globe';
    script.src = container.dataset.src;
    script.async = true;
    script.onerror = unavailable;
    script.onload = rendered;
    timeout = setTimeout(unavailable, 15000);
    container.append(script);
  }

  retry.addEventListener('click', loadMap);
  // Capture image/iframe load events, including those after the script loads.
  container.addEventListener('load', () => checkRendered(), true);
  requestAnimationFrame(loadMap);
})();
