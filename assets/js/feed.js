(() => {
  const feed = document.querySelector('#episode-feed'), more = document.querySelector('.load-more');
  if (!feed || !more) return;
  const status = document.querySelector('#feed-status');
  let busy = false, observer;
  async function load(manual = false) {
    if (busy || !more.dataset.json) return;
    busy = true; more.setAttribute('aria-disabled', 'true'); status.textContent = 'Loading episodes…';
    try {
      const response = await fetch(more.dataset.json);
      if (!response.ok) throw new Error('Unavailable');
      const data = await response.json(), first = feed.children.length;
      feed.insertAdjacentHTML('beforeend', data.html);
      if (manual) {const link = feed.children[first].querySelector('a'); link.focus({preventScroll:true});}
      status.textContent = `${feed.children.length} episodes shown${data.next ? '.' : '. You’re all caught up.'}`;
      if (data.next) {more.href = data.next; more.dataset.json = data.json;}
      else {observer?.disconnect(); more.removeAttribute('data-json'); more.hidden = true;}
    } catch {status.textContent = 'Could not load episodes. Follow the next page link to continue.'; observer?.disconnect(); more.dataset.failed = 'true';}
    finally {busy = false; more.removeAttribute('aria-disabled');}
  }
  more.addEventListener('click', event => {if (!more.dataset.failed) {event.preventDefault(); load(true);}});
  // Keep footer reachable: at most one automatic batch per intentional scroll.
  if ('IntersectionObserver' in window && !navigator.connection?.saveData) {
    observer = new IntersectionObserver(entries => {if (entries.some(entry => entry.isIntersecting)) load();}, {rootMargin:'100px'});
    observer.observe(more);
  }
})();
