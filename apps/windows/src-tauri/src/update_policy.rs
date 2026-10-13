pub const API_ORIGIN: &str = "https://audiotp-media-api.ctcm251010.workers.dev";

pub fn valid_token(token: &str) -> bool {
    (1..=4096).contains(&token.len())
        && token
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-._~+/=".contains(&byte))
}

pub fn valid_release(current: &str, version: &str, url: &tauri::Url) -> bool {
    let (Ok(current), Ok(release)) = (
        semver::Version::parse(current),
        semver::Version::parse(version),
    ) else {
        return false;
    };
    release.cmp_precedence(&current).is_gt()
        && url.as_str() == format!("{API_ORIGIN}/v1/update-files/{version}/installer")
}

pub struct UpdateSession<T> {
    generation: u64,
    checking: bool,
    installing: bool,
    pending: Option<T>,
}

impl<T> Default for UpdateSession<T> {
    fn default() -> Self {
        Self {
            generation: 0,
            checking: false,
            installing: false,
            pending: None,
        }
    }
}

impl<T> UpdateSession<T> {
    pub fn begin_check(&mut self) -> Option<u64> {
        if self.checking || self.installing {
            return None;
        }
        self.generation = self.generation.checked_add(1)?;
        self.checking = true;
        self.pending = None;
        Some(self.generation)
    }
    pub fn finish_check(&mut self, generation: u64, pending: Option<T>) -> bool {
        if self.generation != generation || !self.checking {
            return false;
        }
        self.checking = false;
        self.pending = pending;
        true
    }
    pub fn clear(&mut self) {
        self.generation = self.generation.wrapping_add(1);
        self.checking = false;
        self.pending = None;
    }
    pub fn begin_install(&mut self) -> Option<(u64, T)> {
        if self.checking || self.installing {
            return None;
        }
        let update = self.pending.take()?;
        self.installing = true;
        Some((self.generation, update))
    }
    pub fn may_install(&self, generation: u64) -> bool {
        self.installing && self.generation == generation
    }
    pub fn finish_install(&mut self) {
        self.installing = false;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bearer_tokens_are_bounded_and_cannot_inject_headers() {
        assert!(valid_token("abc.def-123_xyz"));
        assert!(valid_token(&"a".repeat(4096)));
        for token in [
            "",
            "abc\r\nInjected: true",
            "abc\tdef",
            "abc def",
            "é",
            &"a".repeat(4097),
        ] {
            assert!(!valid_token(token));
        }
    }

    #[test]
    fn installers_are_only_newer_versions_at_the_exact_private_route() {
        let good =
            "https://audiotp-media-api.ctcm251010.workers.dev/v1/update-files/1.0.2/installer";
        assert!(valid_release(
            "1.0.1",
            "1.0.2",
            &tauri::Url::parse(good).unwrap()
        ));
        assert!(!valid_release(
            "1.0.2",
            "1.0.2",
            &tauri::Url::parse(good).unwrap()
        ));
        assert!(!valid_release(
            "1.1.0",
            "1.0.2",
            &tauri::Url::parse(good).unwrap()
        ));
        assert!(!valid_release(
            "invalid",
            "1.0.2",
            &tauri::Url::parse(good).unwrap()
        ));
        assert!(!valid_release(
            "1.0.1+build1",
            "1.0.1+build2",
            &tauri::Url::parse("https://audiotp-media-api.ctcm251010.workers.dev/v1/update-files/1.0.1+build2/installer").unwrap(),
        ));
        for url in [
            good.replace("https://", "http://"),
            good.replace("workers.dev/", "workers.dev.evil/"),
            good.replace("https://", "https://user@"),
            good.replace("workers.dev/", "workers.dev:444/"),
            good.replace("/1.0.2/", "/1.0.3/"),
            format!("{good}?token=other"),
            format!("{good}#fragment"),
            format!("{good}/"),
        ] {
            assert!(
                !valid_release("1.0.1", "1.0.2", &tauri::Url::parse(&url).unwrap()),
                "{url}"
            );
        }
    }

    #[test]
    fn logout_discards_pending_and_late_check_results() {
        let mut session = UpdateSession::<u8>::default();
        let old = session.begin_check().unwrap();
        assert!(session.begin_check().is_none());
        session.clear();
        let new = session.begin_check().unwrap();
        assert!(!session.finish_check(old, Some(1)));
        assert!(session.finish_check(new, Some(2)));
        assert_eq!(session.begin_install(), Some((new, 2)));
        assert!(session.begin_install().is_none());
        assert!(session.begin_check().is_none());
    }

    #[test]
    fn logout_during_download_blocks_install_until_download_finishes() {
        let mut session = UpdateSession::<u8>::default();
        let generation = session.begin_check().unwrap();
        assert!(session.finish_check(generation, Some(1)));
        let (generation, _) = session.begin_install().unwrap();
        assert!(session.may_install(generation));
        session.clear();
        assert!(!session.may_install(generation));
        assert!(session.begin_check().is_none());
        session.finish_install();
        assert!(session.begin_check().is_some());
    }

    #[test]
    fn an_empty_or_failed_check_removes_the_previous_update() {
        let mut session = UpdateSession::<u8>::default();
        let old = session.begin_check().unwrap();
        assert!(session.finish_check(old, Some(1)));
        let new = session.begin_check().unwrap();
        assert!(session.begin_install().is_none());
        assert!(session.finish_check(new, None));
        assert!(session.begin_install().is_none());
    }
}
