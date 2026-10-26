import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Bell,
  Check, ChevronDown, CircleHelp, Clock3, Command, Cpu, Database, FileSearch,
  Filter, Gauge, GitBranch, LayoutDashboard, LifeBuoy, Menu, Moon, MoreHorizontal,
  Network, Search, Settings2, ShieldCheck, Sun, Terminal, Zap
} from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const fallbackIncidents = [
  { id: 'INC-2048', title: 'Checkout requests timing out', service: 'checkout-api', severity: 'Critical', status: 'Investigating', age: '4 min ago', errors: 148, affected: 3, summary: 'Elevated checkout latency following a rise in database connection errors.' },
  { id: 'INC-2047', title: 'Inventory sync lag', service: 'inventory-worker', severity: 'High', status: 'Monitoring', age: '18 min ago', errors: 62, affected: 2, summary: 'Worker queue depth is above its normal range; delayed stock updates reported.' },
  { id: 'INC-2046', title: 'Authentication retry spike', service: 'auth-gateway', severity: 'Medium', status: 'Resolved', age: '52 min ago', errors: 31, affected: 1, summary: 'A short burst of upstream retries caused intermittent sign-in failures.' },
  { id: 'INC-2045', title: 'Search index freshness degraded', service: 'search-indexer', severity: 'Low', status: 'Monitoring', age: '1 hr ago', errors: 19, affected: 2, summary: 'Indexing throughput is below target after a batch processing delay.' },
]
const chartData = [
  { time: '14:00', errors: 12, latency: 24 }, { time: '14:05', errors: 16, latency: 28 },
  { time: '14:10', errors: 14, latency: 31 }, { time: '14:15', errors: 29, latency: 42 },
  { time: '14:20', errors: 44, latency: 58 }, { time: '14:25', errors: 82, latency: 75 },
  { time: '14:30', errors: 118, latency: 88 }, { time: '14:35', errors: 148, latency: 96 },
  { time: '14:40', errors: 132, latency: 91 }, { time: '14:45', errors: 109, latency: 84 },
]
const timeline = [
  { time: '14:02:11', level: 'warn', service: 'database-pool', text: 'Connection pool usage reached 91%', detail: 'pool_active=46 · pool_max=50' },
  { time: '14:03:04', level: 'error', service: 'checkout-api', text: 'Request exceeded upstream timeout', detail: 'duration_ms=5000 · route=/api/checkout' },
  { time: '14:03:29', level: 'error', service: 'payment-worker', text: 'Payment attempt scheduled for retry', detail: 'retry_count=3 · order_batch=checkout-7' },
  { time: '14:04:02', level: 'warn', service: 'inventory-api', text: 'Dependency response time above threshold', detail: 'p95_ms=1840 · threshold_ms=900' },
]

function IconButton({ title, children, onClick, className = '' }) {
  return <button className={`icon-button ${className}`} title={title} aria-label={title} onClick={onClick}>{children}</button>
}
function Pill({ children, tone = 'neutral' }) { return <span className={`pill pill-${tone}`}>{children}</span> }
function SectionTitle({ eyebrow, title, action }) { return <div className="section-title"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2></div>{action}</div> }

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('tracewise-theme') || 'dark')
  const [incidents, setIncidents] = useState(fallbackIncidents)
  const [activeId, setActiveId] = useState('INC-2048')
  const [page, setPage] = useState('Overview')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All incidents')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [apiState, setApiState] = useState('checking')
  const [toast, setToast] = useState('')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('tracewise-theme', theme)
  }, [theme])
  useEffect(() => {
    fetch('/api/health').then(r => { if (!r.ok) throw new Error(); return r.json() }).then(() => setApiState('connected')).catch(() => setApiState('demo'))
    fetch('/api/incidents').then(r => r.ok ? r.json() : Promise.reject()).then(data => { if (Array.isArray(data) && data.length) setIncidents(data) }).catch(() => {})
  }, [])
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 2800); return () => clearTimeout(timer) }, [toast])

  const activeIncident = incidents.find(i => i.id === activeId) || incidents[0]
  const visibleIncidents = useMemo(() => incidents.filter(i => {
    const matchesText = `${i.id} ${i.title} ${i.service}`.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'All incidents' || i.severity === filter || i.status === filter
    return matchesText && matchesFilter
  }), [incidents, search, filter])

  async function runAnalysis() {
    setAnalyzing(true); setAnalysis(null)
    try {
      const response = await fetch(`/api/incidents/${activeId}/analyze`, { method: 'POST' })
      if (!response.ok) throw new Error('API unavailable')
      setAnalysis(await response.json())
    } catch {
      setAnalysis({
        incident_id: activeId, method: 'Local heuristic baseline',
        disclaimer: 'Demo analysis generated from bundled example signals. Connect the Python API to run the full analysis pipeline.',
        hypotheses: [
          { rank: 1, cause: 'Database connection pool exhaustion', score: 0.82, confidence: 'Moderate', evidence: ['Connection pool usage reached 91% before checkout timeouts.', 'Checkout failures increased shortly after pool saturation.'], counter_evidence: ['No direct database restart or saturation event is present in this sample.'], next_check: 'Inspect active connections, pool wait time, and slow-query logs.' },
          { rank: 2, cause: 'Upstream payment retry amplification', score: 0.61, confidence: 'Low–moderate', evidence: ['Payment retries increased after checkout timeouts began.'], counter_evidence: ['Retry events occur after the first checkout timeout, so they may be a consequence.'], next_check: 'Compare retry policy, retry count, and request rate before the incident.' },
          { rank: 3, cause: 'Inventory API latency', score: 0.43, confidence: 'Low', evidence: ['Inventory dependency latency rose during the incident window.'], counter_evidence: ['The latency signal appears later than the first connection-pool warning.'], next_check: 'Review inventory service traces and dependency latency baseline.' },
        ]
      })
    } finally { setAnalyzing(false); setPage('Investigation') }
  }

  const navItems = [
    { label: 'Overview', icon: LayoutDashboard }, { label: 'Incidents', icon: AlertTriangle, count: '04' },
    { label: 'Service map', icon: Network }, { label: 'Evidence explorer', icon: FileSearch },
    { label: 'Research lab', icon: Gauge },
  ]
  function selectNav(label) { setPage(label); setSidebarOpen(false) }

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Activity size={21} strokeWidth={2.6}/></div><div><div className="brand-name">tracewise<span>·</span></div><div className="brand-sub">INCIDENT INTELLIGENCE</div></div><IconButton title="Close menu" className="mobile-close" onClick={() => setSidebarOpen(false)}>×</IconButton></div>
      <div className="workspace-switch"><div className="workspace-icon">N</div><div className="workspace-copy"><strong>Northstar Systems</strong><span>Personal workspace</span></div><ChevronDown size={15}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="main-nav">{navItems.map(({ label, icon: Icon, count }) => <button key={label} className={`nav-item ${page === label ? 'active' : ''}`} onClick={() => selectNav(label)}><Icon size={18}/><span>{label}</span>{count && <span className="nav-count">{count}</span>}</button>)}</nav>
      <div className="nav-label tools-label">TOOLS</div>
      <nav className="main-nav"><button className={`nav-item ${page === 'Logs' ? 'active' : ''}`} onClick={() => selectNav('Logs')}><Terminal size={18}/><span>Log explorer</span></button><button className={`nav-item ${page === 'Settings' ? 'active' : ''}`} onClick={() => selectNav('Settings')}><Settings2 size={18}/><span>Settings</span></button></nav>
      <div className="sidebar-spacer"/>
      <div className="research-card"><div className="research-icon"><Zap size={16}/></div><div className="research-card-title">Research prototype</div><p>Evidence first. Confidence second. Never guess silently.</p><button onClick={() => selectNav('Research lab')}>Explore methodology <ArrowRight size={14}/></button></div>
      <div className="sidebar-bottom"><div className="avatar">AK</div><div className="user-copy"><strong>Research workspace</strong><span>Local environment</span></div><MoreHorizontal size={18} className="muted-icon"/></div>
    </aside>

    <main className="main-content">
      <header className="topbar"><div className="topbar-left"><IconButton title="Open navigation" className="menu-button" onClick={() => setSidebarOpen(true)}><Menu size={19}/></IconButton><div className="breadcrumb">Workspace <span>/</span> <strong>{page}</strong></div></div><div className="topbar-actions"><div className={`connection-status ${apiState === 'connected' ? 'connected' : ''}`}><span className="status-dot"/>{apiState === 'connected' ? 'API connected' : apiState === 'demo' ? 'Demo mode' : 'Connecting'}</div><div className="topbar-divider"/><IconButton title="Search incidents" onClick={() => document.querySelector('.search-input')?.focus()}><Search size={18}/></IconButton><IconButton title="Notifications" onClick={() => setToast('You’re all caught up.')}><Bell size={18}/><i className="notification-dot"/></IconButton><IconButton title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}</IconButton><div className="top-avatar">A</div></div></header>

      {page === 'Overview' && <div className="page-wrap">
        <div className="page-heading"><div><div className="eyebrow heading-eyebrow"><span className="live-dot"/> SYSTEM OVERVIEW <span className="heading-date">/ OCT 18, 2026</span></div><h1>Good evening, <span>researcher.</span></h1><p className="page-description">Here’s what’s happening across your services today.</p></div><button className="primary-button" onClick={() => { setActiveId('INC-2048'); runAnalysis() }}><Zap size={16}/> Investigate incident</button></div>
        <div className="metrics-grid">
          <MetricCard label="Active incidents" value="04" delta="2 need attention" icon={AlertTriangle} accent="orange" trend="up"/>
          <MetricCard label="Services monitored" value="12" delta="All systems reporting" icon={GitBranch} accent="blue" trend="flat"/>
          <MetricCard label="Mean time to detect" value="2.4m" delta="18% faster this week" icon={Clock3} accent="green" trend="down"/>
          <MetricCard label="Evidence coverage" value="86.2%" delta="Across current incidents" icon={ShieldCheck} accent="purple" trend="up"/>
        </div>
        <div className="overview-grid">
          <section className="panel activity-panel"><div className="panel-header"><div><div className="eyebrow">TELEMETRY</div><h2>Incident activity</h2></div><button className="select-button" onClick={() => setToast('Showing the last 45 minutes.')}>Last 45 minutes <ChevronDown size={14}/></button></div><div className="chart-legend"><span><i className="legend-dot legend-orange"/> Error events</span><span><i className="legend-dot legend-blue"/> Latency index</span><span className="chart-current"><span className="live-dot"/> Live sample</span></div><div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}><defs><linearGradient id="errorFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f59e61" stopOpacity={0.22}/><stop offset="100%" stopColor="#f59e61" stopOpacity={0}/></linearGradient><linearGradient id="latencyFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7b9cff" stopOpacity={0.16}/><stop offset="100%" stopColor="#7b9cff" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="var(--grid)" vertical={false}/><XAxis dataKey="time" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false} dy={8}/><YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)', fontSize: 12 }} /><Area type="monotone" dataKey="errors" stroke="#f59e61" strokeWidth={2.2} fill="url(#errorFill)"/><Area type="monotone" dataKey="latency" stroke="#7b9cff" strokeWidth={2} fill="url(#latencyFill)"/></AreaChart></ResponsiveContainer></div><div className="chart-footnote"><span><span className="footnote-dot"/> Peak activity at 14:35</span><span>Illustrative telemetry · not live production data</span></div></section>
          <section className="panel health-panel"><div className="panel-header"><div><div className="eyebrow">INFRASTRUCTURE</div><h2>Service health</h2></div><IconButton title="Service health details" onClick={() => selectNav('Service map')}><ArrowUpRight size={17}/></IconButton></div><div className="health-score-row"><div><div className="health-score">98.4<span>%</span></div><div className="health-sub">Overall availability</div></div><Pill tone="success"><span className="tiny-dot"/> Healthy</Pill></div><div className="health-bar"><span/></div><div className="service-list">{[{name:'API Gateway',status:'Operational',latency:'42 ms',tone:'success',width:'82%'},{name:'Checkout API',status:'Degraded',latency:'1.8 s',tone:'warning',width:'37%'},{name:'Database Pool',status:'Under pressure',latency:'240 ms',tone:'warning',width:'90%'},{name:'Payment Worker',status:'Operational',latency:'86 ms',tone:'success',width:'72%'}].map(s=><div className="service-row" key={s.name}><span className={`service-symbol ${s.tone}`}><Activity size={14}/></span><div className="service-name-wrap"><strong>{s.name}</strong><div className="mini-progress"><span className={s.tone} style={{width:s.width}}/></div></div><div className="service-latency"><strong>{s.latency}</strong><span>{s.status}</span></div></div>)}</div><button className="text-button full-button" onClick={() => selectNav('Service map')}>View service map <ArrowRight size={15}/></button></section>
        </div>
        <section className="panel incidents-panel"><div className="panel-header incident-header"><div><div className="eyebrow">NEEDS ATTENTION</div><h2>Recent incidents <span className="subtle-count">04</span></h2></div><button className="text-button" onClick={() => selectNav('Incidents')}>View all incidents <ArrowRight size={15}/></button></div><div className="table-tools"><div className="search-box"><Search size={16}/><input className="search-input" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search incidents or services…"/></div><select className="filter-select" value={filter} onChange={e => setFilter(e.target.value)}><option>All incidents</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option><option>Investigating</option><option>Monitoring</option><option>Resolved</option></select><button className="filter-button" onClick={() => {setSearch('');setFilter('All incidents')}}><Filter size={15}/> Reset</button></div><div className="incident-table-wrap"><table className="incident-table"><thead><tr><th>INCIDENT</th><th>SERVICE</th><th>SEVERITY</th><th>STATUS</th><th>EVENTS</th><th>LAST SEEN</th><th/></tr></thead><tbody>{visibleIncidents.map(i=><tr key={i.id} className={activeId === i.id ? 'selected-row' : ''} onClick={() => {setActiveId(i.id);setPage('Investigation')}}><td><div className="incident-id">{i.id}</div><div className="incident-title">{i.title}</div></td><td><span className="service-code">{i.service}</span></td><td><Pill tone={i.severity.toLowerCase()}><span className="tiny-dot"/>{i.severity}</Pill></td><td><span className="status-text"><span className={`status-dot ${i.status === 'Resolved' ? 'resolved' : i.status === 'Monitoring' ? 'monitoring' : ''}`}/>{i.status}</span></td><td className="event-count">{i.errors}</td><td className="last-seen">{i.age}</td><td><IconButton title={`Investigate ${i.id}`} onClick={e => {e?.stopPropagation?.();setActiveId(i.id);setPage('Investigation')}}><ArrowUpRight size={16}/></IconButton></td></tr>)}</tbody></table>{visibleIncidents.length === 0 && <div className="empty-state">No incidents match those filters.</div>}</div><div className="table-footer"><span>Showing <strong>{visibleIncidents.length}</strong> of {incidents.length} incidents</span><span className="footer-note"><ShieldCheck size={14}/> Evidence is traceable by design</span></div></section>
        <footer className="page-footer"><span>TRACEWISE AI <span className="footer-separator">/</span> RESEARCH PROTOTYPE</span><span>Built for explainable incident investigation <span className="footer-separator">·</span> v0.1.0</span></footer>
      </div>}

      {page === 'Investigation' && <InvestigationPage incident={activeIncident} analysis={analysis} analyzing={analyzing} onAnalyze={runAnalysis} onBack={() => setPage('Overview')} />}
      {page === 'Incidents' && <IncidentsPage incidents={visibleIncidents} search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} onSelect={id => {setActiveId(id);setPage('Investigation')}} />}
      {page === 'Service map' && <ServiceMapPage onInvestigate={() => {setActiveId('INC-2048');setPage('Investigation')}} />}
      {page === 'Evidence explorer' && <EvidencePage />}
      {page === 'Research lab' && <ResearchPage />}
      {page === 'Logs' && <LogsPage />}
      {page === 'Settings' && <SettingsPage theme={theme} setTheme={setTheme} apiState={apiState} />}
    </main>
    {sidebarOpen && <button className="mobile-overlay" aria-label="Close menu" onClick={() => setSidebarOpen(false)}/>}
    {toast && <div className="toast"><Check size={16}/>{toast}</div>}
  </div>
}

function MetricCard({label,value,delta,icon:Icon,accent,trend}) { return <div className="metric-card"><div className="metric-top"><span>{label}</span><span className={`metric-icon ${accent}`}><Icon size={17}/></span></div><div className="metric-value">{value}</div><div className="metric-bottom"><span className={`metric-trend ${trend === 'up' && accent === 'orange' ? 'trend-warning' : ''}`}>{trend === 'down' ? <ArrowDownRight size={14}/> : trend === 'up' ? <ArrowUpRight size={14}/> : <span className="trend-line"/>}{delta}</span></div></div> }

function InvestigationPage({incident,analysis,analyzing,onAnalyze,onBack}) {
  const hypotheses = analysis?.hypotheses || []
  return <div className="page-wrap subpage"><div className="back-row"><button className="text-button" onClick={onBack}>← Back to overview</button><span className="breadcrumb-mini">/ Investigation workspace</span></div><div className="page-heading"><div><div className="eyebrow heading-eyebrow">INCIDENT INVESTIGATION <span className="heading-date">/ {incident?.id}</span></div><h1>{incident?.title || 'Incident investigation'}</h1><p className="page-description">{incident?.summary || 'Inspect evidence and evaluate possible root causes.'}</p></div><button className="primary-button" onClick={onAnalyze} disabled={analyzing}>{analyzing ? <><span className="spinner"/> Analyzing…</> : <><Zap size={16}/> Run analysis</>}</button></div>
    <div className="investigation-summary"><div><span className="summary-label">SERVICE</span><strong>{incident?.service}</strong></div><div><span className="summary-label">SEVERITY</span><Pill tone={(incident?.severity || 'medium').toLowerCase()}>{incident?.severity}</Pill></div><div><span className="summary-label">EVENTS OBSERVED</span><strong>{incident?.errors}</strong></div><div><span className="summary-label">AFFECTED SERVICES</span><strong>{incident?.affected}</strong></div><div><span className="summary-label">STATUS</span><strong><span className="status-dot"/> {incident?.status}</strong></div></div>
    <div className="investigation-grid"><section className="panel"><div className="panel-header"><div><div className="eyebrow">ROOT-CAUSE ANALYSIS</div><h2>Candidate explanations</h2></div><Pill tone="neutral">Ranked</Pill></div>{!analysis && !analyzing && <div className="analysis-empty"><div className="empty-illustration"><FileSearch size={27}/></div><h3>Ready to investigate</h3><p>Run the analysis to rank possible causes and inspect the evidence behind each hypothesis.</p><button className="primary-button" onClick={onAnalyze}><Zap size={15}/> Analyze incident</button><span className="muted-small">Local baseline · no external API required</span></div>}{analyzing && <div className="analysis-empty"><div className="spinner large-spinner"/><h3>Connecting the evidence</h3><p>Correlating timestamps, service relationships, and incident signals…</p></div>}{analysis && <><div className="method-note"><ShieldCheck size={15}/><span>{analysis.method}</span><span className="method-separator">·</span><span>Evidence-linked</span></div>{hypotheses.map(h=><div className="hypothesis-card" key={h.rank}><div className="hypothesis-top"><span className="rank-badge">#{h.rank}</span><div className="hypothesis-name"><h3>{h.cause}</h3><span>{h.confidence} confidence</span></div><div className="score-wrap"><strong>{Math.round(h.score*100)}<small>%</small></strong><span>relative score</span></div></div><div className="score-track"><span style={{width:`${h.score*100}%`}}/></div><div className="evidence-columns"><div><div className="evidence-heading positive"><Check size={14}/> SUPPORTING EVIDENCE</div>{h.evidence.map((e,i)=><p className="evidence-line" key={i}>{e}</p>)}</div><div><div className="evidence-heading caution"><AlertTriangle size={14}/> COUNTER-EVIDENCE</div>{h.counter_evidence.map((e,i)=><p className="evidence-line" key={i}>{e}</p>)}</div></div><div className="next-check"><Search size={14}/><span><strong>Next check:</strong> {h.next_check}</span></div></div>)}<div className="disclaimer"><CircleHelp size={15}/>{analysis.disclaimer || 'Scores are relative ranking scores, not calibrated probabilities. Validate the hypothesis against system evidence.'}</div></>}</section>
    <div className="right-stack"><section className="panel"><div className="panel-header"><div><div className="eyebrow">EVENT CORRELATION</div><h2>Incident timeline</h2></div><span className="small-counter">4 events</span></div><div className="timeline">{timeline.map((item,i)=><div className="timeline-item" key={item.time}><div className={`timeline-marker ${item.level}`}/><div className="timeline-content"><div className="timeline-meta"><span>{item.time}</span><span className={`log-level ${item.level}`}>{item.level.toUpperCase()}</span></div><strong>{item.text}</strong><span className="timeline-service">{item.service}</span><code>{item.detail}</code></div></div>)}</div><div className="panel-bottom-note">Illustrative incident data · source timestamps retained</div></section><section className="panel next-steps-panel"><div className="panel-header"><div><div className="eyebrow">INVESTIGATION GUIDE</div><h2>Suggested next steps</h2></div><LifeBuoy size={17} className="muted-icon"/></div><div className="checklist-item"><span className="step-number">01</span><div><strong>Inspect database pool saturation</strong><p>Compare active connections against configured capacity around 14:02.</p></div></div><div className="checklist-item"><span className="step-number">02</span><div><strong>Review checkout traces</strong><p>Identify the first slow dependency on the failing request path.</p></div></div><div className="checklist-item"><span className="step-number">03</span><div><strong>Check retry amplification</strong><p>Verify retry policy and whether retries increased downstream load.</p></div></div></section></div></div><footer className="page-footer"><span>TRACEWISE AI <span className="footer-separator">/</span> INVESTIGATION</span><span>Always verify before acting</span></footer></div>
}

function IncidentsPage({incidents,search,setSearch,filter,setFilter,onSelect}) { return <div className="page-wrap subpage"><div className="page-heading"><div><div className="eyebrow heading-eyebrow">OPERATIONS</div><h1>Incident <span>registry.</span></h1><p className="page-description">Search, filter, and open incidents for evidence-based investigation.</p></div></div><section className="panel incidents-panel"><div className="table-tools"><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search incidents or services…"/></div><select className="filter-select" value={filter} onChange={e=>setFilter(e.target.value)}><option>All incidents</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option><option>Investigating</option><option>Monitoring</option><option>Resolved</option></select></div><div className="incident-table-wrap"><table className="incident-table"><thead><tr><th>INCIDENT</th><th>SERVICE</th><th>SEVERITY</th><th>STATUS</th><th>EVENTS</th><th>LAST SEEN</th><th/></tr></thead><tbody>{incidents.map(i=><tr key={i.id} onClick={()=>onSelect(i.id)}><td><div className="incident-id">{i.id}</div><div className="incident-title">{i.title}</div></td><td><span className="service-code">{i.service}</span></td><td><Pill tone={i.severity.toLowerCase()}>{i.severity}</Pill></td><td>{i.status}</td><td>{i.errors}</td><td>{i.age}</td><td><ArrowUpRight size={16}/></td></tr>)}</tbody></table>{!incidents.length&&<div className="empty-state">No incidents found.</div>}</div></section></div> }

function ServiceMapPage({onInvestigate}) { const nodes=[{name:'API Gateway',x:50,y:12,status:'ok'},{name:'Checkout API',x:27,y:43,status:'bad'},{name:'Inventory API',x:73,y:43,status:'warn'},{name:'Database Pool',x:27,y:77,status:'warn'},{name:'Payment Worker',x:73,y:77,status:'ok'}];return <div className="page-wrap subpage"><div className="page-heading"><div><div className="eyebrow heading-eyebrow">DEPENDENCY GRAPH</div><h1>Service <span>map.</span></h1><p className="page-description">Explore service relationships and the possible paths through an incident.</p></div><button className="primary-button" onClick={onInvestigate}><FileSearch size={16}/> Investigate checkout</button></div><div className="service-map-layout"><section className="panel map-panel"><div className="panel-header"><div><div className="eyebrow">12 SERVICES · SAMPLE TOPOLOGY</div><h2>Dependency overview</h2></div><Pill tone="warning">2 degraded</Pill></div><div className="map-canvas"><svg className="map-edges" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="50" y1="18" x2="27" y2="39"/><line x1="50" y1="18" x2="73" y2="39"/><line x1="27" y1="49" x2="27" y2="72"/><line x1="73" y1="49" x2="73" y2="72"/><line x1="33" y1="47" x2="67" y2="47" strokeDasharray="2 2"/></svg>{nodes.map(n=><div key={n.name} className={`service-node node-${n.status}`} style={{left:`${n.x}%`,top:`${n.y}%`}}><div className="node-icon"><Activity size={18}/></div><strong>{n.name}</strong><span>{n.status==='ok'?'Operational':n.status==='bad'?'High latency':'Under pressure'}</span></div>)}</div><div className="map-legend"><span><i className="legend-dot legend-green"/> Operational</span><span><i className="legend-dot legend-orange"/> Degraded</span><span><i className="legend-dot legend-red"/> Incident focus</span></div></section><section className="panel"><div className="eyebrow">SELECTED PATH</div><h2>Checkout dependency</h2><p className="muted-paragraph">The sample topology suggests a path from the API gateway through checkout to its database and payment dependencies.</p><div className="path-step"><span>1</span><div><strong>API Gateway</strong><p>Incoming requests</p></div><Pill tone="success">Healthy</Pill></div><div className="path-step"><span>2</span><div><strong>Checkout API</strong><p>Request timeout signals</p></div><Pill tone="critical">Focus</Pill></div><div className="path-step"><span>3</span><div><strong>Database Pool</strong><p>Connection pressure</p></div><Pill tone="warning">Check</Pill></div><div className="map-callout"><CircleHelp size={16}/><p>Edges represent illustrative dependencies, not proof of causal relationships. Confirm the path using traces and timestamps.</p></div></section></div></div>}

function EvidencePage() { const [query,setQuery]=useState(''); const [level,setLevel]=useState('All levels'); const rows=[...timeline,{time:'14:04:21',level:'info',service:'checkout-api',text:'Elevated request queue depth detected',detail:'queue_depth=82 · baseline=14'},{time:'14:05:13',level:'warn',service:'database-pool',text:'Connection acquisition wait increased',detail:'wait_ms=1200 · p95'}];const filtered=rows.filter(r=>(`${r.service} ${r.text} ${r.detail}`.toLowerCase().includes(query.toLowerCase()))&&(level==='All levels'||r.level===level.toLowerCase()));return <div className="page-wrap subpage"><div className="page-heading"><div><div className="eyebrow heading-eyebrow">OBSERVABILITY</div><h1>Evidence <span>explorer.</span></h1><p className="page-description">Inspect the events behind a hypothesis. Every signal should be traceable to a source.</p></div></div><section className="panel"><div className="panel-header"><div><div className="eyebrow">INC-2048 · EVENT STREAM</div><h2>Correlated log events</h2></div><Pill tone="neutral">Sample data</Pill></div><div className="table-tools"><div className="search-box"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search message, service, or field…"/></div><select className="filter-select" value={level} onChange={e=>setLevel(e.target.value)}><option>All levels</option><option>ERROR</option><option>WARN</option><option>INFO</option></select></div><div className="evidence-list">{filtered.map((r,i)=><div className="evidence-row" key={`${r.time}-${i}`}><span className="evidence-time">{r.time}</span><span className={`log-level ${r.level}`}>{r.level.toUpperCase()}</span><div className="evidence-main"><strong>{r.text}</strong><span>{r.service}</span><code>{r.detail}</code></div><button className="small-outline" onClick={()=>navigator.clipboard?.writeText(`${r.time} ${r.service} ${r.text} ${r.detail}`)}>Copy event</button></div>)}{!filtered.length&&<div className="empty-state">No events match the current filters.</div>}</div><div className="disclaimer"><ShieldCheck size={15}/> Source timestamps and original fields should be preserved during real ingestion. These records are illustrative.</div></section></div>}


function ResearchPage() {
  const [noise, setNoise] = useState(0);
  const [missing, setMissing] = useState(0);
  const [ran, setRan] = useState(false);
  const [benchmark, setBenchmark] = useState(null);
  const [benchmarkLoading, setBenchmarkLoading] = useState(true);
  const [benchmarkError, setBenchmarkError] = useState("");
    const [caseSearch, setCaseSearch] = useState("");
  const [caseList, setCaseList] = useState([]);
  const [caseListLoading, setCaseListLoading] = useState(false);
  const [caseListError, setCaseListError] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [caseDetail, setCaseDetail] = useState(null);
  const [caseDetailLoading, setCaseDetailLoading] = useState(false);
  const [caseDetailError, setCaseDetailError] = useState("");


  useEffect(() => {
    let cancelled = false;

    async function loadBenchmark() {
      try {
        setBenchmarkLoading(true);
        setBenchmarkError("");

        const response = await fetch("/api/research/summary");

        if (!response.ok) {
          throw new Error(`Request failed (${response.status})`);
        }

        const data = await response.json();

        if (!cancelled) {
          setBenchmark(data);
        }
      } catch (error) {
        if (!cancelled) {
          setBenchmarkError(
            error.message || "Unable to load benchmark results."
          );
        }
      } finally {
        if (!cancelled) {
          setBenchmarkLoading(false);
        }
      }
    }

    loadBenchmark();

  const results = benchmark?.results || [];

    useEffect(() => {
    let cancelled = false;

    async function loadCases() {
      try {
        setCaseListLoading(true);
        setCaseListError("");

        const params = new URLSearchParams({
          search: caseSearch.trim(),
          limit: "25",
          offset: "0",
        });

        const response = await fetch(
          `/api/research/rcaeval/cases?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error(`Request failed (${response.status})`);
        }

        const data = await response.json();

        if (!cancelled) {
          const cases = Array.isArray(data)
            ? data
            : data.cases || data.results || [];

          setCaseList(cases);

          if (
            selectedCaseId &&
            !cases.some((item) => item.case_id === selectedCaseId)
          ) {
            setSelectedCaseId("");
            setCaseDetail(null);
          }
        }
      } catch (error) {
        if (!cancelled) {
          setCaseListError(
            error.message || "Unable to load RCAEval cases."
          );
        }
      } finally {
        if (!cancelled) {
          setCaseListLoading(false);
        }
      }
    }

    loadCases();

    return () => {
      cancelled = true;
    };
  }, [caseSearch]);

    useEffect(() => {
    if (!selectedCaseId) {
      setCaseDetail(null);
      setCaseDetailError("");
      return;
    }

    let cancelled = false;

    async function loadCaseDetail() {
      try {
        setCaseDetailLoading(true);
        setCaseDetailError("");
        setCaseDetail(null);

        const response = await fetch(
          `/api/research/rcaeval/cases/${encodeURIComponent(
            selectedCaseId
          )}`
        );

        if (!response.ok) {
          throw new Error(`Request failed (${response.status})`);
        }

        const data = await response.json();

        if (!cancelled) {
          setCaseDetail(data);
        }
      } catch (error) {
        if (!cancelled) {
          setCaseDetailError(
            error.message || "Unable to load case details."
          );
        }
      } finally {
        if (!cancelled) {
          setCaseDetailLoading(false);
        }
      }
    }

    loadCaseDetail();

    return () => {
      cancelled = true;
    };
  }, [selectedCaseId]);

    return () => {
      cancelled = true;
    };
  }, []);

  const results = benchmark?.results || [];
  const baseline = results.find((item) => item.version === "V1");
  const candidate = results.find((item) => item.version === "V2_1pct");

  const metricCards = [
    {
      label: "Hit@1",
      key: "hit_at_1_pct",
      format: (value) => `${value.toFixed(2)}%`,
      description: "Correct root cause ranked first."
    },
    {
      label: "Hit@3",
      key: "hit_at_3_pct",
      format: (value) => `${value.toFixed(2)}%`,
      description: "Correct root cause within the top three."
    },
    {
      label: "Mean reciprocal rank",
      key: "mrr",
      format: (value) => value.toFixed(4),
      description: "Higher values indicate better ranking."
    },
    {
      label: "Mean correct rank",
      key: "mean_correct_rank",
      format: (value) => value.toFixed(3),
      description: "Lower values indicate better ranking."
    }
  ];

  return (
    <div className="page-wrap subpage">
      <div className="page-heading">
        <div>
          <div className="eyebrow heading-eyebrow">
            EXPERIMENT WORKBENCH
          </div>
          <h1>Research <span>lab.</span></h1>
          <p className="page-description">
            Explore diagnostic robustness and inspect saved RCAEval benchmark
            results.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">SAVED BENCHMARK</div>
            <h2>RCAEval evaluation</h2>
          </div>
          <Pill tone="neutral">
            {benchmarkLoading
              ? "Loading"
              : benchmarkError
                ? "Unavailable"
                : "Exploratory"}
          </Pill>
        </div>

        {benchmarkLoading && (
          <p className="muted-paragraph">
            Loading saved evaluation results from the local backend...
          </p>
        )}

        {benchmarkError && (
          <div className="scenario-note">
            <AlertTriangle size={16} />
            <div>
              <strong>Could not load benchmark results</strong>
              <p>{benchmarkError}. Check that the FastAPI backend is running
                and try refreshing this page.</p>
              <button
                className="primary-button"
                onClick={() => window.location.reload()}
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {benchmark && (
          <>
            <p className="muted-paragraph">
              Dataset: {benchmark.dataset} · Evaluation split:{" "}
              {benchmark.evaluation_split} · Cases per version:{" "}
              {candidate?.cases ?? "—"}
            </p>

            <div className="research-metric">
              <span className="metric-icon blue">
                <Gauge size={16} />
              </span>
              <div>
                <strong>V1 baseline vs. V2 candidate</strong>
                <p>
                  V2 uses a 1% relative scale floor in the robust metric
                  deviation ranking heuristic.
                </p>
              </div>
            </div>

            {baseline && candidate && (
              <div style={{ overflowX: "auto" }}>
                <table style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  marginTop: "16px",
                  textAlign: "left"
                }}>
                  <thead>
                    <tr>
                      <th style={{ padding: "12px 8px" }}>Metric</th>
                      <th style={{ padding: "12px 8px" }}>V1</th>
                      <th style={{ padding: "12px 8px" }}>V2 candidate</th>
                      <th style={{ padding: "12px 8px" }}>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metricCards.map((metric) => {
                      const oldValue = baseline[metric.key];
                      const newValue = candidate[metric.key];
                      const difference = newValue - oldValue;

                      return (
                        <tr key={metric.key}>
                          <td style={{ padding: "12px 8px" }}>
                            <strong>{metric.label}</strong>
                            <p className="muted-paragraph">
                              {metric.description}
                            </p>
                          </td>
                          <td style={{ padding: "12px 8px" }}>
                            {metric.format(oldValue)}
                          </td>
                          <td style={{ padding: "12px 8px" }}>
                            {metric.format(newValue)}
                          </td>
                          <td style={{ padding: "12px 8px" }}>
                            {metric.key === "mean_correct_rank"
                              ? `${difference > 0 ? "+" : ""}${difference.toFixed(3)}`
                              : `${difference > 0 ? "+" : ""}${difference.toFixed(4)}${
                                  metric.key.endsWith("_pct") ? " pp" : ""
                                }`}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="map-callout">
              <CircleHelp size={16} />
              <p>
                Research limitation: {benchmark.interpretation}
              </p>
            </div>

            <p className="muted-paragraph">
              Protocol status: {benchmark.protocol_status}
            </p>
          </>
        )}
      </section>

      
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">CASE EXPLORER</div>
            <h2>Saved RCAEval cases</h2>
          </div>
          <Pill tone="neutral">RE2-OB · 90 cases</Pill>
        </div>

        <p className="muted-paragraph">
          Search previously evaluated cases to inspect service rankings and
          metric-level evidence. These records are not live predictions.
        </p>

        <input
          type="search"
          value={caseSearch}
          onChange={(event) => setCaseSearch(event.target.value)}
          placeholder="Search case ID or fault type, e.g. checkoutservice or cpu"
          aria-label="Search RCAEval cases"
          style={{
            width: "100%",
            padding: "12px",
            margin: "8px 0 16px",
            borderRadius: "8px",
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--text)",
            font: "inherit",
          }}
        />

        {caseListLoading && (
          <p className="muted-paragraph">Loading saved cases...</p>
        )}

        {caseListError && (
          <div className="scenario-note">
            <AlertTriangle size={16} />
            <div>
              <strong>Unable to load cases</strong>
              <p>{caseListError}</p>
            </div>
          </div>
        )}

        {!caseListLoading && !caseListError && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
              gap: "10px",
              marginBottom: "20px",
            }}
          >
            {caseList.map((item) => (
              <button
                key={item.case_id}
                type="button"
                onClick={() => setSelectedCaseId(item.case_id)}
                aria-pressed={selectedCaseId === item.case_id}
                style={{
                  textAlign: "left",
                  padding: "12px",
                  borderRadius: "10px",
                  border:
                    selectedCaseId === item.case_id
                      ? "2px solid var(--accent)"
                      : "1px solid var(--border)",
                  background: "var(--surface)",
                  color: "var(--text)",
                  cursor: "pointer",
                  font: "inherit",
                  overflowWrap: "anywhere",
                }}
              >
                <strong>{item.case_id}</strong>
                <p className="muted-paragraph">
                  Fault: {item.fault_type}
                </p>
                <span className="eyebrow">
                  {item.available_versions?.join(" vs. ")}
                </span>
              </button>
            ))}
          </div>
        )}

        {!caseListLoading &&
          !caseListError &&
          caseList.length === 0 && (
            <p className="muted-paragraph">
              No cases match this search.
            </p>
          )}

        {caseDetailLoading && (
          <p className="muted-paragraph">
            Loading selected case details...
          </p>
        )}

        {caseDetailError && (
          <div className="scenario-note">
            <AlertTriangle size={16} />
            <div>
              <strong>Unable to load case details</strong>
              <p>{caseDetailError}</p>
            </div>
          </div>
        )}

        {caseDetail && (
          <div>
            <div className="map-callout">
              <CircleHelp size={16} />
              <p>
                {caseDetail.interpretation}
              </p>
            </div>

            <h3 style={{ marginTop: "20px" }}>
              {caseDetail.case_id}
            </h3>
            <p className="muted-paragraph">
              Dataset: {caseDetail.dataset} · Split:{" "}
              {caseDetail.evaluation_split} · Fault:{" "}
              {caseDetail.fault_type}
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "14px",
                marginTop: "16px",
              }}
            >
              {["V1", "V2_1pct"].map((version) => {
                const result = caseDetail.versions?.[version];
                if (!result) return null;

                const evaluation = result.evaluation;

                return (
                  <div
                    key={version}
                    style={{
                      border: "1px solid var(--border)",
                      borderRadius: "10px",
                      padding: "14px",
                      minWidth: 0,
                    }}
                  >
                    <h3>{version === "V1" ? "Baseline V1" : "Candidate V2"}</h3>
                    <p className="muted-paragraph">
                      Correct root-cause rank:{" "}
                      {evaluation.correct_root_cause_rank ?? "—"}
                    </p>
                    <p>
                      Hit@1: <strong>{evaluation.hit_at_1 ? "Yes" : "No"}</strong>
                    </p>
                    <p>
                      Hit@3: <strong>{evaluation.hit_at_3 ? "Yes" : "No"}</strong>
                    </p>
                    <p>
                      Reciprocal rank:{" "}
                      <strong>
                        {Number(evaluation.reciprocal_rank).toFixed(3)}
                      </strong>
                    </p>
                    <p className="muted-paragraph">
                      {evaluation.services_ranked} services ·{" "}
                      {evaluation.usable_metrics} usable metrics ·{" "}
                      {evaluation.pre_rows}/{evaluation.post_rows} pre/post rows
                    </p>

                    <h4 style={{ marginTop: "18px" }}>Service ranking</h4>
                    <div style={{ overflowX: "auto" }}>
                      <table
                        style={{
                          width: "100%",
                          borderCollapse: "collapse",
                          textAlign: "left",
                        }}
                      >
                        <thead>
                          <tr>
                            <th style={{ padding: "8px 4px" }}>Rank</th>
                            <th style={{ padding: "8px 4px" }}>Service</th>
                            <th style={{ padding: "8px 4px" }}>Score</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(result.rankings || []).slice(0, 5).map((item) => (
                            <tr key={`${version}-${item.service}`}>
                              <td style={{ padding: "8px 4px" }}>{item.rank}</td>
                              <td style={{ padding: "8px 4px", overflowWrap: "anywhere" }}>
                                {item.service}
                              </td>
                              <td style={{ padding: "8px 4px" }}>
                                {Number(item.service_score).toPrecision(4)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
            </div>

            <h3 style={{ marginTop: "24px" }}>
              Metric-level evidence
            </h3>
            <p className="muted-paragraph">
              Evidence below uses the saved V2 candidate scores. A high score
              indicates a larger normalized metric deviation, not proof of
              causality.
            </p>

            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  textAlign: "left",
                }}
              >
                <thead>
                  <tr>
                    {[
                      "Service",
                      "Metric",
                      "Pre median",
                      "Post median",
                      "Effective scale",
                      "Change score",
                    ].map((heading) => (
                      <th key={heading} style={{ padding: "10px 8px" }}>
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(caseDetail.versions?.V2_1pct?.metric_evidence || [])
                    .slice(0, 15)
                    .map((item) => (
                      <tr key={`${item.service}-${item.metric}`}>
                        <td style={{ padding: "10px 8px" }}>{item.service}</td>
                        <td style={{ padding: "10px 8px" }}>{item.metric}</td>
                        <td style={{ padding: "10px 8px" }}>
                          {Number(item.pre_median).toPrecision(4)}
                        </td>
                        <td style={{ padding: "10px 8px" }}>
                          {Number(item.post_median).toPrecision(4)}
                        </td>
                        <td style={{ padding: "10px 8px" }}>
                          {Number(item.effective_scale).toPrecision(4)}
                        </td>
                        <td style={{ padding: "10px 8px" }}>
                          {Number(item.change_score).toPrecision(4)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <div className="research-layout">
        <section className="panel experiment-panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">ROBUSTNESS STUDY</div>
              <h2>Evidence degradation</h2>
            </div>
            <Pill tone="neutral">Simulation</Pill>
          </div>

          <p className="muted-paragraph">
            Configure a synthetic scenario to explore how data quality may
            affect diagnosis. These controls do not rerun RCAEval or change
            the saved benchmark results.
          </p>

          <div className="range-control">
            <div>
              <label htmlFor="noise-range">Injected noise</label>
              <strong>{noise}%</strong>
            </div>
            <input
              id="noise-range"
              type="range"
              min="0"
              max="60"
              step="5"
              value={noise}
              onChange={(event) => {
                setNoise(Number(event.target.value));
                setRan(false);
              }}
            />
            <div className="range-labels">
              <span>Clean</span>
              <span>Heavy noise</span>
            </div>
          </div>

          <div className="range-control">
            <div>
              <label htmlFor="missing-range">Missing telemetry</label>
              <strong>{missing}%</strong>
            </div>
            <input
              id="missing-range"
              type="range"
              min="0"
              max="70"
              step="5"
              value={missing}
              onChange={(event) => {
                setMissing(Number(event.target.value));
                setRan(false);
              }}
            />
            <div className="range-labels">
              <span>Complete</span>
              <span>Sparse</span>
            </div>
          </div>

          <button className="primary-button" onClick={() => setRan(true)}>
            <Cpu size={16} /> Configure scenario
          </button>

          {ran && (
            <div className="scenario-note">
              <AlertTriangle size={16} />
              <div>
                <strong>Simulation configured</strong>
                <p>
                  {noise}% synthetic noise and {missing}% telemetry removal
                  selected. No benchmark was rerun and no measured accuracy
                  is available for this configuration.
                </p>
              </div>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="eyebrow">EVALUATION PLAN</div>
          <h2>What we measure</h2>

          <div className="research-metric">
            <span className="metric-icon blue"><Gauge size={16} /></span>
            <div>
              <strong>Hit@1 / Hit@3</strong>
              <p>Whether the labelled cause appears at rank one or within
                the top three.</p>
            </div>
          </div>

          <div className="research-metric">
            <span className="metric-icon purple"><Activity size={16} /></span>
            <div>
              <strong>Mean reciprocal rank</strong>
              <p>Rewards placing the correct cause higher in the ranked list.</p>
            </div>
          </div>

          <div className="research-metric">
            <span className="metric-icon orange">
              <ShieldCheck size={16} />
            </span>
            <div>
              <strong>Risk vs. coverage</strong>
              <p>Measure accuracy when the system answers only on cases it
                considers reliable. This remains future evaluation work.</p>
            </div>
          </div>

          <div className="map-callout">
            <CircleHelp size={16} />
            <p>
              Keep simulated scenarios separate from measured benchmark
              results. Independent validation is still needed.
            </p>
          </div>
        </section>
      </div>

      <section className="panel research-question">
        <div className="eyebrow">WORKING RESEARCH QUESTION</div>
        <h2>
          Can evidence-aware ranking remain reliable under incomplete and
          noisy telemetry?
        </h2>
        <p>
          Compare a transparent baseline with the proposed method. Future
          experiments should isolate temporal signals, dependency
          information, and uncertainty handling.
        </p>
        <div className="research-tags">
          <span>Root-cause ranking</span>
          <span>Explainable AI</span>
          <span>Robustness</span>
          <span>Uncertainty calibration</span>
        </div>
      </section>
    </div>
  );
}

function LogsPage() { const [filter,setFilter]=useState('All levels');return <div className="page-wrap subpage"><div className="page-heading"><div><div className="eyebrow heading-eyebrow">TELEMETRY</div><h1>Log <span>explorer.</span></h1><p className="page-description">A focused view of events captured for the selected sample incident.</p></div></div><section className="panel"><div className="panel-header"><div><div className="eyebrow">STREAM · CHECKOUT API</div><h2>Recent events</h2></div><select className="filter-select" value={filter} onChange={e=>setFilter(e.target.value)}><option>All levels</option><option>error</option><option>warn</option><option>info</option></select></div><div className="log-terminal">{timeline.filter(t=>filter==='All levels'||t.level===filter).map(t=><div className="terminal-line" key={t.time}><span>{t.time}</span><b className={t.level}>{t.level.toUpperCase()}</b><span>{t.service}</span><p>{t.text} <code>{t.detail}</code></p></div>)}</div><div className="disclaimer"><Terminal size={15}/> Sample stream only. Connect a real ingestion adapter before using operationally.</div></section></div>}

function SettingsPage({theme,setTheme,apiState}) {return <div className="page-wrap subpage"><div className="page-heading"><div><div className="eyebrow heading-eyebrow">PREFERENCES</div><h1>Workspace <span>settings.</span></h1><p className="page-description">Customize the local TraceWise experience.</p></div></div><section className="panel settings-panel"><div className="setting-row"><div className="setting-icon"><Sun size={18}/></div><div className="setting-copy"><strong>Appearance</strong><p>Choose the interface theme. Your choice is saved in this browser.</p></div><div className="theme-switch"><button className={theme==='light'?'selected':''} onClick={()=>setTheme('light')}><Sun size={15}/> Light</button><button className={theme==='dark'?'selected':''} onClick={()=>setTheme('dark')}><Moon size={15}/> Dark</button></div></div><div className="setting-row"><div className="setting-icon"><Activity size={18}/></div><div className="setting-copy"><strong>Backend connection</strong><p>FastAPI endpoint status for local incident analysis.</p></div><Pill tone={apiState==='connected'?'success':'warning'}>{apiState==='connected'?'Connected':'Demo fallback'}</Pill></div><div className="setting-row"><div className="setting-icon"><Database size={18}/></div><div className="setting-copy"><strong>Data privacy</strong><p>Core analysis is designed to run locally. No external AI API is required.</p></div><Pill tone="success">Local-first</Pill></div></section><div className="settings-footnote"><ShieldCheck size={16}/> TraceWise is a research prototype. Do not connect production credentials or sensitive telemetry without a security review.</div></div>}