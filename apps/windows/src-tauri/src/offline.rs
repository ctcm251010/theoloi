//! Scoped offline library. Authentication grants downloads; verified local bytes
//! remain playable without a session. No IPC accepts a path, object key or URL.
use crate::offline_fs::{Cache, IO_ERROR};
use serde::{Deserialize, Serialize};
use std::{
    collections::{HashMap, HashSet},
    fs::File,
    io::{Read, Seek, SeekFrom, Write},
    path::Path,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Condvar, Mutex,
    },
    time::{Duration, SystemTime},
};
use tauri::Manager as _;

const BAD_MANIFEST: &str = "Danh mục offline không hợp lệ.";
const NETWORK_ERROR: &str = "Không tải được bài. Kiểm tra kết nối hoặc đăng nhập lại rồi thử lại.";
const MAX_ASSET_BYTES: u64 = 1024 * 1024 * 1024;
const RESERVE_BYTES: u64 = 64 * 1024 * 1024;
const CHUNK_BYTES: u64 = 4 * 1024 * 1024;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Track {
    pub id: String,
    pub logical_id: String,
    pub mode: String,
    pub section: Option<String>,
    pub number: u32,
    pub title: String,
    pub category: String,
    pub duration_seconds: f64,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Asset {
    pub asset_id: String,
    pub bytes: u64,
    pub sha256: String,
    pub content_type: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Manifest {
    pub schema_version: u32,
    pub revision: String,
    pub tracks: Vec<Track>,
    pub assets: Vec<Asset>,
}
impl Manifest {
    fn validate(&self, allow_test: bool) -> Result<(), String> {
        if self.schema_version != 1
            || self.revision.trim().is_empty()
            || self.revision.len() > 256
            || self.tracks.is_empty()
            || self.tracks.len() > 10_000
            || self.assets.len() != self.tracks.len()
        {
            return Err(BAD_MANIFEST.into());
        }
        let mut ids = HashSet::new();
        for track in &self.tracks {
            if !valid_id(&track.id)
                || !valid_id(&track.logical_id)
                || !ids.insert(track.id.as_str())
                || !["guide", "instrumental", "silent"].contains(&track.mode.as_str())
                || (if track.mode == "silent" {
                    track.section.is_some()
                } else {
                    !matches!(track.section.as_deref(), Some("main" | "appendix"))
                })
                || track.number == 0
                || track.title.trim().is_empty()
                || track.title.len() > 1024
                || track.category.trim().is_empty()
                || track.category.len() > 256
                || !track.duration_seconds.is_finite()
                || track.duration_seconds <= 0.
                || track.duration_seconds > 86400.
            {
                return Err(BAD_MANIFEST.into());
            }
        }
        let mut assets = HashSet::new();
        for asset in &self.assets {
            if !ids.contains(asset.asset_id.as_str())
                || !assets.insert(asset.asset_id.as_str())
                || asset.bytes == 0
                || asset.bytes > MAX_ASSET_BYTES
                || asset.sha256.len() != 64
                || !asset
                    .sha256
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                || !(asset.content_type == "audio/mp4"
                    || (allow_test && asset.content_type == "audio/wav"))
            {
                return Err(BAD_MANIFEST.into());
            }
        }
        Ok(())
    }
}

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 256
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b":_-".contains(&b))
}
fn valid_base(base: &str, allow_test: bool) -> bool {
    if base == crate::update_policy::API_ORIGIN {
        return true;
    }
    allow_test
        && tauri::Url::parse(base).is_ok_and(|url| {
            url.scheme() == "http"
                && matches!(url.host_str(), Some("localhost" | "127.0.0.1"))
                && url.port().is_some()
                && url.username().is_empty()
                && url.password().is_none()
                && url.query().is_none()
                && url.fragment().is_none()
                && url.origin().ascii_serialization() == base
        })
}
fn range(value: &str, size: u64) -> Option<(u64, u64)> {
    if size == 0 {
        return None;
    }
    let (start, end) = value.strip_prefix("bytes=")?.split_once('-')?;
    if start.is_empty() {
        let suffix = end.parse::<u64>().ok()?;
        return (suffix > 0).then_some((size.saturating_sub(suffix), size - 1));
    }
    let start = start.parse::<u64>().ok()?;
    let end = if end.is_empty() {
        size - 1
    } else {
        end.parse::<u64>().ok()?.min(size - 1)
    };
    (start < size && end >= start).then_some((start, end))
}
fn content_range(value: &str, start: u64, end: u64, total: u64) -> bool {
    value == format!("bytes {start}-{end}/{total}")
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct QueueItem {
    asset_id: String,
    status: String,
    bytes: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    error: Option<String>,
    #[serde(default)]
    etag: Option<String>,
    #[serde(default)]
    attempts: u8,
}
#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct QueueDisk {
    revision: String,
    items: Vec<QueueItem>,
}
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ItemStatus {
    asset_id: String,
    status: String,
    bytes: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct JobStatus {
    status: String,
    total: usize,
    completed: usize,
    failed: usize,
    bytes: u64,
    total_bytes: u64,
}
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Status {
    manifest: Option<Manifest>,
    completed: Vec<String>,
    items: Vec<ItemStatus>,
    job: JobStatus,
    free_bytes: u64,
}
#[derive(Clone, PartialEq, Eq)]
struct Stamp {
    bytes: u64,
    modified: Option<SystemTime>,
    created: Option<SystemTime>,
}
fn stamp(file: &File) -> Result<Stamp, String> {
    let meta = file.metadata().map_err(|_| IO_ERROR)?;
    Ok(Stamp {
        bytes: meta.len(),
        modified: meta.modified().ok(),
        created: meta.created().ok(),
    })
}
#[derive(Clone)]
struct Session {
    base: String,
    token: String,
}
struct Inner {
    manifest: Option<Manifest>,
    completed: HashMap<String, Stamp>,
    items: Vec<QueueItem>,
    job: String,
    generation: u64,
    worker: bool,
    removing: bool,
    syncing: bool,
    session: Option<Session>,
}
struct OfflineManager {
    cache: Cache,
    inner: Mutex<Inner>,
    changed: Condvar,
    allow_test: bool,
    next_request: Mutex<std::time::Instant>,
}
impl OfflineManager {
    fn open(dir: &Path, allow_test: bool) -> Result<Arc<Self>, String> {
        let cache = Cache::open(dir)?;
        let manifest = cache.read_json::<Manifest>("manifest")?;
        if let Some(manifest) = &manifest {
            manifest.validate(allow_test)?;
        }
        let mut completed = HashMap::new();
        if let Some(manifest) = &manifest {
            for asset in &manifest.assets {
                if cache.verify(&asset.asset_id, asset.bytes, &asset.sha256)? {
                    let file = cache.open_read(&cache.name(&asset.asset_id, "audio"))?;
                    completed.insert(asset.asset_id.clone(), stamp(&file)?);
                }
            }
        }
        let mut items = Vec::new();
        if let (Some(manifest), Ok(Some(queue))) =
            (&manifest, cache.read_json::<QueueDisk>("queue"))
        {
            let mut seen = HashSet::new();
            if queue.revision == manifest.revision
                && queue.items.len() <= manifest.assets.len()
                && queue.items.iter().all(|item| {
                    seen.insert(item.asset_id.clone())
                        && manifest.assets.iter().any(|asset| {
                            asset.asset_id == item.asset_id && item.bytes <= asset.bytes
                        })
                        && item.attempts <= 3
                        && item.etag.as_ref().is_none_or(|v| valid_etag(v))
                        && [
                            "queued",
                            "downloading",
                            "paused",
                            "failed",
                            "completed",
                            "cancelled",
                        ]
                        .contains(&item.status.as_str())
                })
            {
                items = queue.items;
                for item in &mut items {
                    item.error = None;
                    if completed.contains_key(&item.asset_id) {
                        item.status = "completed".into();
                    } else if item.status == "completed" {
                        item.status = "failed".into();
                        item.bytes = 0;
                        item.error = Some("File offline thiếu hoặc đã hỏng.".into());
                    } else if !["failed", "cancelled"].contains(&item.status.as_str()) {
                        item.status = "paused".into();
                    }
                }
            }
        }
        let job = if items.iter().any(|i| i.status == "paused") {
            "paused"
        } else if items.iter().any(|i| i.status == "failed") {
            "failed"
        } else if items.iter().any(|i| i.status == "cancelled") {
            "cancelled"
        } else if items.is_empty() {
            "idle"
        } else {
            "completed"
        };
        Ok(Arc::new(Self {
            cache,
            inner: Mutex::new(Inner {
                manifest,
                completed,
                items,
                job: job.into(),
                generation: 0,
                worker: false,
                removing: false,
                syncing: false,
                session: None,
            }),
            changed: Condvar::new(),
            allow_test,
            next_request: Mutex::new(std::time::Instant::now()),
        }))
    }
    fn refresh(&self, inner: &mut Inner) -> Result<(), String> {
        let Some(manifest) = &inner.manifest else {
            return Ok(());
        };
        for asset in &manifest.assets {
            if let Some(previous) = inner.completed.get(&asset.asset_id) {
                let mut file = match self
                    .cache
                    .open_read(&self.cache.name(&asset.asset_id, "audio"))
                {
                    Ok(file) => file,
                    Err(_) => {
                        inner.completed.remove(&asset.asset_id);
                        continue;
                    }
                };
                let current = stamp(&file)?;
                if &current != previous {
                    if crate::offline_fs::verify_file(&mut file, asset.bytes, &asset.sha256)? {
                        inner.completed.insert(asset.asset_id.clone(), current);
                    } else {
                        inner.completed.remove(&asset.asset_id);
                    }
                }
            }
        }
        for item in &mut inner.items {
            if item.status == "completed" && !inner.completed.contains_key(&item.asset_id) {
                item.status = "failed".into();
                item.bytes = 0;
                item.error = Some("File offline thiếu hoặc đã hỏng. Hãy tải lại bài.".into());
            }
        }
        if !inner.worker
            && inner.job == "completed"
            && inner.items.iter().any(|i| i.status == "failed")
        {
            inner.job = "failed".into();
        }
        Ok(())
    }
    fn status(&self) -> Result<Status, String> {
        let mut inner = self.inner.lock().map_err(|_| IO_ERROR)?;
        self.refresh(&mut inner)?;
        let mut completed = inner.completed.keys().cloned().collect::<Vec<_>>();
        completed.sort();
        let assets = inner
            .manifest
            .as_ref()
            .map(|m| {
                m.assets
                    .iter()
                    .map(|a| (a.asset_id.as_str(), a.bytes))
                    .collect::<HashMap<_, _>>()
            })
            .unwrap_or_default();
        let job = JobStatus {
            status: inner.job.clone(),
            total: inner.items.len(),
            completed: inner
                .items
                .iter()
                .filter(|i| i.status == "completed")
                .count(),
            failed: inner.items.iter().filter(|i| i.status == "failed").count(),
            bytes: inner.items.iter().map(|i| i.bytes).sum(),
            total_bytes: inner
                .items
                .iter()
                .filter_map(|i| assets.get(i.asset_id.as_str()))
                .copied()
                .sum(),
        };
        Ok(Status {
            manifest: inner.manifest.clone(),
            completed,
            items: inner
                .items
                .iter()
                .map(|item| ItemStatus {
                    asset_id: item.asset_id.clone(),
                    status: item.status.clone(),
                    bytes: item.bytes,
                    error: item.error.clone(),
                })
                .collect(),
            job,
            free_bytes: self.cache.free_bytes()?,
        })
    }
    fn session(&self, base: String, token: String) -> Result<Session, String> {
        if !valid_base(&base, self.allow_test) || !crate::update_policy::valid_token(&token) {
            return Err("Địa chỉ hoặc phiên tải offline không hợp lệ.".into());
        }
        Ok(Session { base, token })
    }
    fn sync(&self, base: String, token: String) -> Result<Status, String> {
        let session = self.session(base, token)?;
        let generation = {
            let mut inner = self.inner.lock().map_err(|_| IO_ERROR)?;
            if inner.worker || inner.removing || inner.syncing {
                return Err("Hãy dừng tác vụ hiện tại trước khi cập nhật danh mục.".into());
            }
            inner.generation = inner.generation.wrapping_add(1);
            inner.syncing = true;
            inner.generation
        };
        let fetched = (|| {
            let client = http_client()?;
            let response = self
                .send_request(
                    generation,
                    session.base == crate::update_policy::API_ORIGIN,
                    || {
                        client
                            .get(format!("{}/v1/offline-manifest", session.base))
                            .bearer_auth(&session.token)
                    },
                )
                .map_err(|_| NETWORK_ERROR)?;
            let manifest: Manifest = read_json_response(response, 8 * 1024 * 1024)?;
            manifest.validate(self.allow_test)?;
            Ok::<_, String>(manifest)
        })();
        let mut inner = self.inner.lock().map_err(|_| IO_ERROR)?;
        if inner.generation != generation {
            return Err("Đã hủy cập nhật danh mục offline.".into());
        }
        inner.syncing = false;
        let manifest = fetched?;
        self.cache.write_json("manifest", &manifest)?;
        let previous = inner
            .manifest
            .as_ref()
            .map(|m| {
                m.assets
                    .iter()
                    .map(|a| (a.asset_id.clone(), a.clone()))
                    .collect::<HashMap<_, _>>()
            })
            .unwrap_or_default();
        inner.completed.retain(|id, _| {
            manifest
                .assets
                .iter()
                .any(|asset| &asset.asset_id == id && previous.get(id) == Some(asset))
        });
        if inner
            .manifest
            .as_ref()
            .is_none_or(|old| old.revision != manifest.revision || old.assets != manifest.assets)
        {
            inner.items.clear();
            inner.job = "idle".into();
        }
        inner.manifest = Some(manifest);
        self.persist(&inner)?;
        drop(inner);
        self.status()
    }
    fn start(
        self: &Arc<Self>,
        base: String,
        token: String,
        ids: Vec<String>,
    ) -> Result<Status, String> {
        let session = self.session(base, token)?;
        let mut inner = self.inner.lock().map_err(|_| IO_ERROR)?;
        if inner.worker || inner.removing || inner.syncing {
            return Err("Đang có một tác vụ offline. Hãy đợi tác vụ dừng.".into());
        }
        validate_ids(&inner, &ids)?;
        self.refresh(&mut inner)?;
        let manifest = inner.manifest.clone().ok_or(BAD_MANIFEST)?;
        let mut items = Vec::new();
        let mut required = 0u64;
        for id in ids {
            let asset = manifest
                .assets
                .iter()
                .find(|a| a.asset_id == id)
                .ok_or(BAD_MANIFEST)?;
            let done = inner.completed.contains_key(&id)
                && self.cache.verify(&id, asset.bytes, &asset.sha256)?;
            if !done {
                inner.completed.remove(&id);
            }
            let previous = inner.items.iter().find(|i| i.asset_id == id);
            let etag = previous.and_then(|i| i.etag.clone());
            let partial = if !done && etag.is_some() && self.cache.name(&id, "part").exists() {
                self.cache
                    .open_read(&self.cache.name(&id, "part"))?
                    .metadata()
                    .map_err(|_| IO_ERROR)?
                    .len()
                    .min(asset.bytes)
            } else {
                0
            };
            if !done {
                required = required
                    .checked_add(asset.bytes - partial)
                    .ok_or(BAD_MANIFEST)?;
            }
            items.push(QueueItem {
                asset_id: id,
                status: if done { "completed" } else { "queued" }.into(),
                bytes: if done { asset.bytes } else { partial },
                error: None,
                etag,
                attempts: 0,
            });
        }
        if required > 0 {
            disk_preflight(self.cache.free_bytes()?, required)?;
        }
        inner.items = items;
        inner.session = Some(session);
        inner.generation = inner.generation.wrapping_add(1);
        self.persist(&inner)?;
        self.launch(inner)?;
        self.status()
    }
    fn launch(self: &Arc<Self>, mut inner: std::sync::MutexGuard<'_, Inner>) -> Result<(), String> {
        if !inner.items.iter().any(|i| i.status == "queued") {
            inner.job = if inner.items.iter().any(|i| i.status == "failed") {
                "failed"
            } else {
                "completed"
            }
            .into();
            inner.session = None;
            return self.persist(&inner);
        }
        if inner.session.is_none() {
            return Err("Đăng nhập lại để tiếp tục tải. Các bài offline vẫn nghe được.".into());
        }
        inner.worker = true;
        inner.job = "running".into();
        let generation = inner.generation;
        let manager = self.clone();
        if std::thread::Builder::new()
            .name("audiotp-offline-download".into())
            .spawn(move || manager.worker(generation))
            .is_err()
        {
            inner.worker = false;
            inner.session = None;
            inner.job = "failed".into();
            return Err("Không khởi động được tác vụ tải offline.".into());
        }
        Ok(())
    }
    fn control(
        self: &Arc<Self>,
        action: &str,
        base: Option<String>,
        token: Option<String>,
    ) -> Result<Status, String> {
        if !["pause", "resume", "cancel", "retry"].contains(&action) {
            return Err("Thao tác offline không hợp lệ.".into());
        }
        let session = match (base, token) {
            (Some(base), Some(token)) => Some(self.session(base, token)?),
            (None, None) => None,
            _ => return Err("Cần cả địa chỉ và phiên đăng nhập để tiếp tục tải.".into()),
        };
        let mut inner = self.inner.lock().map_err(|_| IO_ERROR)?;
        if inner.removing {
            return Err("Đang xóa dữ liệu offline.".into());
        }
        match action {
            "cancel" => {
                inner.generation = inner.generation.wrapping_add(1);
                inner.syncing = false;
                inner.session = None;
                inner.job = "cancelled".into();
                for item in &mut inner.items {
                    if ["queued", "downloading", "paused"].contains(&item.status.as_str()) {
                        item.status = "cancelled".into();
                    }
                }
                self.persist(&inner)?;
                self.changed.notify_all();
                drop(inner);
            }
            "pause" => {
                if inner.worker {
                    inner.job = "paused".into();
                    for item in &mut inner.items {
                        if item.status == "downloading" {
                            item.status = "paused".into();
                        }
                    }
                    self.persist(&inner)?;
                }
                drop(inner);
            }
            _ => {
                if inner.syncing {
                    return Err("Đang cập nhật danh mục offline.".into());
                }
                if let Some(session) = session {
                    inner.session = Some(session);
                }
                if inner.session.is_none() {
                    return Err(
                        "Đăng nhập lại để tiếp tục tải. Các bài offline vẫn nghe được.".into(),
                    );
                }
                for item in &mut inner.items {
                    if item.status == "paused" || (action == "retry" && item.status == "failed") {
                        item.status = "queued".into();
                        item.error = None;
                        if action == "retry" {
                            item.attempts = 0;
                        }
                    }
                }
                if inner.worker {
                    inner.job = "running".into();
                    self.changed.notify_all();
                    drop(inner);
                } else {
                    inner.generation = inner.generation.wrapping_add(1);
                    self.persist(&inner)?;
                    self.launch(inner)?;
                }
            }
        }
        self.status()
    }
    fn remove(&self, ids: Vec<String>) -> Result<Status, String> {
        let mut inner = self.inner.lock().map_err(|_| IO_ERROR)?;
        validate_ids(&inner, &ids)?;
        if inner.removing {
            return Err("Đang xóa dữ liệu offline. Hãy đợi một chút.".into());
        }
        inner.removing = true;
        inner.generation = inner.generation.wrapping_add(1);
        inner.syncing = false;
        inner.session = None;
        inner.job = "cancelled".into();
        self.changed.notify_all();
        while inner.worker {
            let (guard, timeout) = self
                .changed
                .wait_timeout(inner, Duration::from_secs(50))
                .map_err(|_| IO_ERROR)?;
            inner = guard;
            if timeout.timed_out() && inner.worker {
                inner.removing = false;
                return Err("Tác vụ tải đang dừng. Hãy thử xóa lại sau một chút.".into());
            }
        }
        let result = (|| {
            for id in &ids {
                self.cache.remove(&self.cache.name(id, "audio"))?;
                self.cache.remove(&self.cache.name(id, "part"))?;
                inner.completed.remove(id);
            }
            inner.items.retain(|item| !ids.contains(&item.asset_id));
            self.persist(&inner)
        })();
        inner.removing = false;
        drop(inner);
        result?;
        self.status()
    }
    fn persist(&self, inner: &Inner) -> Result<(), String> {
        if let Some(manifest) = &inner.manifest {
            self.cache.write_json(
                "queue",
                &QueueDisk {
                    revision: manifest.revision.clone(),
                    items: inner.items.clone(),
                },
            )?;
        }
        Ok(())
    }
    fn worker(self: Arc<Self>, generation: u64) {
        loop {
            let next = (|| {
                let mut inner = self.inner.lock().ok()?;
                while inner.generation == generation && inner.job == "paused" {
                    inner = self.changed.wait(inner).ok()?;
                }
                if inner.generation != generation {
                    return None;
                }
                let index = inner.items.iter().position(|i| i.status == "queued")?;
                let asset = inner
                    .manifest
                    .as_ref()?
                    .assets
                    .iter()
                    .find(|a| a.asset_id == inner.items[index].asset_id)?
                    .clone();
                inner.items[index].status = "downloading".into();
                inner.items[index].attempts = inner.items[index].attempts.saturating_add(1);
                inner.items[index].error = None;
                let session = inner.session.clone()?;
                if self.persist(&inner).is_err() {
                    inner.items[index].status = "failed".into();
                    inner.items[index].error = Some(IO_ERROR.into());
                    return None;
                }
                Some((asset, session))
            })();
            let Some((asset, session)) = next else {
                break;
            };
            let result = self.download(generation, &asset, &session);
            let halt_network =
                matches!(&result,Err(DownloadError::Failed(error)) if *error==NETWORK_ERROR);
            if let Ok(mut inner) = self.inner.lock() {
                if inner.generation == generation {
                    let resumed = inner.job == "running";
                    if let Some(item) = inner
                        .items
                        .iter_mut()
                        .find(|i| i.asset_id == asset.asset_id)
                    {
                        match result {
                            Ok(()) => {
                                item.status = "completed".into();
                                item.bytes = asset.bytes;
                                item.error = None;
                            }
                            Err(DownloadError::Interrupted) => {
                                item.status = if resumed { "queued" } else { "paused" }.into();
                                item.attempts = item.attempts.saturating_sub(1);
                            }
                            Err(DownloadError::Failed(error)) => {
                                item.status = "failed".into();
                                item.error = Some(error.into());
                            }
                        }
                    }
                    if self.persist(&inner).is_err() {
                        inner.job = "failed".into();
                        break;
                    }
                    if halt_network {
                        for item in &mut inner.items {
                            if item.status == "queued" {
                                item.status = "paused".into();
                            }
                        }
                        inner.session = None;
                        break;
                    }
                }
            } else {
                break;
            }
        }
        if let Ok(mut inner) = self.inner.lock() {
            inner.worker = false;
            if inner.generation == generation {
                inner.job = if inner.items.iter().any(|i| i.status == "failed") {
                    "failed"
                } else if inner.items.iter().any(|i| i.status == "cancelled") {
                    "cancelled"
                } else {
                    "completed"
                }
                .into();
                inner.session = None;
            }
            let _ = self.persist(&inner);
            self.changed.notify_all();
        }
    }
    fn checkpoint(&self, generation: u64) -> Result<(), DownloadError> {
        let inner = self
            .inner
            .lock()
            .map_err(|_| DownloadError::Failed(IO_ERROR))?;
        if inner.generation != generation || inner.job == "paused" {
            return Err(DownloadError::Interrupted);
        }
        Ok(())
    }
    fn wait_request(&self, generation: u64, duration: Duration) -> Result<(), DownloadError> {
        let deadline = std::time::Instant::now() + duration;
        let mut inner = self
            .inner
            .lock()
            .map_err(|_| DownloadError::Failed(IO_ERROR))?;
        loop {
            if inner.generation != generation || inner.worker && inner.job == "paused" {
                return Err(DownloadError::Interrupted);
            }
            let remaining = deadline.saturating_duration_since(std::time::Instant::now());
            if remaining.is_zero() {
                return Ok(());
            }
            inner = self
                .changed
                .wait_timeout(inner, remaining.min(Duration::from_millis(250)))
                .map_err(|_| DownloadError::Failed(IO_ERROR))?
                .0;
        }
    }
    fn send_request(
        &self,
        generation: u64,
        pace: bool,
        mut request: impl FnMut() -> reqwest::blocking::RequestBuilder,
    ) -> Result<reqwest::blocking::Response, DownloadError> {
        for attempt in 0..3 {
            self.wait_request(generation, Duration::ZERO)?;
            if pace {
                let delay = {
                    let mut next = self
                        .next_request
                        .lock()
                        .map_err(|_| DownloadError::Failed(IO_ERROR))?;
                    let now = std::time::Instant::now();
                    let slot = (*next).max(now);
                    *next = slot + Duration::from_millis(500);
                    slot.saturating_duration_since(now)
                };
                self.wait_request(generation, delay)?;
            }
            let response = request()
                .send()
                .map_err(|_| DownloadError::Failed(NETWORK_ERROR))?;
            if response.status() != 429 || attempt == 2 {
                return if response.status().is_success() {
                    Ok(response)
                } else {
                    Err(DownloadError::Failed(NETWORK_ERROR))
                };
            }
            let seconds = response
                .headers()
                .get("Retry-After")
                .and_then(|v| v.to_str().ok())
                .and_then(|v| v.parse::<u64>().ok())
                .filter(|v| *v > 0)
                .unwrap_or(60);
            // A very long server delay pauses the job instead of retrying
            // earlier than requested or leaving a hidden worker waiting hours.
            if seconds > 300 {
                return Err(DownloadError::Failed(NETWORK_ERROR));
            }
            drop(response);
            self.wait_request(generation, Duration::from_secs(seconds))?;
        }
        Err(DownloadError::Failed(NETWORK_ERROR))
    }
    fn download(
        &self,
        generation: u64,
        asset: &Asset,
        session: &Session,
    ) -> Result<(), DownloadError> {
        use DownloadError::Failed as Failure;
        self.checkpoint(generation)?;
        let client = http_client().map_err(|_| Failure(NETWORK_ERROR))?;
        let pace = session.base == crate::update_policy::API_ORIGIN;
        let response = self.send_request(generation, pace, || {
            client
                .post(format!("{}/v1/play-tickets", session.base))
                .bearer_auth(&session.token)
                .json(&serde_json::json!({"assetId":asset.asset_id}))
        })?;
        let ticket: Ticket =
            read_json_response(response, 8192).map_err(|_| Failure(NETWORK_ERROR))?;
        let expected_path = format!("/v1/media/{}", encode(&asset.asset_id));
        if ticket.asset_id != asset.asset_id
            || ticket.path != expected_path
            || !crate::update_policy::valid_token(&ticket.ticket)
            || ticket.expires_at == 0
        {
            return Err(Failure(NETWORK_ERROR));
        }
        let media_url = format!(
            "{}{}?ticket={}",
            session.base,
            expected_path,
            encode(&ticket.ticket)
        );
        let path = self.cache.name(&asset.asset_id, "part");
        let mut file = self
            .cache
            .open_write(&path, true)
            .map_err(|_| Failure(IO_ERROR))?;
        let mut offset = file.metadata().map_err(|_| Failure(IO_ERROR))?.len();
        let mut etag = {
            let inner = self.inner.lock().map_err(|_| Failure(IO_ERROR))?;
            inner
                .items
                .iter()
                .find(|i| i.asset_id == asset.asset_id)
                .and_then(|i| i.etag.clone())
        };
        if offset > asset.bytes || etag.is_none() {
            file.set_len(0).map_err(|_| Failure(IO_ERROR))?;
            offset = 0;
            etag = None;
        }
        file.seek(SeekFrom::Start(offset))
            .map_err(|_| Failure(IO_ERROR))?;
        let mut representation_restarts = 0;
        let result = (|| {
            while offset < asset.bytes {
                self.checkpoint(generation)?;
                let end = (offset + CHUNK_BYTES - 1).min(asset.bytes - 1);
                disk_preflight(
                    self.cache.free_bytes().map_err(|_| Failure(IO_ERROR))?,
                    end - offset + 1,
                )
                .map_err(|_| Failure("Ổ đĩa không đủ dung lượng trống để tiếp tục tải."))?;
                let mut response = self.send_request(generation, pace, || {
                    let mut request = client
                        .get(&media_url)
                        .header("Range", format!("bytes={offset}-{end}"))
                        .header("Accept-Encoding", "identity");
                    if let Some(etag) = &etag {
                        request = request.header("If-Range", etag);
                    }
                    request
                })?;
                self.checkpoint(generation)?;
                let header =
                    |name: &str| response.headers().get(name).and_then(|v| v.to_str().ok());
                if header("content-type") != Some(asset.content_type.as_str())
                    || header("x-audiotp-asset-id") != Some(asset.asset_id.as_str())
                    || header("content-encoding").is_some_and(|v| v != "identity")
                {
                    return Err(Failure("Thông tin file tải về không khớp danh mục."));
                }
                let response_etag = header("etag")
                    .filter(|v| valid_etag(v))
                    .ok_or(Failure("Máy chủ không cung cấp phiên bản file an toàn."))?
                    .to_owned();
                let expected = match response.status().as_u16() {
                    206 => {
                        if !header("content-range")
                            .is_some_and(|v| content_range(v, offset, end, asset.bytes))
                        {
                            return Err(Failure(
                                "Phần tải tiếp không đúng vị trí hoặc kích thước file.",
                            ));
                        }
                        if offset > 0 && etag.as_ref() != Some(&response_etag) {
                            if representation_restarts >= 1 {
                                return Err(Failure("File nguồn thay đổi nhiều lần. Hãy làm mới danh mục rồi thử lại."));
                            }
                            representation_restarts += 1;
                            file.set_len(0).map_err(|_| Failure(IO_ERROR))?;
                            file.seek(SeekFrom::Start(0))
                                .map_err(|_| Failure(IO_ERROR))?;
                            offset = 0;
                            etag = None;
                            continue;
                        }
                        end - offset + 1
                    }
                    200 => {
                        file.set_len(0).map_err(|_| Failure(IO_ERROR))?;
                        file.seek(SeekFrom::Start(0))
                            .map_err(|_| Failure(IO_ERROR))?;
                        offset = 0;
                        asset.bytes
                    }
                    _ => return Err(Failure(NETWORK_ERROR)),
                };
                if response.content_length() != Some(expected) {
                    return Err(Failure("Kích thước phần tải về không hợp lệ."));
                }
                etag = Some(response_etag);
                {
                    let mut inner = self.inner.lock().map_err(|_| Failure(IO_ERROR))?;
                    if inner.generation != generation {
                        return Err(DownloadError::Interrupted);
                    }
                    if let Some(item) = inner
                        .items
                        .iter_mut()
                        .find(|i| i.asset_id == asset.asset_id)
                    {
                        item.etag = etag.clone();
                        item.bytes = offset;
                    }
                    self.persist(&inner).map_err(|_| Failure(IO_ERROR))?;
                }
                let mut received = 0u64;
                let mut buffer = [0; 64 * 1024];
                loop {
                    self.checkpoint(generation)?;
                    let count = response
                        .read(&mut buffer)
                        .map_err(|_| Failure(NETWORK_ERROR))?;
                    if count == 0 {
                        break;
                    }
                    self.checkpoint(generation)?;
                    if received + count as u64 > expected {
                        return Err(Failure("Máy chủ trả về quá nhiều dữ liệu."));
                    }
                    file.write_all(&buffer[..count])
                        .map_err(|_| Failure("Không ghi được file. Kiểm tra dung lượng ổ đĩa."))?;
                    received += count as u64;
                    offset += count as u64;
                    let mut inner = self.inner.lock().map_err(|_| Failure(IO_ERROR))?;
                    if inner.generation != generation {
                        return Err(DownloadError::Interrupted);
                    }
                    if let Some(item) = inner
                        .items
                        .iter_mut()
                        .find(|i| i.asset_id == asset.asset_id)
                    {
                        item.bytes = offset;
                        item.status = "downloading".into();
                    }
                }
                file.sync_all().map_err(|_| Failure(IO_ERROR))?;
                if received != expected {
                    return Err(Failure(NETWORK_ERROR));
                }
                let inner = self.inner.lock().map_err(|_| Failure(IO_ERROR))?;
                self.persist(&inner).map_err(|_| Failure(IO_ERROR))?;
            }
            self.checkpoint(generation)?;
            file.sync_all().map_err(|_| Failure(IO_ERROR))?;
            if !crate::offline_fs::verify_file(&mut file, asset.bytes, &asset.sha256)
                .map_err(|_| Failure(IO_ERROR))?
            {
                file.set_len(0).map_err(|_| Failure(IO_ERROR))?;
                let mut inner = self.inner.lock().map_err(|_| Failure(IO_ERROR))?;
                if let Some(item) = inner
                    .items
                    .iter_mut()
                    .find(|i| i.asset_id == asset.asset_id)
                {
                    item.bytes = 0;
                    item.etag = None;
                }
                return Err(Failure(
                    "SHA-256 không khớp. File chưa được lưu offline; hãy tải lại.",
                ));
            }
            Ok(())
        })();
        if result.is_err() {
            let _ = file.sync_all();
            return result;
        }
        drop(file);
        let mut inner = self.inner.lock().map_err(|_| Failure(IO_ERROR))?;
        if inner.generation != generation || inner.job == "paused" {
            return Err(DownloadError::Interrupted);
        }
        self.cache
            .promote(&asset.asset_id)
            .map_err(|_| Failure(IO_ERROR))?;
        // Re-open without following reparses and verify the actual committed file.
        // Rename is not permission to trust a path in a writable user directory.
        let mut file = self
            .cache
            .open_read(&self.cache.name(&asset.asset_id, "audio"))
            .map_err(|_| Failure(IO_ERROR))?;
        if !crate::offline_fs::verify_file(&mut file, asset.bytes, &asset.sha256)
            .map_err(|_| Failure(IO_ERROR))?
        {
            return Err(Failure("File offline không vượt qua xác minh SHA-256."));
        }
        inner.completed.insert(
            asset.asset_id.clone(),
            stamp(&file).map_err(|_| Failure(IO_ERROR))?,
        );
        Ok(())
    }
}
fn disk_preflight(available: u64, required: u64) -> Result<(), String> {
    if required
        .checked_add(RESERVE_BYTES)
        .is_none_or(|required| required > available)
    {
        Err("Ổ đĩa không đủ dung lượng trống để tải các bài đã chọn.".into())
    } else {
        Ok(())
    }
}
fn valid_etag(etag: &str) -> bool {
    etag.len() >= 2
        && etag.len() <= 256
        && etag.starts_with('"')
        && etag.ends_with('"')
        && etag.bytes().all(|b| b >= 32 && b < 127)
}
fn validate_ids(inner: &Inner, ids: &[String]) -> Result<(), String> {
    let manifest = inner
        .manifest
        .as_ref()
        .ok_or("Cần cập nhật danh mục offline trước khi tải.")?;
    let mut seen = HashSet::new();
    if ids.is_empty()
        || ids.len() > manifest.assets.len()
        || ids.iter().any(|id| {
            !seen.insert(id) || !manifest.assets.iter().any(|asset| &asset.asset_id == id)
        })
    {
        return Err("Danh sách bài offline không hợp lệ.".into());
    }
    Ok(())
}
enum DownloadError {
    Interrupted,
    Failed(&'static str),
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Ticket {
    asset_id: String,
    path: String,
    ticket: String,
    expires_at: u64,
}
fn encode(value: &str) -> String {
    let mut encoded = String::new();
    for byte in value.bytes() {
        if byte.is_ascii_alphanumeric() || b"-_.~".contains(&byte) {
            encoded.push(byte as char);
        } else {
            encoded.push_str(&format!("%{byte:02X}"));
        }
    }
    encoded
}
fn http_client() -> Result<reqwest::blocking::Client, String> {
    let _ = rustls::crypto::ring::default_provider().install_default();
    reqwest::blocking::Client::builder()
        .connect_timeout(Duration::from_secs(10))
        .timeout(Duration::from_secs(45))
        .redirect(reqwest::redirect::Policy::none())
        .no_proxy()
        .build()
        .map_err(|_| NETWORK_ERROR.into())
}
fn read_json_response<T: serde::de::DeserializeOwned>(
    response: reqwest::blocking::Response,
    limit: u64,
) -> Result<T, String> {
    if response.status() != 200 || response.content_length().is_some_and(|n| n > limit) {
        return Err(NETWORK_ERROR.into());
    }
    let mut bytes = Vec::new();
    response
        .take(limit + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| NETWORK_ERROR)?;
    if bytes.len() as u64 > limit {
        return Err(NETWORK_ERROR.into());
    }
    serde_json::from_slice(&bytes).map_err(|_| NETWORK_ERROR.into())
}

#[derive(Clone, Default)]
pub struct OfflineState(Arc<RuntimeState>);
#[derive(Default)]
struct RuntimeState {
    started: AtomicBool,
    manager: Mutex<Option<Result<Arc<OfflineManager>, String>>>,
    protocol_active: std::sync::atomic::AtomicUsize,
}
impl OfflineState {
    fn manager(&self) -> Result<Option<Arc<OfflineManager>>, String> {
        self.0
            .manager
            .lock()
            .map_err(|_| IO_ERROR)?
            .clone()
            .transpose()
    }
    fn status(&self) -> Result<Status, String> {
        if let Some(manager) = self.manager()? {
            return manager.status();
        }
        Ok(Status {
            manifest: None,
            completed: Vec::new(),
            items: Vec::new(),
            job: JobStatus {
                status: "verifying".into(),
                total: 0,
                completed: 0,
                failed: 0,
                bytes: 0,
                total_bytes: 0,
            },
            free_bytes: 0,
        })
    }
}
/// Startup disk verification has no HTTP/login dependency and never blocks WebView creation.
pub fn initialize(app: &tauri::AppHandle) {
    let state = app.state::<OfflineState>().inner().clone();
    if state.0.started.swap(true, Ordering::AcqRel) {
        return;
    }
    let app = app.clone();
    let thread_state = state.clone();
    if std::thread::Builder::new()
        .name("audiotp-offline-verify".into())
        .spawn(move || {
            let result = app
                .path()
                .app_local_data_dir()
                .map_err(|_| IO_ERROR.to_string())
                .and_then(|dir| {
                    OfflineManager::open(&dir, local_identifier(&app.config().identifier))
                });
            if let Ok(mut slot) = thread_state.0.manager.lock() {
                *slot = Some(result);
            }
        })
        .is_err()
    {
        if let Ok(mut slot) = state.0.manager.lock() {
            *slot = Some(Err("Không khởi động được xác minh offline.".into()));
        }
    }
}
fn local_identifier(identifier: &str) -> bool {
    matches!(identifier, "org.audiotp.acceptance" | "org.audiotp.local")
}
fn trusted_window(window: &tauri::WebviewWindow) -> Result<(), String> {
    let url = window.url().map_err(|_| IO_ERROR)?;
    if window.label() != "main" || !crate::internal_navigation(&url) {
        return Err("Chỉ cửa sổ AudioTP được truy cập thư viện offline.".into());
    }
    Ok(())
}
async fn disk_task<T: Send + 'static>(
    work: impl FnOnce() -> Result<T, String> + Send + 'static,
) -> Result<T, String> {
    tauri::async_runtime::spawn_blocking(work)
        .await
        .map_err(|_| IO_ERROR.to_string())?
}

#[tauri::command]
pub async fn offline_status(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OfflineState>,
) -> Result<Status, String> {
    trusted_window(&window)?;
    initialize(&app);
    let state = state.inner().clone();
    disk_task(move || state.status()).await
}
#[tauri::command]
pub async fn offline_sync(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OfflineState>,
    base: String,
    token: String,
) -> Result<Status, String> {
    trusted_window(&window)?;
    initialize(&app);
    let state = state.inner().clone();
    disk_task(move || {
        state
            .manager()?
            .ok_or("Đang xác minh thư viện offline. Hãy đợi một chút.".to_string())?
            .sync(base, token)
    })
    .await
}
#[tauri::command]
pub async fn offline_start(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OfflineState>,
    base: String,
    token: String,
    ids: Vec<String>,
) -> Result<Status, String> {
    trusted_window(&window)?;
    initialize(&app);
    let state = state.inner().clone();
    disk_task(move || {
        state
            .manager()?
            .ok_or("Đang xác minh thư viện offline. Hãy đợi một chút.".to_string())?
            .start(base, token, ids)
    })
    .await
}
#[tauri::command]
pub async fn offline_control(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OfflineState>,
    action: String,
    base: Option<String>,
    token: Option<String>,
) -> Result<Status, String> {
    trusted_window(&window)?;
    initialize(&app);
    let state = state.inner().clone();
    disk_task(move || match state.manager()? {
        Some(manager) => manager.control(&action, base, token),
        None if action == "cancel" => state.status(),
        None => Err("Đang xác minh thư viện offline. Hãy đợi một chút.".into()),
    })
    .await
}
#[tauri::command]
pub async fn offline_remove(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OfflineState>,
    ids: Vec<String>,
) -> Result<Status, String> {
    trusted_window(&window)?;
    initialize(&app);
    let state = state.inner().clone();
    disk_task(move || {
        state
            .manager()?
            .ok_or("Đang xác minh thư viện offline. Hãy đợi một chút.".to_string())?
            .remove(ids)
    })
    .await
}

pub fn register(builder: tauri::Builder<tauri::Wry>) -> tauri::Builder<tauri::Wry> {
    builder
        .manage(OfflineState::default())
        .register_asynchronous_uri_scheme_protocol("offline", |context, request, responder| {
            let app = context.app_handle().clone();
            let label = context.webview_label().to_owned();
            let state = app.state::<OfflineState>().inner().clone();
            if state.0.protocol_active.fetch_add(1, Ordering::AcqRel) >= 4 {
                state.0.protocol_active.fetch_sub(1, Ordering::AcqRel);
                responder.respond(response(503, None, None));
                return;
            }
            let thread_state = state.clone();
            // Protocol hashing/reads are isolated from WebView's event loop and bounded
            // to four requests and at most4MiB per Range response.
            std::thread::spawn(move || {
                let trusted = label == "main"
                    && app
                        .get_webview_window("main")
                        .is_some_and(|window| trusted_window(&window).is_ok());
                let result = if !trusted {
                    response(403, None, None)
                } else {
                    match thread_state.manager() {
                        Ok(Some(manager)) => manager.serve(request),
                        Ok(None) => response(503, None, None),
                        Err(_) => response(500, None, None),
                    }
                };
                responder.respond(result);
                thread_state
                    .0
                    .protocol_active
                    .fetch_sub(1, Ordering::AcqRel);
            });
        })
}
type HttpResponse = tauri::http::Response<Vec<u8>>;
fn response(status: u16, origin: Option<&str>, length: Option<u64>) -> HttpResponse {
    let mut builder = tauri::http::Response::builder()
        .status(status)
        .header("Cache-Control", "no-store")
        .header("Cross-Origin-Resource-Policy", "cross-origin")
        .header("X-Content-Type-Options", "nosniff");
    if let Some(origin) = origin {
        builder = builder
            .header("Access-Control-Allow-Origin", origin)
            .header("Vary", "Origin");
    }
    if let Some(length) = length {
        builder = builder.header("Content-Length", length);
    }
    builder
        .body(Vec::new())
        .expect("static offline HTTP headers")
}
fn decode(value: &str) -> Option<String> {
    if value.len() > 768 {
        return None;
    }
    let bytes = value.as_bytes();
    let mut decoded = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' {
            let hex = std::str::from_utf8(bytes.get(i + 1..i + 3)?).ok()?;
            decoded.push(u8::from_str_radix(hex, 16).ok()?);
            i += 3;
        } else {
            decoded.push(bytes[i]);
            i += 1;
        }
    }
    let id = String::from_utf8(decoded).ok()?;
    valid_id(&id).then_some(id)
}
impl OfflineManager {
    fn serve(&self, request: tauri::http::Request<Vec<u8>>) -> HttpResponse {
        let origin = request
            .headers()
            .get("Origin")
            .and_then(|v| v.to_str().ok());
        if origin.is_some_and(|v| {
            ![
                "http://tauri.localhost",
                "https://tauri.localhost",
                "tauri://localhost",
            ]
            .contains(&v)
        }) {
            return response(403, None, None);
        }
        if !["GET", "HEAD"].contains(&request.method().as_str()) {
            return response(405, origin, None);
        }
        if request.uri().query().is_some() {
            return response(404, origin, None);
        }
        let Some(id) = request.uri().path().strip_prefix('/').and_then(decode) else {
            return response(404, origin, None);
        };
        let asset = {
            let Ok(inner) = self.inner.lock() else {
                return response(500, origin, None);
            };
            if !inner.completed.contains_key(&id) {
                return response(404, origin, None);
            }
            let Some(asset) = inner
                .manifest
                .as_ref()
                .and_then(|m| m.assets.iter().find(|a| a.asset_id == id))
                .cloned()
            else {
                return response(404, origin, None);
            };
            asset
        };
        // The read handle denies writes/deletion while hashing and serving. Size
        // and timestamps alone cannot detect rapid same-size Windows rewrites.
        let verified = (|| {
            let mut file = self.cache.open_read(&self.cache.name(&id, "audio"))?;
            if !crate::offline_fs::verify_file(&mut file, asset.bytes, &asset.sha256)? {
                return Err(IO_ERROR.to_string());
            }
            Ok::<_, String>(file)
        })();
        let mut file = match verified {
            Ok(file) => file,
            Err(_) => {
                if let Ok(mut inner) = self.inner.lock() {
                    inner.completed.remove(&id);
                }
                return response(409, origin, None);
            }
        };
        let requested = match request.headers().get("Range") {
            Some(value) => match value
                .to_str()
                .ok()
                .and_then(|value| range(value, asset.bytes))
            {
                Some(range) => Some(range),
                None => {
                    let mut result = response(416, origin, None);
                    result.headers_mut().insert(
                        "Content-Range",
                        format!("bytes */{}", asset.bytes).parse().unwrap(),
                    );
                    return result;
                }
            },
            None => None,
        };
        let (start, requested_end) = requested.unwrap_or((0, asset.bytes - 1));
        let end = requested_end.min(start + CHUNK_BYTES - 1);
        let partial = requested.is_some() || end + 1 < asset.bytes;
        let head = request.method() == tauri::http::Method::HEAD;
        let length = if head && requested.is_none() {
            asset.bytes
        } else {
            end - start + 1
        };
        let mut result = response(
            if partial && !head {
                206
            } else if requested.is_some() {
                206
            } else {
                200
            },
            origin,
            Some(length),
        );
        let headers = result.headers_mut();
        headers.insert("Content-Type", asset.content_type.parse().unwrap());
        headers.insert("Accept-Ranges", "bytes".parse().unwrap());
        headers.insert("ETag", format!("\"{}\"", asset.sha256).parse().unwrap());
        if partial && (!head || requested.is_some()) {
            headers.insert(
                "Content-Range",
                format!("bytes {start}-{end}/{}", asset.bytes)
                    .parse()
                    .unwrap(),
            );
        }
        if !head {
            let mut body = vec![0; length as usize];
            if file.seek(SeekFrom::Start(start)).is_err() || file.read_exact(&mut body).is_err() {
                return response(500, origin, None);
            }
            *result.body_mut() = body;
        }
        result
    }
}

#[cfg(test)]
#[path = "offline_tests.rs"]
mod tests;
