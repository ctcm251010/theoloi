// Public shapes, not production catalog contents. Keep in sync with windows_catalog.py.
export interface ClientTrack {
  id: string;
  logicalId: string;
  mode: 'guide' | 'instrumental' | 'silent';
  section: 'main' | 'appendix' | null;
  number: number;
  title: string;
  category: string;
  durationSeconds: number;
}
export interface ClientCatalog { schemaVersion: 1; revision: string; tracks: ClientTrack[] }
export interface Asset { assetId: string; objectKey: string; bytes: number; sha256: string }
export interface PrayerTrack {
  id: 'watv:vi:prayer:our-wish';
  logicalId: 'watv:vi:prayer:our-wish';
  mode: 'prayer';
  section: null;
  number: null;
  title: 'Cầu nguyện chúng con mong muốn';
  category: 'Cầu nguyện';
  durationSeconds: number;
}
export interface QuickAudio { schemaVersion: 1; revision: string; tracks: PrayerTrack[]; assets: Record<string, Asset> }
export interface UpdateRelease { version: string; pubDate: string; notes: string; objectKey: string; bytes: number; sha256: string; signature: string }
