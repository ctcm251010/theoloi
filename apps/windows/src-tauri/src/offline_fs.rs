//! The offline cache has no caller-selected paths. All names are hashes of IDs.
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File},
    io::{Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
};

pub const IO_ERROR: &str = "Không truy cập được bộ nhớ offline an toàn.";
pub struct Cache {
    pub root: PathBuf,
    _directories: Vec<File>,
    _lock: File,
}

impl Cache {
    pub fn open(app_dir: &Path) -> Result<Self, String> {
        if !app_dir.is_absolute() {
            return Err(IO_ERROR.into());
        }
        let root = app_dir.join("offline-v1");
        let mut directories = Vec::new();
        // Keep each directory handle open without FILE_SHARE_DELETE. On Windows
        // this prevents ancestry replacement by a junction during an operation.
        let mut current = PathBuf::new();
        for component in root.components() {
            if matches!(
                component,
                std::path::Component::ParentDir | std::path::Component::CurDir
            ) {
                return Err(IO_ERROR.into());
            }
            current.push(component);
            if matches!(component, std::path::Component::Prefix(_)) {
                continue;
            }
            match fs::symlink_metadata(&current) {
                Ok(_) => (),
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                    fs::create_dir(&current).map_err(|_| IO_ERROR)?
                }
                Err(_) => return Err(IO_ERROR.into()),
            }
            directories.push(open_safe(&current, false, false, true)?);
        }
        let lock_path = root.join("cache.lock");
        let lock = open_safe(&lock_path, true, true, false)?;
        lock.try_lock()
            .map_err(|_| "Bộ nhớ offline đang được một cửa sổ khác sử dụng.".to_string())?;
        Ok(Self {
            root,
            _directories: directories,
            _lock: lock,
        })
    }
    pub fn name(&self, id: &str, extension: &str) -> PathBuf {
        self.root
            .join(format!("{:x}.{extension}", Sha256::digest(id.as_bytes())))
    }
    fn child(&self, path: &Path) -> Result<(), String> {
        if path.parent() != Some(self.root.as_path()) {
            return Err(IO_ERROR.into());
        }
        let name = path.file_name().and_then(|v| v.to_str()).ok_or(IO_ERROR)?;
        let hashed = name.split_once('.').is_some_and(|(stem, ext)| {
            stem.len() == 64
                && stem.bytes().all(|b| b.is_ascii_hexdigit())
                && ["audio", "part"].contains(&ext)
        });
        if !hashed
            && ![
                "manifest.json",
                "manifest.pending",
                "queue.json",
                "queue.pending",
            ]
            .contains(&name)
        {
            return Err(IO_ERROR.into());
        }
        Ok(())
    }
    pub fn open_read(&self, path: &Path) -> Result<File, String> {
        self.child(path)?;
        open_safe(path, false, false, false)
    }
    pub fn open_write(&self, path: &Path, create: bool) -> Result<File, String> {
        self.child(path)?;
        open_safe(path, true, create, false)
    }
    pub fn remove(&self, path: &Path) -> Result<(), String> {
        self.child(path)?;
        if !path.try_exists().map_err(|_| IO_ERROR)? {
            return Ok(());
        }
        // Never follow a reparse point or unlink a hardlink pretending to be ours.
        drop(self.open_read(path)?);
        fs::remove_file(path).map_err(|_| IO_ERROR.into())
    }
    pub fn free_bytes(&self) -> Result<u64, String> {
        free_space(&self.root)
    }
    pub fn verify(&self, id: &str, bytes: u64, hash: &str) -> Result<bool, String> {
        let mut file = match self.open_read(&self.name(id, "audio")) {
            Ok(file) => file,
            Err(_) => return Ok(false),
        };
        verify_file(&mut file, bytes, hash)
    }
    pub fn write_json<T: serde::Serialize>(&self, name: &str, value: &T) -> Result<(), String> {
        let destination = self.root.join(format!("{name}.json"));
        let pending = self.root.join(format!("{name}.pending"));
        self.remove(&pending)?;
        let bytes = serde_json::to_vec(value).map_err(|_| IO_ERROR)?;
        let mut file = self.open_write(&pending, true)?;
        file.set_len(0).map_err(|_| IO_ERROR)?;
        file.write_all(&bytes).map_err(|_| IO_ERROR)?;
        file.sync_all().map_err(|_| IO_ERROR)?;
        drop(file);
        if destination.exists() {
            drop(self.open_read(&destination)?);
        }
        fs::rename(pending, destination).map_err(|_| IO_ERROR.into())
    }
    pub fn read_json<T: serde::de::DeserializeOwned>(
        &self,
        name: &str,
    ) -> Result<Option<T>, String> {
        let path = self.root.join(format!("{name}.json"));
        if !path.try_exists().map_err(|_| IO_ERROR)? {
            return Ok(None);
        }
        let file = self.open_read(&path)?;
        if file.metadata().map_err(|_| IO_ERROR)?.len() > 8 * 1024 * 1024 {
            return Err(IO_ERROR.into());
        }
        serde_json::from_reader(file.take(8 * 1024 * 1024 + 1))
            .map(Some)
            .map_err(|_| IO_ERROR.into())
    }
    pub fn promote(&self, id: &str) -> Result<(), String> {
        let source = self.name(id, "part");
        let destination = self.name(id, "audio");
        drop(self.open_read(&source)?);
        if destination.exists() {
            drop(self.open_read(&destination)?);
        }
        fs::rename(source, destination).map_err(|_| IO_ERROR.into())
    }
}

pub fn verify_file(file: &mut File, bytes: u64, hash: &str) -> Result<bool, String> {
    if file.metadata().map_err(|_| IO_ERROR)?.len() != bytes {
        return Ok(false);
    }
    file.seek(SeekFrom::Start(0)).map_err(|_| IO_ERROR)?;
    let mut digest = Sha256::new();
    let mut buffer = [0; 64 * 1024];
    let mut read = 0u64;
    loop {
        let count = file.read(&mut buffer).map_err(|_| IO_ERROR)?;
        if count == 0 {
            break;
        }
        read += count as u64;
        if read > bytes {
            return Ok(false);
        }
        digest.update(&buffer[..count]);
    }
    Ok(read == bytes && format!("{:x}", digest.finalize()) == hash)
}

#[cfg(windows)]
fn open_safe(path: &Path, write: bool, create: bool, directory: bool) -> Result<File, String> {
    use std::os::windows::{fs::OpenOptionsExt, io::AsRawHandle};
    let mut options = fs::OpenOptions::new();
    options
        .read(true)
        .write(write)
        .create(create)
        .truncate(false)
        .share_mode(if write || directory { 3 } else { 1 })
        .custom_flags(0x00200000 | if directory { 0x02000000 } else { 0 }); // OPEN_REPARSE_POINT / BACKUP_SEMANTICS
    if directory {
        options.access_mode(0x80);
    } // FILE_READ_ATTRIBUTES, no directory listing right required.
    let file = options.open(path).map_err(|_| IO_ERROR)?;
    let mut info = FileInfo::default();
    // SAFETY: live file handle and correctly sized writable Win32 structure.
    if unsafe { GetFileInformationByHandle(file.as_raw_handle().cast(), &mut info) } == 0
        || info.attributes & 0x400 != 0
        || (info.attributes & 0x10 != 0) != directory
        || (!directory && info.links != 1)
    {
        return Err(IO_ERROR.into());
    }
    Ok(file)
}
#[cfg(windows)]
#[repr(C)]
#[derive(Default)]
struct FileInfo {
    attributes: u32,
    creation: [u32; 2],
    access: [u32; 2],
    write: [u32; 2],
    volume: u32,
    size_high: u32,
    size_low: u32,
    links: u32,
    index_high: u32,
    index_low: u32,
}
#[cfg(windows)]
#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetFileInformationByHandle(handle: *mut std::ffi::c_void, info: *mut FileInfo) -> i32;
    fn GetDiskFreeSpaceExW(
        path: *const u16,
        available: *mut u64,
        total: *mut u64,
        free: *mut u64,
    ) -> i32;
}
#[cfg(windows)]
fn free_space(path: &Path) -> Result<u64, String> {
    use std::os::windows::ffi::OsStrExt;
    let path: Vec<u16> = path.as_os_str().encode_wide().chain(Some(0)).collect();
    let mut available = 0;
    if unsafe {
        GetDiskFreeSpaceExW(
            path.as_ptr(),
            &mut available,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
        )
    } == 0
    {
        return Err(IO_ERROR.into());
    }
    Ok(available.min(9_007_199_254_740_991))
}
#[cfg(not(windows))]
fn open_safe(_path: &Path, _write: bool, _create: bool, _directory: bool) -> Result<File, String> {
    Err("Chỉ hỗ trợ bộ nhớ offline Windows.".into())
}
#[cfg(not(windows))]
fn free_space(_path: &Path) -> Result<u64, String> {
    Err("Chỉ hỗ trợ Windows.".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn temp() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("target")
            .join(format!(
                "audiotp-offline-fs-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ))
    }
    #[test]
    fn cache_isolated_verified_and_deletion_is_local() {
        let dir = temp();
        let cache = Cache::open(&dir).unwrap();
        let original = dir.join("original.audio");
        fs::write(&original, b"outside cache").unwrap();
        let path = cache.name("../../outside:asset", "audio");
        assert_eq!(path.parent(), Some(cache.root.as_path()));
        let mut file = cache.open_write(&path, true).unwrap();
        file.write_all(b"authorized test bytes").unwrap();
        drop(file);
        let hash = format!("{:x}", Sha256::digest(b"authorized test bytes"));
        assert!(cache.verify("../../outside:asset", 21, &hash).unwrap());
        assert!(!cache
            .verify("../../outside:asset", 21, &"0".repeat(64))
            .unwrap());
        assert!(cache.open_read(&original).is_err());
        assert!(cache.remove(&original).is_err());
        cache.remove(&path).unwrap();
        assert!(!path.exists());
        assert!(original.exists());
        assert!(cache.free_bytes().unwrap() > 0);
        drop(cache);
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn a_second_manager_cannot_mutate_the_same_cache() {
        let dir = temp();
        let first = Cache::open(&dir).unwrap();
        assert!(Cache::open(&dir).is_err());
        drop(first);
        let second = Cache::open(&dir).unwrap();
        drop(second);
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn hardlinks_are_rejected_without_touching_their_target() {
        let dir = temp();
        let cache = Cache::open(&dir).unwrap();
        let original = dir.join("original.audio");
        fs::write(&original, b"original").unwrap();
        let link = cache.name("id", "audio");
        fs::hard_link(&original, &link).unwrap();
        assert!(cache.open_read(&link).is_err());
        assert!(cache.open_write(&link, false).is_err());
        assert!(cache.remove(&link).is_err());
        assert_eq!(fs::read(&original).unwrap(), b"original");
        drop(cache);
        fs::remove_dir_all(dir).unwrap();
    }
}
