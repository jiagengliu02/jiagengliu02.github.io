// Keep the static originals available and respect the visitor's motion preference.
(() => {
  const button = document.getElementById('animation-toggle');
  const images = document.querySelectorAll('img[data-animation]');
  if (!button || !images.length) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let paused = reducedMotion.matches;
  function render() {
    images.forEach((image) => {
      image.src = paused ? image.dataset.still : image.dataset.animation;
      // A deliberate Play click can override the OS preference for this page.
      const source = image.closest('picture').querySelector('source');
      source.media = paused ? '(prefers-reduced-motion: reduce)' : 'not all';
    });
    button.textContent = paused ? 'Play animations' : 'Pause animations';
  }
  button.hidden = false;
  button.addEventListener('click', () => { paused = !paused; render(); });
  reducedMotion.addEventListener('change', (event) => { paused = event.matches; render(); });
  render();
})();
