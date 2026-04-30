import { useState, useEffect, useCallback, useRef } from 'react'
import { api, auth } from './api'

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = `
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0f12;--bg2:#141720;--bg3:#1c2030;--bg4:#242840;
  --border:#2a2f45;--border2:#3a4060;
  --text:#c8cfe8;--text2:#7880a0;--text3:#4a5070;
  --accent:#4f8ef7;--accent2:#2a5ab8;
  --green:#22c55e;--green2:#166534;
  --amber:#f59e0b;--amber2:#78350f;
  --red:#ef4444;--red2:#7f1d1d;
  --cyan:#06b6d4;--purple:#a855f7;
  --mono:'JetBrains Mono',monospace;--sans:'IBM Plex Sans',sans-serif;
}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:13px;min-height:100vh}

/* ── Login ── */
.login-bg{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg)}
.login-card{background:var(--bg2);border:1px solid var(--border2);border-radius:16px;padding:36px 32px;width:360px;max-width:95vw}
.login-logo{display:flex;align-items:center;gap:10px;margin-bottom:28px}
.login-logo-mark{width:38px;height:38px;background:var(--accent2);border-radius:10px;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-weight:600;font-size:13px;color:var(--accent)}
.login-logo-text{font-family:var(--mono);font-size:16px;font-weight:600;color:var(--text)}
.login-logo-sub{font-size:11px;color:var(--text2);margin-top:1px}
.login-field{margin-bottom:14px}
.login-label{font-family:var(--mono);font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px}
.login-input{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:9px 12px;border-radius:8px;font-family:var(--mono);font-size:12px;outline:none;transition:border-color .15s}
.login-input:focus{border-color:var(--accent)}
.login-input.error{border-color:var(--red)}
.login-btn{width:100%;background:var(--accent2);border:1px solid var(--accent);color:var(--accent);padding:10px;border-radius:8px;font-family:var(--mono);font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;margin-top:4px}
.login-btn:hover{background:var(--accent);color:#fff}
.login-btn:disabled{opacity:.5;cursor:not-allowed}
.login-err{background:var(--red2);border:1px solid var(--red);color:var(--red);border-radius:7px;padding:8px 12px;font-family:var(--mono);font-size:11px;margin-bottom:14px}
.login-footer{text-align:center;margin-top:20px;font-family:var(--mono);font-size:10px;color:var(--text3)}

/* ── Shell ── */
.shell{display:flex;height:100vh;overflow:hidden}
.sidebar{width:52px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:12px 0;gap:4px;flex-shrink:0}
.logo{width:36px;height:36px;background:var(--accent2);border-radius:10px;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-weight:600;font-size:11px;color:var(--accent)}
.nav-icon{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text3);font-size:16px;transition:all .15s;border:1px solid transparent;background:none;user-select:none}
.nav-icon:hover{background:var(--bg3);color:var(--text)}
.nav-icon.active{background:var(--accent2);color:var(--accent);border-color:var(--accent)}
.nav-sep{width:28px;height:1px;background:var(--border);margin:4px 0}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{height:44px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 16px;gap:10px;flex-shrink:0}
.topbar-title{font-family:var(--mono);font-size:12px;color:var(--text2);flex:1}
.topbar-title b{color:var(--text);font-weight:500}
.tb-badge{display:flex;align-items:center;gap:5px;font-family:var(--mono);font-size:11px;color:var(--text2)}
.dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.dot.green{background:var(--green);box-shadow:0 0 6px #22c55e55}
.dot.red{background:var(--red)}.dot.amber{background:var(--amber)}.dot.gray{background:var(--text3)}
.content{flex:1;overflow-y:auto;padding:16px}
.content::-webkit-scrollbar{width:4px}
.content::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}

/* ── Cards & tables ── */
.summary-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.stat-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:12px 14px;cursor:pointer;transition:border-color .15s}
.stat-card:hover{border-color:var(--border2)}
.stat-label{font-family:var(--mono);font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.stat-val{font-family:var(--mono);font-size:22px;font-weight:600;line-height:1}
.stat-sub{font-size:11px;color:var(--text2);margin-top:4px}
.stat-card.green .stat-val{color:var(--green)}.stat-card.amber .stat-val{color:var(--amber)}
.stat-card.red .stat-val{color:var(--red)}.stat-card.blue .stat-val{color:var(--accent)}
.sec-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.sec-title{font-family:var(--mono);font-size:11px;color:var(--text2);text-transform:uppercase;letter-spacing:.8px}
.sec-actions{display:flex;gap:6px;align-items:center}
.tbl-wrap{background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:16px}
.tbl-head{display:grid;padding:8px 14px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px}
.tbl-row{display:grid;padding:9px 14px;border-bottom:1px solid var(--border);align-items:center;cursor:pointer;transition:background .1s;font-size:11px}
.tbl-row:last-child{border-bottom:none}.tbl-row:hover{background:var(--bg3)}
.patch-cols{grid-template-columns:180px 1fr 60px 110px 100px}
.docker-cols{grid-template-columns:150px 1fr 80px 100px 80px}
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:4px;font-family:var(--mono);font-size:10px;font-weight:500;white-space:nowrap}
.badge.green{background:var(--green2);color:var(--green)}.badge.amber{background:var(--amber2);color:var(--amber)}
.badge.red{background:var(--red2);color:var(--red)}.badge.blue{background:var(--accent2);color:var(--accent)}
.badge.gray{background:var(--bg3);color:var(--text2);border:1px solid var(--border)}.badge.cyan{background:#083344;color:var(--cyan)}
.hostname{font-family:var(--mono);font-size:12px;color:var(--text);font-weight:500}
.os-tag{font-family:var(--mono);font-size:11px;color:var(--text2)}
.pkg-count-n{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--amber)}
.pkg-count-z{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--green)}
.btn{background:var(--bg3);border:1px solid var(--border2);color:var(--text);padding:4px 10px;border-radius:6px;font-family:var(--mono);font-size:11px;cursor:pointer;transition:all .15s;white-space:nowrap}
.btn:hover{background:var(--bg4);border-color:var(--accent);color:var(--accent)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn.primary{background:var(--accent2);border-color:var(--accent);color:var(--accent)}
.btn.primary:hover{background:var(--accent);color:#fff}
.btn.danger{background:var(--red2);border-color:var(--red);color:var(--red)}

/* ── Log ── */
.log-panel{background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:16px}
.log-body{font-family:var(--mono);font-size:11px;padding:10px 14px;max-height:200px;overflow-y:auto;line-height:1.8}
.log-line{display:flex;gap:12px}
.log-ts{color:var(--text3);min-width:80px;flex-shrink:0}
.log-lvl{min-width:28px;flex-shrink:0}
.log-lvl.OK{color:var(--green)}.log-lvl.WARN{color:var(--amber)}.log-lvl.ERROR{color:var(--red)}.log-lvl.INFO{color:var(--accent)}
.log-msg{color:var(--text2)}

/* ── Telegram panel ── */
.tg-panel{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:16px}
.tg-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.tg-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)}
.tg-row:last-child{border-bottom:none}
.tg-info{flex:1}
.tg-name{font-family:var(--mono);font-size:11px;color:var(--text)}
.tg-desc{font-size:11px;color:var(--text2);margin-top:2px}

/* ── Toggle ── */
.tog{position:relative;width:34px;height:18px;cursor:pointer;flex-shrink:0}
.tog input{opacity:0;position:absolute;width:100%;height:100%;cursor:pointer;margin:0}
.tog-track{width:34px;height:18px;background:var(--bg4);border-radius:9px;border:1px solid var(--border2);transition:background .2s}
.tog input:checked+.tog-track{background:var(--accent2);border-color:var(--accent)}
.tog-thumb{position:absolute;top:2px;left:2px;width:14px;height:14px;background:var(--text3);border-radius:50%;transition:transform .2s,background .2s;pointer-events:none}
.tog input:checked~.tog-thumb{transform:translateX(16px);background:var(--accent)}

/* ── Form inputs ── */
.inp{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:6px;font-family:var(--mono);font-size:11px;outline:none;width:100%}
.inp:focus{border-color:var(--accent)}
.form-label{font-family:var(--mono);font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.form-row{margin-bottom:12px}

/* ── Modal ── */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:100}
.modal{background:var(--bg2);border:1px solid var(--border2);border-radius:12px;padding:20px;width:420px;max-width:95vw}
.modal-title{font-family:var(--mono);font-size:14px;font-weight:600;color:var(--text);margin-bottom:4px}
.modal-sub{font-size:12px;color:var(--text2);margin-bottom:16px}

/* ── Toast ── */
.toast{position:fixed;bottom:20px;right:20px;background:var(--bg3);border:1px solid var(--border2);color:var(--text);font-family:var(--mono);font-size:11px;padding:8px 14px;border-radius:8px;z-index:999;transition:opacity .3s,transform .3s;max-width:320px;opacity:1;transform:translateY(0)}
.toast.green{border-color:var(--green);color:var(--green)}
.toast.red{border-color:var(--red);color:var(--red)}
.toast.hide{opacity:0;transform:translateY(6px)}
.empty{text-align:center;padding:32px;color:var(--text3);font-family:var(--mono);font-size:12px}
`

// ─── Toast ────────────────────────────────────────────────────────────────────
function Toast({ msg, type, onDone }) {
  const [hiding, setHiding] = useState(false)
  useEffect(() => {
    const t1 = setTimeout(() => setHiding(true), 2600)
    const t2 = setTimeout(onDone, 3000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [onDone])
  return <div className={`toast ${type} ${hiding ? 'hide' : ''}`}>{msg}</div>
}

function useToast() {
  const [toasts, setToasts] = useState([])
  const notify = useCallback((msg, type = 'default') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
  }, [])
  const remove = useCallback((id) => setToasts(t => t.filter(x => x.id !== id)), [])
  return { toasts, notify, remove }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmtTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false })
}
function fmtAgo(iso) {
  if (!iso) return '—'
  const s = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
function patchBadge(h) {
  if (h.reboot_required) return <span className="badge red">⟳ reboot req</span>
  if (h.patch_status === 'pending') return <span className="badge amber">⚠ pending</span>
  if (h.patch_status === 'current') return <span className="badge green">✓ current</span>
  if (h.patch_status === 'patching') return <span className="badge blue">↻ patching</span>
  if (h.patch_status === 'failed') return <span className="badge red">✗ failed</span>
  if (h.patch_status === 'scheduled') return <span className="badge blue">↻ scheduled</span>
  return <span className="badge gray">? unknown</span>
}

// ─── Login Screen ─────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const pwRef = useRef()

  async function submit(e) {
    e?.preventDefault()
    if (!username || !password) { setError('Enter username and password'); return }
    setLoading(true)
    setError('')
    try {
      const { access_token } = await api.login(username, password)
      auth.setToken(access_token)
      onLogin()
    } catch (err) {
      if (err.status === 429) {
        setError('Too many attempts. Wait 60 seconds and try again.')
      } else {
        setError('Invalid username or password.')
      }
      setPassword('')
      pwRef.current?.focus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-mark">PM</div>
          <div>
            <div className="login-logo-text">PatchMon Lite</div>
            <div className="login-logo-sub">Patch management for your homelab</div>
          </div>
        </div>

        {error && <div className="login-err">{error}</div>}

        <form onSubmit={submit}>
          <div className="login-field">
            <div className="login-label">Username</div>
            <input
              className={`login-input ${error ? 'error' : ''}`}
              value={username}
              onChange={e => { setUsername(e.target.value); setError('') }}
              autoComplete="username"
              autoFocus
              spellCheck={false}
            />
          </div>
          <div className="login-field">
            <div className="login-label">Password</div>
            <input
              ref={pwRef}
              type="password"
              className={`login-input ${error ? 'error' : ''}`}
              value={password}
              onChange={e => { setPassword(e.target.value); setError('') }}
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            className="login-btn"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign in →'}
          </button>
        </form>

        <div className="login-footer">Session ends when tab closes</div>
      </div>
    </div>
  )
}

// ─── Add Host Modal ───────────────────────────────────────────────────────────
function AddHostModal({ onClose, onAdded, notify }) {
  const [form, setForm] = useState({ hostname: '', ip_address: '', ssh_user: 'root', ssh_port: 22 })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function submit() {
    if (!form.hostname || !form.ip_address) { notify('Hostname and IP are required', 'red'); return }
    setLoading(true)
    try {
      await api.addHost(form)
      notify(`Host ${form.hostname} added`, 'green')
      onAdded()
      onClose()
    } catch (e) { notify(e.message, 'red') }
    finally { setLoading(false) }
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">Add Host</div>
        <div className="modal-sub">Host will be checked on the next scheduler run (or manually below)</div>
        <div className="form-row">
          <div className="form-label">Hostname</div>
          <input className="inp" value={form.hostname} onChange={e => set('hostname', e.target.value)} placeholder="pve-app01" autoFocus />
        </div>
        <div className="form-row">
          <div className="form-label">IP Address</div>
          <input className="inp" value={form.ip_address} onChange={e => set('ip_address', e.target.value)} placeholder="192.168.1.x" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div className="form-row">
            <div className="form-label">SSH User</div>
            <input className="inp" value={form.ssh_user} onChange={e => set('ssh_user', e.target.value)} />
          </div>
          <div className="form-row">
            <div className="form-label">SSH Port</div>
            <input className="inp" type="number" value={form.ssh_port} onChange={e => set('ssh_port', +e.target.value)} />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button className="btn primary" style={{ flex: 1 }} onClick={submit} disabled={loading}>
            {loading ? 'Adding...' : 'Add Host'}
          </button>
          <button className="btn" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

// ─── Patch Panel ──────────────────────────────────────────────────────────────
function PatchPanel({ notify, onAuthError }) {
  const [hosts, setHosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [busy, setBusy] = useState({})

  const load = useCallback(async () => {
    try { setHosts(await api.hosts()) }
    catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
    finally { setLoading(false) }
  }, [notify, onAuthError])

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  const pending = hosts.reduce((s, h) => s + h.pending_count, 0)
  const upToDate = hosts.filter(h => h.patch_status === 'current').length
  const rebootReq = hosts.filter(h => h.reboot_required).length

  async function doCheck(h) {
    notify(`Queuing check for ${h.hostname}...`)
    try { await api.checkHost(h.id); setTimeout(load, 2000) }
    catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
  }

  async function doPatch(h, dry = false) {
    setBusy(b => ({ ...b, [h.id]: true }))
    try {
      const r = await api.patchHost(h.id, dry)
      notify(`${dry ? 'Dry run' : 'Patch'} complete: ${h.hostname} — ${r.packages_updated} pkgs`, 'green')
      load()
    } catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
    finally { setBusy(b => ({ ...b, [h.id]: false })) }
  }

  async function doDelete(h) {
    if (!confirm(`Remove ${h.hostname} from PatchMon?`)) return
    try { await api.deleteHost(h.id); notify(`Removed ${h.hostname}`); load() }
    catch (e) { notify(e.message, 'red') }
  }

  return (
    <div>
      {showAdd && <AddHostModal onClose={() => setShowAdd(false)} onAdded={load} notify={notify} />}
      <div className="summary-row">
        <div className="stat-card amber"><div className="stat-label">Pending Updates</div><div className="stat-val">{pending}</div><div className="stat-sub">across {hosts.filter(h => h.pending_count > 0).length} hosts</div></div>
        <div className="stat-card green"><div className="stat-label">Up to Date</div><div className="stat-val">{upToDate}</div><div className="stat-sub">no action needed</div></div>
        <div className="stat-card red"><div className="stat-label">Reboot Required</div><div className="stat-val">{rebootReq}</div><div className="stat-sub">kernel updates</div></div>
        <div className="stat-card blue"><div className="stat-label">Total Hosts</div><div className="stat-val">{hosts.length}</div><div className="stat-sub">{hosts.filter(h => h.status === 'online').length} online</div></div>
      </div>
      <div className="sec-head">
        <span className="sec-title">Host Patch Queue</span>
        <div className="sec-actions">
          <button className="btn" onClick={() => { notify('Queuing checks for all hosts...'); hosts.forEach(h => api.checkHost(h.id).catch(() => {})); setTimeout(load, 3000) }}>↻ Check All</button>
          <button className="btn primary" onClick={() => setShowAdd(true)}>+ Add Host</button>
        </div>
      </div>
      <div className="tbl-wrap">
        <div className="tbl-head patch-cols"><span>Hostname</span><span>OS / Pkg Mgr</span><span>Pending</span><span>Status</span><span>Actions</span></div>
        {loading && <div className="empty">Loading hosts...</div>}
        {!loading && hosts.length === 0 && <div className="empty">No hosts yet — click + Add Host to get started</div>}
        {hosts.map(h => (
          <div className="tbl-row patch-cols" key={h.id}>
            <span className="hostname">{h.hostname}</span>
            <span className="os-tag">{h.os_name || 'Unknown'} · {h.pkg_manager || '?'}</span>
            <span className={h.pending_count > 0 ? 'pkg-count-n' : 'pkg-count-z'}>{h.pending_count}</span>
            <span>{patchBadge(h)}</span>
            <span style={{ display: 'flex', gap: 4 }}>
              <button className="btn" title="Refresh" onClick={() => doCheck(h)} style={{ padding: '3px 7px' }}>↻</button>
              <button className="btn primary" onClick={() => doPatch(h, false)} disabled={busy[h.id] || h.pending_count === 0}>{busy[h.id] ? '...' : 'Patch'}</button>
              <button className="btn" onClick={() => doPatch(h, true)} disabled={busy[h.id]} title="Dry run">DRY</button>
              <button className="btn danger" onClick={() => doDelete(h)} style={{ padding: '3px 7px' }} title="Remove">✕</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Docker Panel ─────────────────────────────────────────────────────────────
function DockerPanel({ notify, onAuthError }) {
  const [containers, setContainers] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setContainers(await api.docker()) }
    catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
    finally { setLoading(false) }
  }, [notify, onAuthError])

  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t) }, [load])

  const running = containers.filter(c => c.state === 'running').length
  const stopped = containers.filter(c => c.state !== 'running').length
  const outdated = containers.filter(c => c.is_outdated).length
  const hostCount = [...new Set(containers.map(c => c.hostname))].length

  function stateBadge(c) {
    if (c.state === 'running' && c.is_outdated) return <span className="badge amber">⚠ outdated</span>
    if (c.state === 'running') return <span className="badge green">● running</span>
    if (c.state === 'paused') return <span className="badge amber">⏸ paused</span>
    if (c.state === 'restarting') return <span className="badge blue">↻ restarting</span>
    return <span className="badge red">■ stopped</span>
  }

  return (
    <div>
      <div className="summary-row">
        <div className="stat-card green"><div className="stat-label">Running</div><div className="stat-val">{running}</div><div className="stat-sub">containers</div></div>
        <div className="stat-card red"><div className="stat-label">Stopped</div><div className="stat-val">{stopped}</div><div className="stat-sub">not running</div></div>
        <div className="stat-card amber"><div className="stat-label">Outdated Images</div><div className="stat-val">{outdated}</div><div className="stat-sub">digest mismatch</div></div>
        <div className="stat-card blue"><div className="stat-label">Hosts w/ Docker</div><div className="stat-val">{hostCount}</div><div className="stat-sub">monitored</div></div>
      </div>
      <div className="sec-head">
        <span className="sec-title">Container Inventory</span>
        <button className="btn primary" onClick={() => { notify('Docker scan queued...'); api.dockerScan().then(() => setTimeout(load, 5000)).catch(e => notify(e.message, 'red')) }}>↻ Scan All</button>
      </div>
      <div className="tbl-wrap">
        <div className="tbl-head docker-cols"><span>Container</span><span>Image</span><span>State</span><span>Host</span><span>Checked</span></div>
        {loading && <div className="empty">Loading containers...</div>}
        {!loading && containers.length === 0 && <div className="empty">No containers found. Add hosts with Docker installed, then run a scan.</div>}
        {containers.map(c => (
          <div className="tbl-row docker-cols" key={c.id}>
            <span className="hostname">{c.name}</span>
            <span className="os-tag" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.image}</span>
            <span>{stateBadge(c)}</span>
            <span className="os-tag">{c.hostname}</span>
            <span className="os-tag">{fmtAgo(c.updated_at)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Proxmox Panel ────────────────────────────────────────────────────────────
function ProxmoxPanel({ notify, onAuthError }) {
  const [guests, setGuests] = useState([])
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const s = await api.proxmoxStatus()
      setStatus(s)
      if (s.configured) setGuests(await api.proxmoxGuests())
    } catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
    finally { setLoading(false) }
  }, [notify, onAuthError])

  useEffect(() => { load() }, [load])

  const vms = guests.filter(g => g.type === 'qemu').length
  const lxcs = guests.filter(g => g.type === 'lxc').length
  const running = guests.filter(g => g.status === 'running').length

  return (
    <div>
      <div className="summary-row">
        <div className="stat-card blue"><div className="stat-label">Total VMs</div><div className="stat-val">{vms}</div><div className="stat-sub">QEMU instances</div></div>
        <div className="stat-card green"><div className="stat-label">LXC Containers</div><div className="stat-val">{lxcs}</div><div className="stat-sub">auto-enrolled</div></div>
        <div className="stat-card green"><div className="stat-label">Running</div><div className="stat-val">{running}</div><div className="stat-sub">of {guests.length} total</div></div>
        <div className={`stat-card ${status?.configured ? 'green' : 'red'}`}>
          <div className="stat-label">PVE Status</div>
          <div className="stat-val" style={{ fontSize: 14, marginTop: 4 }}>{status?.configured ? 'Linked' : 'Not Set'}</div>
          <div className="stat-sub">{status?.configured ? 'API connected' : 'Set env vars'}</div>
        </div>
      </div>

      {!status?.configured && (
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 14, marginBottom: 16 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text)', marginBottom: 6, fontWeight: 500 }}>Proxmox Not Configured</div>
          <div style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 8 }}>Add these to your <code style={{ color: 'var(--accent)' }}>.env</code> file and restart:</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--cyan)', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 5, padding: '8px 10px', lineHeight: 2 }}>
            PROXMOX_HOST=192.168.1.100:8006<br />
            PROXMOX_TOKEN_ID=root@pam!patchmon<br />
            PROXMOX_TOKEN_SECRET=your-token-secret<br />
            PROXMOX_NODE=pve
          </div>
        </div>
      )}

      <div className="sec-head">
        <span className="sec-title">VM / LXC Inventory</span>
        <button className="btn primary" onClick={() => { notify('Syncing...'); api.proxmoxSync().then(() => setTimeout(load, 3000)).catch(e => notify(e.message, 'red')) }} disabled={!status?.configured}>↻ Sync from PVE</button>
      </div>
      <div className="tbl-wrap">
        <div className="tbl-head" style={{ display: 'grid', gridTemplateColumns: '60px 1fr 70px 80px' }}>
          <span>VMID</span><span>Name</span><span>Type</span><span>State</span>
        </div>
        {loading && <div className="empty">Loading...</div>}
        {!loading && !status?.configured && <div className="empty">Configure Proxmox API to see guests</div>}
        {!loading && status?.configured && guests.length === 0 && <div className="empty">No guests found — run a sync</div>}
        {guests.map(g => (
          <div className="tbl-row" key={g.vmid} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 70px 80px' }}>
            <span className="os-tag">{g.vmid}</span>
            <span className="hostname">{g.name}</span>
            <span><span className={`badge ${g.type === 'lxc' ? 'cyan' : 'gray'}`}>{g.type}</span></span>
            <span><span className={`badge ${g.status === 'running' ? 'green' : 'red'}`}>{g.status === 'running' ? '● running' : '■ stopped'}</span></span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Alerts Panel ─────────────────────────────────────────────────────────────
function AlertsPanel({ notify, onAuthError }) {
  const [rules, setRules] = useState([])
  const [tgStatus, setTgStatus] = useState(null)
  const [form, setForm] = useState({ bot_token: '', chat_id: '' })
  const [connecting, setConnecting] = useState(false)

  const load = useCallback(async () => {
    try {
      const [r, t] = await Promise.all([api.alertRules(), api.telegramStatus()])
      setRules(r); setTgStatus(t)
    } catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
  }, [notify, onAuthError])

  useEffect(() => { load() }, [load])

  async function connectTg() {
    if (!form.bot_token || !form.chat_id) { notify('Token and Chat ID are required', 'red'); return }
    setConnecting(true)
    try { await api.connectTelegram(form); notify('Telegram connected — test message sent!', 'green'); load() }
    catch (e) { notify(e.message, 'red') }
    finally { setConnecting(false) }
  }

  async function toggle(rule) {
    try { await api.toggleRule(rule.id, !rule.enabled); load() }
    catch (e) { notify(e.message, 'red') }
  }

  async function testAlert(event_type) {
    try { await api.testAlert(event_type); notify(`Test alert sent: ${event_type}`, 'green') }
    catch (e) { notify(e.message, 'red') }
  }

  return (
    <div>
      <div className="tg-panel">
        <div className="tg-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 32, height: 32, background: '#1a3a4a', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>✈</div>
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 500, color: 'var(--text)' }}>Telegram Alerts</div>
              <div style={{ fontSize: 11, color: 'var(--text2)' }}>{tgStatus?.configured ? `Chat: ${tgStatus.chat_id}` : 'Not connected'}</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className={`dot ${tgStatus?.configured ? 'green' : 'red'}`}></div>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: tgStatus?.configured ? 'var(--green)' : 'var(--red)' }}>
              {tgStatus?.configured ? 'connected' : 'disconnected'}
            </span>
          </div>
        </div>

        {!tgStatus?.configured && (
          <div style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 8, padding: 12, marginBottom: 14 }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text)', marginBottom: 8, fontWeight: 500 }}>Connect Telegram Bot</div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <div style={{ flex: 3 }}>
                <div className="form-label">Bot Token</div>
                <input className="inp" value={form.bot_token} onChange={e => setForm(f => ({ ...f, bot_token: e.target.value }))} placeholder="7823456789:AAF..." />
              </div>
              <div style={{ flex: 1 }}>
                <div className="form-label">Chat ID</div>
                <input className="inp" value={form.chat_id} onChange={e => setForm(f => ({ ...f, chat_id: e.target.value }))} placeholder="-100..." />
              </div>
            </div>
            <button className="btn primary" onClick={connectTg} disabled={connecting}>
              {connecting ? 'Connecting...' : 'Connect & Send Test'}
            </button>
          </div>
        )}

        <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 8 }}>Alert Rules</div>
        {rules.map(r => (
          <div className="tg-row" key={r.id}>
            <div className="tg-info">
              <div className="tg-name">{r.name}</div>
              <div className="tg-desc">{r.description}</div>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="btn" style={{ padding: '2px 8px', fontSize: 10 }} onClick={() => testAlert(r.event_type)}>Test</button>
              <label className="tog">
                <input type="checkbox" checked={r.enabled} onChange={() => toggle(r)} />
                <div className="tog-track"></div>
                <div className="tog-thumb"></div>
              </label>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Log Panel ────────────────────────────────────────────────────────────────
function LogPanel({ notify, onAuthError }) {
  const [logs, setLogs] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [l, s] = await Promise.all([api.logs(200), api.logSummary()])
      setLogs(l); setSummary(s)
    } catch (e) { if (e.status === 401) onAuthError(); else notify(e.message, 'red') }
    finally { setLoading(false) }
  }, [notify, onAuthError])

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t) }, [load])

  return (
    <div>
      {summary && (
        <div className="summary-row">
          <div className="stat-card green"><div className="stat-label">Success 24h</div><div className="stat-val">{summary.ok}</div><div className="stat-sub">completed jobs</div></div>
          <div className="stat-card red"><div className="stat-label">Errors</div><div className="stat-val">{summary.error}</div><div className="stat-sub">last 24h</div></div>
          <div className="stat-card amber"><div className="stat-label">Warnings</div><div className="stat-val">{summary.warn}</div><div className="stat-sub">last 24h</div></div>
          <div className="stat-card blue"><div className="stat-label">Total Events</div><div className="stat-val">{summary.total_24h}</div><div className="stat-sub">last 24h</div></div>
        </div>
      )}
      <div className="sec-head">
        <span className="sec-title">Audit Log</span>
        <button className="btn" onClick={() => api.exportLogs()}>↓ Export CSV</button>
      </div>
      <div className="log-panel">
        <div style={{ display: 'grid', gridTemplateColumns: '90px 40px 1fr', padding: '8px 14px', borderBottom: '1px solid var(--border)', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.5px' }}>
          <span>Time</span><span>Lvl</span><span>Event</span>
        </div>
        <div className="log-body" style={{ maxHeight: 400 }}>
          {loading && <div style={{ color: 'var(--text3)' }}>Loading...</div>}
          {!loading && logs.length === 0 && <div style={{ color: 'var(--text3)' }}>No log entries yet</div>}
          {logs.map(l => (
            <div className="log-line" key={l.id}>
              <span className="log-ts">{fmtTime(l.created_at)}</span>
              <span className={`log-lvl ${l.level}`}>{l.level}</span>
              <span className="log-msg">
                {l.hostname && <b style={{ color: 'var(--text)' }}>{l.hostname} — </b>}
                {l.event}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── App Shell ────────────────────────────────────────────────────────────────
const PANELS = {
  patch:   { icon: '⬡', title: 'Patch Management' },
  docker:  { icon: '▣', title: 'Docker Monitor' },
  proxmox: { icon: '⬢', title: 'Proxmox Integration' },
  alerts:  { icon: '✉', title: 'Telegram Alerts' },
  log:     { icon: '≡', title: 'Audit Log' },
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(auth.isLoggedIn())
  const [panel, setPanel] = useState('patch')
  const [stats, setStats] = useState(null)
  const { toasts, notify, remove } = useToast()

  // Force back to login if any request returns 401
  const onAuthError = useCallback(() => {
    auth.clearToken()
    setLoggedIn(false)
    setStats(null)
  }, [])

  // Poll stats
  useEffect(() => {
    if (!loggedIn) return
    const fetchStats = () => api.stats().then(setStats).catch(e => { if (e.status === 401) onAuthError() })
    fetchStats()
    const t = setInterval(fetchStats, 30000)
    return () => clearInterval(t)
  }, [loggedIn, onAuthError])

  if (!loggedIn) {
    return (
      <>
        <style>{S}</style>
        <LoginScreen onLogin={() => setLoggedIn(true)} />
        {toasts.map(t => <Toast key={t.id} msg={t.msg} type={t.type} onDone={() => remove(t.id)} />)}
      </>
    )
  }

  const panelProps = { notify, onAuthError }

  return (
    <>
      <style>{S}</style>
      <div className="shell">
        <div className="sidebar">
          <div className="logo">PM</div>
          {Object.entries(PANELS).map(([key, p]) => (
            <button
              key={key}
              className={`nav-icon ${panel === key ? 'active' : ''}`}
              onClick={() => setPanel(key)}
              title={p.title}
            >
              {p.icon}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button
            className="nav-icon"
            title="Sign out"
            onClick={() => { auth.clearToken(); setLoggedIn(false) }}
            style={{ fontSize: 14 }}
          >
            ⏻
          </button>
        </div>

        <div className="main">
          <div className="topbar">
            <span className="topbar-title"><b>{PANELS[panel].title}</b></span>
            {stats && (
              <>
                <div className="tb-badge">
                  <div className={`dot ${stats.hosts_online > 0 ? 'green' : 'gray'}`} />
                  {stats.hosts_online}/{stats.hosts_total} hosts online
                </div>
                {stats.pending_updates > 0 && (
                  <div className="tb-badge"><div className="dot amber" />{stats.pending_updates} pending</div>
                )}
                {stats.outdated_containers > 0 && (
                  <div className="tb-badge"><div className="dot amber" />{stats.outdated_containers} docker outdated</div>
                )}
              </>
            )}
          </div>

          <div className="content">
            {panel === 'patch'   && <PatchPanel   {...panelProps} />}
            {panel === 'docker'  && <DockerPanel  {...panelProps} />}
            {panel === 'proxmox' && <ProxmoxPanel {...panelProps} />}
            {panel === 'alerts'  && <AlertsPanel  {...panelProps} />}
            {panel === 'log'     && <LogPanel     {...panelProps} />}
          </div>
        </div>
      </div>

      {toasts.map(t => <Toast key={t.id} msg={t.msg} type={t.type} onDone={() => remove(t.id)} />)}
    </>
  )
}
