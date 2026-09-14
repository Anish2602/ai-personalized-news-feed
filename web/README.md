# AI News Feed — web

A small React reader for the [backend API](../README.md): create an account,
trigger ingestion, and get a live, personalized, explainable feed.

## Stack

Vite · React 19 · TypeScript · Tailwind CSS v4. No router, no state-management
library, no component kit — the app is small enough that a couple of hooks and
one context cover it (see [Design notes](#design-notes)).

## Local development

```bash
cp .env.example .env      # VITE_API_BASE_URL, defaults to localhost:8000
npm install
npm run dev                # http://localhost:3000
```

Requires the backend running (`docker compose up` from the repo root) and its
CORS origins to include `http://localhost:3000` (the default in the root
`.env.example`).

```bash
npm run build     # type-check + production build to dist/
npm run lint       # oxlint
npm run preview    # serve the production build locally
```

## Docker

Built and run as part of the main stack:

```bash
docker compose up --build   # from the repo root; serves on :3000 via nginx
```

`VITE_API_BASE_URL` is a **build-time** value (Vite bakes `import.meta.env.*`
into the static bundle) — override it with `--build-arg` if the API isn't at
`http://localhost:8000/api/v1`, not with a runtime environment variable.

## What it does

- **Onboarding** — `POST /users`, then every request after that carries the
  user's id (as the `X-User-Id` header for `/feed`, in the body for
  `/interactions`); persisted to `localStorage` so a refresh doesn't lose you.
- **Feed** — cursor-paginated cards (`GET /feed`) with topic pills, sources,
  relative time, and the ranking score. A **Debug** toggle reveals the
  per-feature score breakdown (`?debug=true`) as a "Why am I seeing this?"
  panel — semantic / freshness / popularity / source quality / diversity,
  straight from the backend's transparent ranking function.
- **Reactions** — Like / Dislike / Save / Skip call `POST /interactions`
  against the story's freshest member article; "Read full story" opens the
  source and fires a `CLICK`. These feed the backend's profile rebuild, so
  liking a few stories visibly changes the ranking on the next load.
- **Interests** — a small panel over `GET`/`POST /users/{id}/interests`.
- **Ingest news** — calls `POST /admin/ingest` with `run_sync: true` so the
  UI can show how many articles came in; processing (embed → dedup → classify
  → summarize) still happens in the background via Celery.

## Design notes

- **One context, two hooks.** `UserContext` owns the current user;
  `useFeed` owns pagination + optimistic reaction state for one feed screen.
  No Redux/Zustand/React Query — the data needs here are simple enough that
  they'd be pure overhead.
- **`primary_article_id` / `primary_article_url` on `FeedItem`.** The feed API
  is story-centric (aggregates duplicate articles), but interactions and
  "read the source" are article-level. Rather than have the UI fetch
  `GET /stories/{id}` for every card just to find an article to act on, the
  backend now includes the story's freshest member article directly on each
  feed item (see the backend README's recommendation section).
- **Manual refresh via remount, not a fetch method prop.** `<FeedList
  key={refreshToken} .../>` — bumping `refreshToken` after a fresh ingest
  remounts `FeedList` and its `useFeed` state cleanly, which is simpler here
  than threading an imperative refetch callback through props.
