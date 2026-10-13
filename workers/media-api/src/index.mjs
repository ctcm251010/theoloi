import catalog from '../generated/catalog.json' with {type:'json'};
import assets from '../generated/assets.json' with {type:'json'};
import {createService} from './service.mjs';
// JSON inference widens literal enums. validateData inside createService checks
// every field at runtime before any request, including forbidden private fields.
export default createService(/** @type {import('./contracts').ClientCatalog} */(catalog),assets);
