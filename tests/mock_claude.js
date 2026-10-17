// A stand-in for claude.ai's window.claude (db, user, downloads) for the page tests. The store lives in
// sessionStorage, so it survives a reload the way the real one does. Seed it with sessionStorage __mockdb (path -> record) and __mockcfg ({me, isOwner, names, noDb, downloads}).
(() => {
  if (window !== window.top) return;     // not inside a test build's iframe
  const KEY = "__mockdb";
  const cfg = JSON.parse(sessionStorage.getItem("__mockcfg") || "{}");
  let data = JSON.parse(sessionStorage.getItem(KEY) || "{}");
  const listeners = [];
  const save = () => sessionStorage.setItem(KEY, JSON.stringify(data));
  const clone = (v) => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));
  const depth = (p) => p.split("/").length;
  function snap(p) { const d = data[p]; return { id: p.split("/").pop(), exists: d !== undefined, data: () => clone(d), metadata: { fromCache: false, hasPendingWrites: false } }; }
  function colDocs(path) { return Object.keys(data).filter((p) => p.startsWith(path + "/") && depth(p) === depth(path) + 1).sort().map(snap); }
  function deliver(l) {
    setTimeout(() => {
      if (!listeners.includes(l)) return;
      if (l.kind === "col") { const docs = colDocs(l.path); l.fn({ docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: {} }); }
      else l.fn(snap(l.path));
    }, 0);
  }
  function notify(path) {                // only the listeners a write concerns, as the real store does
    const parent = path.split("/").slice(0, -1).join("/");
    for (const l of [...listeners]) if (l.path === path || l.path === parent) deliver(l);
  }
  function log(entry) { window.__writes = (window.__writes || []).concat([entry]); }
  async function guard(path) {
    if (window.__mockFail) throw window.__mockFail;
    const me = cfg.me === undefined ? "u_owner" : cfg.me;
    const owner = cfg.isOwner === undefined ? true : cfg.isOwner;
    if (!owner && !(path === "people/" + me || path.startsWith("people/" + me + "/"))) throw { code: "invalid_argument", message: "refused by the access rules" };
  }
  function docRef(path) {
    return {
      id: path.split("/").pop(), path,
      get: async () => snap(path),
      set: async (d) => { await guard(path); data[path] = clone(d); save(); log({ op: "set", path, d: clone(d) }); notify(path); },
      update: async (d) => { await guard(path); data[path] = { ...(data[path] || {}), ...clone(d) }; save(); log({ op: "update", path, d: clone(d) }); notify(path); },
      delete: async () => { await guard(path); delete data[path]; save(); log({ op: "delete", path }); notify(path); },
      onSnapshot: (fn) => { const l = { kind: "doc", path, fn }; listeners.push(l); deliver(l); return () => listeners.splice(listeners.indexOf(l), 1); },
      collection: (sub) => colRef(path + "/" + sub),
    };
  }
  function colRef(path) {
    return {
      path, doc: (id) => docRef(path + "/" + id),
      onSnapshot: (fn) => { const l = { kind: "col", path, fn }; listeners.push(l); deliver(l); return () => listeners.splice(listeners.indexOf(l), 1); },
      get: async () => { const docs = colDocs(path); return { docs, size: docs.length, empty: !docs.length }; },
    };
  }
  const db = { doc: docRef, collection: colRef };
  const user = {
    id: async () => (cfg.me === undefined ? "u_owner" : cfg.me),
    isOwner: async () => (cfg.isOwner === undefined ? true : cfg.isOwner),
    canEdit: async () => true,
    profiles: async (ids) => Object.fromEntries([].concat(ids).map((id) => [id, { id, name: (cfg.names || {})[id] || "" }])),
  };
  window.__mock = {
    set(path, d) { data[path] = clone(d); save(); notify(path); },
    del(path) { delete data[path]; save(); notify(path); },
    get(path) { return clone(data[path]); },
    paths() { return Object.keys(data).sort(); },
  };
  window.claude = {
    use: async (name) => {
      if (name === "db") return cfg.noDb ? null : db;
      if (name === "user") return user;
      if (name === "downloads") return cfg.downloads ? { save: async (x) => { window.__saved = x.filename; } } : null;
      return null;
    },
  };
})();
