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
