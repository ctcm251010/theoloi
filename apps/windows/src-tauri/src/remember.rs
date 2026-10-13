use std::{
    fs,
    io::{Read, Write},
    path::Path,
};

const FAILURE: &str = "Không truy cập được dữ liệu đăng nhập đã mã hóa trên Windows.";

fn valid_base(base: &str) -> bool {
    tauri::Url::parse(base).is_ok_and(|url| {
        url.scheme() == "https"
            && url.host_str().is_some()
            && url.username().is_empty()
            && url.password().is_none()
            && url.query().is_none()
            && url.fragment().is_none()
            && url.origin().ascii_serialization() == base
    })
}

fn valid_code(code: &str) -> bool {
    (24..=256).contains(&code.chars().count()) && !code.chars().any(char::is_control)
}

#[cfg(windows)]
fn crypt(input: &[u8], base: &str, encrypt: bool) -> Result<Vec<u8>, String> {
    use std::{ffi::c_void, ptr};
    #[repr(C)]
    struct Blob {
        len: u32,
        data: *mut u8,
    }
    #[link(name = "crypt32")]
    unsafe extern "system" {
        fn CryptProtectData(
            input: *const Blob,
            description: *const u16,
            entropy: *const Blob,
            reserved: *mut c_void,
            prompt: *mut c_void,
            flags: u32,
            output: *mut Blob,
        ) -> i32;
        fn CryptUnprotectData(
            input: *const Blob,
            description: *mut *mut u16,
            entropy: *const Blob,
            reserved: *mut c_void,
            prompt: *mut c_void,
            flags: u32,
            output: *mut Blob,
        ) -> i32;
    }
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn LocalFree(memory: *mut c_void) -> *mut c_void;
    }
    // DPAPI current user + exact origin as entropy. Never LOCAL_MACHINE.
    let input = Blob {
        len: input.len() as u32,
        data: input.as_ptr() as *mut u8,
    };
    let entropy = Blob {
        len: base.len() as u32,
        data: base.as_ptr() as *mut u8,
    };
    let mut output = Blob {
        len: 0,
        data: ptr::null_mut(),
    };
    // SAFETY: input/entropy live for the call; all optional outputs are null;
    // returned memory belongs to LocalFree and is copied before releasing it.
    let success = unsafe {
        if encrypt {
            CryptProtectData(
                &input,
                ptr::null(),
                &entropy,
                ptr::null_mut(),
                ptr::null_mut(),
                1,
                &mut output,
            )
        } else {
            CryptUnprotectData(
                &input,
                ptr::null_mut(),
                &entropy,
                ptr::null_mut(),
                ptr::null_mut(),
                1,
                &mut output,
            )
        }
    };
    if success == 0 {
        return Err(FAILURE.into());
    }
    if output.data.is_null() {
        return Err(FAILURE.into());
    }
    let data = unsafe { std::slice::from_raw_parts(output.data, output.len as usize).to_vec() };
    unsafe {
        if !encrypt {
            for offset in 0..output.len as usize {
                ptr::write_volatile(output.data.add(offset), 0);
            }
        }
        LocalFree(output.data.cast());
    }
    Ok(data)
}

#[cfg(not(windows))]
fn crypt(_: &[u8], _: &str, _: bool) -> Result<Vec<u8>, String> {
    Err("Chỉ hỗ trợ Windows.".into())
}

pub fn save(dir: &Path, base: &str, code: &str) -> Result<(), String> {
    if !valid_base(base) || !valid_code(code) {
        return Err("Mã hoặc địa chỉ thư viện không hợp lệ.".into());
    }
    let encrypted = crypt(code.as_bytes(), base, true)?;
    let _lock = directory_lock(dir)?;
    let pending = dir.join("access-code.pending");
    remove_if_present(&pending)?;
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&pending)
        .map_err(|_| FAILURE)?;
    let result = (|| {
        file.write_all(&encrypted)?;
        file.sync_all()?;
        drop(file);
        fs::rename(&pending, dir.join("access-code.dpapi"))
    })();
    if result.is_err() {
        let _ = fs::remove_file(pending);
    }
    result.map_err(|_| FAILURE.into())
}

pub fn read(dir: &Path, base: &str) -> Result<Option<String>, String> {
    if !valid_base(base) {
        return Err("Địa chỉ thư viện không hợp lệ.".into());
    }
    if !dir.exists() {
        return Ok(None);
    }
    let _lock = directory_lock(dir)?;
    let path = dir.join("access-code.dpapi");
    let metadata = match fs::symlink_metadata(&path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(FAILURE.into()),
        Ok(value) => value,
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() || metadata.len() > 8192 {
        return Err(FAILURE.into());
    }
    let mut bytes = Vec::new();
    fs::File::open(path)
        .map_err(|_| FAILURE)?
        .take(8193)
        .read_to_end(&mut bytes)
        .map_err(|_| FAILURE)?;
    if bytes.len() > 8192 {
        return Err(FAILURE.into());
    }
    let code = String::from_utf8(crypt(&bytes, base, false)?).map_err(|_| FAILURE)?;
    if !valid_code(&code) {
        return Err(FAILURE.into());
    }
    Ok(Some(code))
}

pub fn forget(dir: &Path) -> Result<(), String> {
    if !dir.exists() {
        return Ok(());
    }
    let _lock = directory_lock(dir)?;
    remove_if_present(&dir.join("access-code.pending"))?;
    remove_if_present(&dir.join("access-code.dpapi"))
}

fn directory_lock(dir: &Path) -> Result<fs::File, String> {
    fs::create_dir_all(dir).map_err(|_| FAILURE)?;
    let lock = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(dir.join("access-code.lock"))
        .map_err(|_| FAILURE)?;
    // OS-owned lock is released even after process termination. Fail instead of
    // blocking the UI if another application instance is updating this store.
    lock.try_lock()
        .map_err(|_| "Đăng nhập đã lưu đang được một cửa sổ khác cập nhật. Hãy thử lại.")?;
    Ok(lock)
}

fn remove_if_present(path: &Path) -> Result<(), String> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(_) => Err(FAILURE.into()),
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn stores_ciphertext_bound_to_origin_and_forgets_it() {
        let dir = std::env::temp_dir().join(format!(
            "audiotp-remember-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let base = "https://library.test";
        let code = "synthetic-only-access-code-for-native-test";
        assert_eq!(super::read(&dir, base).unwrap(), None);
        super::save(&dir, base, code).unwrap();
        let bytes = std::fs::read(dir.join("access-code.dpapi")).unwrap();
        assert!(!bytes.windows(code.len()).any(|w| w == code.as_bytes()));
        assert_eq!(super::read(&dir, base).unwrap().as_deref(), Some(code));
        super::save(&dir, base, code).unwrap();
        assert_eq!(super::read(&dir, base).unwrap().as_deref(), Some(code));
        assert!(super::read(&dir, "https://another.test").is_err());
        std::fs::write(dir.join("access-code.dpapi"), b"invalid ciphertext").unwrap();
        assert!(super::read(&dir, base).is_err());
        super::forget(&dir).unwrap();
        assert_eq!(super::read(&dir, base).unwrap(), None);
        std::fs::remove_file(dir.join("access-code.lock")).unwrap();
        std::fs::remove_dir(dir).unwrap();
    }

    #[test]
    fn refuses_unsafe_origins_and_invalid_code_without_creating_files() {
        let dir = std::env::temp_dir().join("audiotp-invalid-code-must-not-exist");
        for base in [
            "http://example.test",
            "https://code@example.test",
            "https://example.test/?code=x",
        ] {
            assert!(super::save(&dir, base, "synthetic-only-access-code-for-native-test").is_err());
        }
        assert!(super::save(&dir, "https://library.test", "short").is_err());
        assert!(!dir.exists());
    }

    #[test]
    fn interrupted_staging_recovers_and_logout_cleans_it() {
        let dir = std::env::temp_dir().join(format!("audiotp-stale-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("access-code.pending"),
            b"interrupted synthetic save",
        )
        .unwrap();
        super::save(
            &dir,
            "https://library.test",
            "synthetic-only-access-code-for-native-test",
        )
        .unwrap();
        std::fs::write(dir.join("access-code.pending"), b"another interrupted save").unwrap();
        super::forget(&dir).unwrap();
        assert!(!dir.join("access-code.pending").exists());
        super::save(
            &dir,
            "https://library.test",
            "synthetic-only-access-code-for-native-test",
        )
        .unwrap();
        super::forget(&dir).unwrap();
        std::fs::remove_file(dir.join("access-code.lock")).unwrap();
        std::fs::remove_dir(dir).unwrap();
    }

    #[test]
    fn lock_protects_store_across_processes_and_releases_on_close() {
        let dir = std::env::temp_dir().join(format!("audiotp-lock-{}", std::process::id()));
        let lock = super::directory_lock(&dir).unwrap();
        let child = |held: bool| {
            std::process::Command::new(std::env::current_exe().unwrap())
                .args(["--exact", "remember::tests::child_lock_probe", "--ignored"])
                .env("AUDIOTP_TEST_LOCK_DIR", &dir)
                .env("AUDIOTP_TEST_LOCK_HELD", if held { "yes" } else { "no" })
                .status()
                .unwrap()
                .success()
        };
        assert!(child(true));
        drop(lock);
        assert!(child(false));
        std::fs::remove_file(dir.join("access-code.lock")).unwrap();
        std::fs::remove_dir(dir).unwrap();
    }

    #[test]
    #[ignore = "subprocess helper executed twice by lock_protects_store_across_processes_and_releases_on_close"]
    fn child_lock_probe() {
        let dir = std::path::PathBuf::from(std::env::var_os("AUDIOTP_TEST_LOCK_DIR").unwrap());
        let held = std::env::var("AUDIOTP_TEST_LOCK_HELD").unwrap() == "yes";
        assert_eq!(super::directory_lock(&dir).is_err(), held);
    }
}
