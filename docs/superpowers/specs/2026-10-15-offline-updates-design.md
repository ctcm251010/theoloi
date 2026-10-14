# AudioTP — Offline downloads & startup updates

User scope: attachment18187dfa-1ac7-4425-9f88-e6f1f3567ef6/Pasted text.txt. Autonomous implementation, tests, build and release requested. Preserve original audio/catalog/state, private R2 and existing auth/signing identity; no bulk real downloads for testing.

## Design

Keep Tauri2, vanilla UI, shared Player and official updater plugin. Native Rust owns an app-local `offline-v1` directory, validated metadata, one download worker, SHA-256 verification, range resume and deletion. Webview only supplies known asset IDs and in-memory session to scoped commands; never arbitrary paths or R2 keys. Authenticated Worker `/v1/offline-manifest` projects current core catalog plus asset bytes/hash/contentType without objectKey/source URLs. Download uses existing scoped play tickets/media route. Offline entitlement persists with verified local files, no online token needed to read them; no immediate remote revocation while disconnected.

Native custom `offline` protocol serves only registered verified assets with GET/HEAD/Range for the existing audio element. Frontend defaults offline when all current core-manifest assets are valid; partial library defaults online when API works, falls back offline on real timeout/network failure. Manual offline filters every library/search/history/queue to downloaded IDs. Prayer remains online unless separately supported; never substitute another audio. Metadata snapshot in app data enables restart without login/network. Local file errors invalidate state, never silently play another track.

UI: gear Settings distinct from Filters; header Nghe offline/Nghe online; download/check/retry actions beside favourites. Download menu below filters: current mode or all core assets, count/bytes confirmation, queue progress pause/resume/cancel/retry. Hide global download when all manifest IDs valid; Trash only with completed files, selected/group/all deletion confirmations. App data independent of installer location/versions.

Updater: retain pinned HTTPS origin, official plugin and Minisign signed-version verification. Add modal, defer, progress and bounded background startup check without blocking offline. Private GitHub Releases cannot be checked anonymously; use existing controlled API metadata, preserving private media and authenticated installer downloads. Any public version metadata change must be minimal and explicitly documented; no GitHub PAT in client. Update preserves identifier/app data and auth storage. Older1.0.1+ updater must still consume existing route.

## Interfaces locked for parallel work

Manifest `{schemaVersion:1,revision:string,tracks:ClientTrack[],assets:[{assetId:string,bytes:number,sha256:string,contentType:string}]}`; core only, no keys/URLs/secrets. Revision is existing catalog revision. Validate unique membership exact tracks↔assets, positive bounds, SHA256hex. TEST may use test IDs/audio-wav only in acceptance build.

Native IPC:
- `offline_status()` → `{manifest:null|Manifest,completed:string[],items:[{assetId,status,bytes,error?}],job:{status,total,completed,failed,bytes,totalBytes},freeBytes:number}`. completed means current local file verified; metadata retained separately. Status may use verification fingerprints to avoid hashing2.5GB every poll; startup/full changes revalidate.
- `offline_sync({base,token})` → status; native fetches authenticated manifest, validates pinned production origin (test/local loopback only corresponding identifiers).
- `offline_start({base,token,ids})` → status; exact current IDs, preflight disk, skip verified, one worker. Tokens in RAM only.
- `offline_control({action:'pause'|'resume'|'cancel'|'retry',base?,token?})` → status; bounded retries, resume can refresh auth, retain completed/valid .part, no auto network on startup.
- `offline_remove({ids})` → status; only managed local files, reject unknown IDs, coordinate with active job; no remote DELETE.
- playback source `http://offline.localhost/<encodeURIComponent(assetId)>` on Windows through custom protocol, no general filesystem capability. GET/HEAD/Range; CORP/CORS only bundled origin.

Frontend `OfflineLibrary` wraps these commands with injectable bridge for fixture tests; browser lacks native support and must not pretend disk downloads are real. Integration modules must tolerate unavailable bridge. Updater agent owns app-updates module/native updater; UI agent consumes its result/progress contract, root coordinates.

## Acceptance

User attachment offline/updater matrix automated with small self-authored fixtures, browser GUI, native local mock where tool permits, production build/signature, installer upgrade-data preservation, secret/index audit and release evidence. Distinguish PASS/SKIP/pending user/clean-machine acceptance. No live mutation until concrete tested artifacts; no paid services or cert purchase. Do not claim a release/update works before actual URL/digest verification.
