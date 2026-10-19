// The map is a normal image and also works with JavaScript disabled.
(() => {
  const map = document.getElementById('visitor-map');
  const image = document.getElementById('visitor-map-image');
  const status = document.getElementById('visitor-map-status');
  const message = document.getElementById('visitor-map-message');
  const retry = document.getElementById('visitor-map-retry');
  if (!map || !image || !status || !message || !retry) return;
  const source = image.src;
  let timeout;

  function loaded() {
    clearTimeout(timeout);
    map.hidden = false;
    status.hidden = true;
  }

  function unavailable() {
    clearTimeout(timeout);
    map.hidden = true;
    status.hidden = false;
    message.textContent = 'The visitor map could not be loaded.';
    retry.hidden = false;
  }

  image.addEventListener('load', loaded);
  image.addEventListener('error', unavailable);
  retry.addEventListener('click', () => {
    retry.hidden = true;
    message.textContent = 'Loading visitor map…';
    timeout = setTimeout(unavailable, 15000);
    image.src = `${source}?reload=${Date.now()}`;
  });
  if (image.complete) {
    if (image.naturalWidth > 0) loaded();
    else unavailable();
  } else {
    timeout = setTimeout(unavailable, 15000);
  }
})();
