// Describe ignored inputs for source-only typecheck. These declarations generate no
// JSON/runtime fallback: a production bundle still fails if prepare-worker was not run.
declare module '*generated/catalog.json' {
  const catalog: import('./contracts').ClientCatalog;
  export default catalog;
}
declare module '*generated/assets.json' {
  const assets: Record<string, import('./contracts').Asset>;
  export default assets;
}
declare module '*generated/quick-audio.json' {
  const quickAudio: import('./contracts').QuickAudio;
  export default quickAudio;
}
declare module '*generated/updates.json' {
  const updates: import('./contracts').UpdateRelease | null;
  export default updates;
}
