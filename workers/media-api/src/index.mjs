import catalog from '../generated/catalog.json' with {type:'json'};
import assets from '../generated/assets.json' with {type:'json'};
import {createService} from './service.mjs';
export default createService(catalog,assets);
