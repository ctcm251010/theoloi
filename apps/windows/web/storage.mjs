const KEY = 'audiotp.library.v1';
export class LibraryStore {
  constructor(storage) {
    this.storage=storage; this.favourites=[]; this.history=[]; this.theme='dark';
    try {
      const data=JSON.parse(storage?.getItem(KEY) || '{}');
      if(Array.isArray(data.favourites))this.favourites=[...new Set(data.favourites.filter(x=>typeof x==='string'))].slice(0,2000);
      if(data.historyVersion===2 && Array.isArray(data.history))this.history=data.history.filter(x=>x && typeof x.id==='string' && typeof x.revision==='string' && Number.isFinite(x.playedAt)).slice(0,100).map(({id,revision,playedAt})=>({id,revision,playedAt}));
      if(data.theme==='light')this.theme='light';
    } catch { /* Storage is optional, including when access is denied. */ }
  }
  save(){try{this.storage?.setItem(KEY,JSON.stringify({historyVersion:2,favourites:this.favourites,history:this.history,theme:this.theme}));}catch{}}
  toggleFavourite(id){this.favourites=this.favourites.includes(id)?this.favourites.filter(x=>x!==id):[...this.favourites,id];this.save();}
  record(track,revision){this.history=[{id:track.id,revision,playedAt:Date.now()},...this.history.filter(x=>x.id!==track.id)].slice(0,100);this.save();}
  setTheme(theme){this.theme=theme==='light'?'light':'dark';this.save();}
}
