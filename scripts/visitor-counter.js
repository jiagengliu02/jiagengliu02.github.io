// The counter is a normal image and also works with JavaScript disabled.
(() => {
  const counter = document.getElementById('visitor-counter');
  const image = document.getElementById('visitor-counter-image');
  const status = document.getElementById('visitor-counter-status');
  const message = document.getElementById('visitor-counter-message');
  const retry = document.getElementById('visitor-counter-retry');
  if (!counter || !image || !status || !message || !retry) return;
  const source = image.src;
  let timeout;

  function loaded() {
    clearTimeout(timeout);
    counter.hidden = false;
    status.hidden = true;
  }

  function unavailable() {
    clearTimeout(timeout);
    counter.hidden = true;
    status.hidden = false;
    message.textContent = 'The visitor counter could not be loaded.';
    retry.hidden = false;
  }

  image.addEventListener('load', loaded);
  image.addEventListener('error', unavailable);
  retry.addEventListener('click', () => {
    retry.hidden = true;
    message.textContent = 'Loading visitor counter…';
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
