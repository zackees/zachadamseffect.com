(() => {
  const box = document.querySelector('[data-video]');
  if (!box) return;
  const shim = box.querySelector('.zl-shim');
  const status = document.querySelector('.player-status');
  let frame, ready = false, requested = false, failed = false, timer, handshake;
  const command = (func) => frame?.contentWindow?.postMessage(JSON.stringify({event:'command', func, args:[]}), 'https://www.youtube-nocookie.com');
  function reveal() {
    if (failed || ready) return;
    ready = true;
    frame.contentWindow?.postMessage(JSON.stringify({event:'command', func:'addEventListener', args:['onStateChange']}), 'https://www.youtube-nocookie.com');
    frame.contentWindow?.postMessage(JSON.stringify({event:'command', func:'addEventListener', args:['onError']}), 'https://www.youtube-nocookie.com');
    clearInterval(handshake);
    box.classList.add('ready');
    frame.tabIndex = 0;
    frame.removeAttribute('aria-hidden');
    if (document.activeElement === shim) frame.focus();
    shim.tabIndex = -1;
    shim.setAttribute('aria-hidden', 'true');
    if (requested) command('playVideo');
    status.textContent = '';
  }
  function youtubeLink() {
    status.textContent = 'Video could not start. Open YouTube in a new tab below.';
    shim.hidden = false; shim.target = '_blank'; shim.rel = 'noopener';
    shim.querySelector('.zl-play span').textContent = 'Open YouTube ↗';
  }
  function fallback() {
    if (failed) return;
    failed = true;
    clearTimeout(timer); clearInterval(handshake);
    frame?.remove();
    box.classList.remove('ready');
    shim.removeAttribute('aria-hidden'); shim.tabIndex = 0;
    if (box.dataset.mp4) {
      const video = document.createElement('video');
      video.controls = true; video.autoplay = requested; video.playsInline = true;
      video.src = box.dataset.mp4;
      box.append(video); shim.hidden = true;
      status.textContent = 'YouTube is unavailable. A local version is available in the player.';
      if (requested) video.focus();
      video.addEventListener('error', () => {video.remove(); youtubeLink();});
    } else {
      youtubeLink();
    }
  }
  function load(autoplay) {
    if (frame || failed) return;
    frame = document.createElement('iframe');
    frame.title = 'Latest Zach Adams Effect episode';
    frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    frame.allowFullscreen = true;
    frame.tabIndex = -1; frame.setAttribute('aria-hidden', 'true');
    frame.src = `https://www.youtube-nocookie.com/embed/${box.dataset.video}?enablejsapi=1&playsinline=1&autoplay=${autoplay ? 1 : 0}&origin=${encodeURIComponent(location.origin)}`;
    frame.addEventListener('load', () => {
      // A load event alone cannot prove a cross-origin player is usable.
      handshake = setInterval(() => frame.contentWindow?.postMessage(JSON.stringify({event:'listening', id:'hero'}), 'https://www.youtube-nocookie.com'), 250);
      setTimeout(() => clearInterval(handshake), 30000);
    });
    frame.addEventListener('error', fallback);
    box.append(frame);
  }
  function play() {
    load(true);
    if (ready) command('playVideo');
    clearTimeout(timer); timer = setTimeout(fallback, 8000);
  }
  addEventListener('message', event => {
    if (event.origin !== 'https://www.youtube-nocookie.com' || event.source !== frame?.contentWindow || failed) return;
    let data; try { data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data; } catch { return; }
    if (data.info?.videoData?.errorCode) {fallback(); return;}
    if (data.event === 'onReady' || (data.event === 'initialDelivery' && data.info)) reveal();
    if (data.event === 'onError') fallback();
    if (data.event === 'onStateChange' && data.info === 1) clearTimeout(timer);
    if (data.event === 'infoDelivery' && data.info?.playerState === 1) {clearTimeout(timer); status.textContent = '';}
  });
  shim.addEventListener('click', event => {
    if (failed) return;
    event.preventDefault(); requested = true;
    status.textContent = 'Loading video…';
    shim.querySelector('.zl-play span').textContent = 'Loading…';
    // Preserve the gesture's intent without starting third-party traffic before load.
    if (document.readyState === 'complete') play();
  });
  function preload() {
    if (requested) {play(); return;}
    if (navigator.connection?.saveData) return;
    const start = () => {
      if (frame || failed) return;
      const link = document.createElement('link'); link.rel = 'preconnect'; link.href = 'https://www.youtube-nocookie.com'; document.head.append(link);
      load(false);
    };
    if ('requestIdleCallback' in window) requestIdleCallback(start, {timeout:2000}); else setTimeout(start, 500);
  }
  if (document.readyState === 'complete') preload(); else addEventListener('load', preload, {once:true});
  // The booking bar must never compete with the episode's own controls on mobile.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(entries => {
      document.body.classList.toggle('hero-in-view', entries[0].isIntersecting);
    }, {rootMargin:'0px 0px 90px 0px'}).observe(box.closest('.zl'));
  }
  const toggle = document.querySelector('.disclosure'), snippet = document.querySelector('.snippet');
  const teaser = document.querySelector('.notes-teaser');
  toggle.hidden = false; teaser.hidden = false; snippet.classList.add('collapsed'); snippet.setAttribute('aria-hidden', 'true');
  addEventListener('resize', () => {if (toggle.getAttribute('aria-expanded') === 'true') snippet.style.maxHeight = `${snippet.scrollHeight}px`;});
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    if (!open && snippet.contains(document.activeElement)) toggle.focus();
    snippet.style.maxHeight = `${snippet.getBoundingClientRect().height}px`;
    snippet.classList.toggle('collapsed', !open);
    requestAnimationFrame(() => {snippet.style.maxHeight = open ? `${snippet.scrollHeight}px` : '4.8em';});
    snippet.setAttribute('aria-hidden', String(!open)); teaser.hidden = open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.textContent = open ? 'Hide episode notes ↑' : 'Show episode notes ↓';
  });
})();
