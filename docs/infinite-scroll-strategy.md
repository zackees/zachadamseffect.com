# Episode discovery strategy

## Research

Google recommends crawlable, uniquely addressed component pages alongside incremental loading: crawlers do not click “load more.” See [pagination guidance](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading) and [lazy-loading guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading). [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) provides asynchronous viewport observation without scroll-handler polling. Infinite loading alone makes the footer difficult to reach, so this site keeps an explicit next-page link and limits automatic loading to observer entry transitions.

## Chosen approach

A single blended feed avoids four sparse tabs with the current six episodes. Build-time ranking uses four disjoint age bands: 0–30, 31–90, 91–365, and over 365 days. These represent last month, the remainder of this quarter, the remainder of this year, and the older archive. They are rolling windows, not calendar boundaries. Each round takes one entry from each nonempty band, redistributing empty quotas automatically. Disjoint membership guarantees deduplication and protects older discoveries from being crowded out by recent uploads.

Within each band, score = `log1p(views) + 2*log1p(likes) + 3/(1 + age_days/30)`. Logarithms dampen blockbusters; likes receive extra weight; recency decays continuously. Missing counts contribute zero rather than invented popularity. Ties resolve by publication date then episode number. Until counts are refreshed, the site effectively recommends recent conversations balanced with older ones. This is a transparent discovery heuristic, not a claim of editorial “best.”

Age is anchored to the newest episode's publication date so generated files remain reproducible between updates; windows advance when a new episode arrives. `python3 scripts/build_episodes.py --refresh-stats` fetches optional integer `views`/`likes` through `uvx yt-dlp`, without an API key or media download. Unavailable/private counts retain their previous value. A failed fetch reports the episode and continues. Refresh manually before regeneration; normal builds never require network access. YouTube can rate-limit or block metadata requests. Counts are optional; do not fabricate them.

## Delivery and accessibility

Three cards per page currently yield two meaningful pages. The same bounded chunks scale linearly to hundreds of episodes; increase `PAGE_SIZE` to 9–12 as the archive grows. The generator writes HTML pages at `/episodes/`, `/episodes/page/2/`, etc., with matching `/episodes/feed/N.json` fragments. Every page has its own canonical URL and real next/previous links. The homepage's previous-episode carousel links to this full archive and remains thumbnail-only.

JavaScript appends a page near the load-more link using IntersectionObserver. No observer or Save-Data means explicit loading only; no JavaScript means ordinary pagination. Fetch failure restores navigation through the original link. An in-flight lock prevents duplicate batches. Screen readers receive a polite count update; manual loading focuses the first new episode link. Automatic loading leaves focus alone. Links remain available for sharing/bookmarking each static page; the script deliberately does not mutate browser history while scrolling. Returning to a component URL displays that component directly. Cards reserve thumbnail space and no archive page creates an iframe.

## Player and media policy

Only the homepage hero embeds YouTube. Episode detail pages link from local thumbnails to YouTube. Hero preload begins after window load in an idle task and is skipped for Save-Data. The iframe uses the privacy-enhanced domain and its own message protocol, without downloading the separate iframe API script. A readiness message triggers the crossfade; an iframe load event alone cannot establish playback readiness ([iframe event limitations](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe#error_and_load_event_behavior)). User-requested playback times out after eight seconds unless playing is reported. The persistent new-tab link remains available, including for embedding-disabled videos.

An episode may optionally specify `mp4` as an HTTPS URL or same-origin absolute path. No media is uploaded by this change. If YouTube fails, that source is used in a native controlled video; otherwise the page explains the failure and offers YouTube in a new tab. Browser popup blocking is avoided by requiring the fallback link's explicit click.

Gestures before window load show a loading state and are queued until load; they create one iframe with autoplay enabled. A gesture during an existing preload uses the same iframe and sends `playVideo` on readiness, avoiding another navigation. The mobile booking bar hides while the episode card is visible so it cannot cover playback, subscription, or disclosure controls.
