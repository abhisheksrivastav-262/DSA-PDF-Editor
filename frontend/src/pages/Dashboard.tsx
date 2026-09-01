import { useEffect, useState } from 'react'
import api from '../lib/api'
import { Link, useNavigate } from 'react-router-dom'
import { FilePlus2, Upload, Clock, Sparkles, Search, FileText } from 'lucide-react'

export default function Dashboard(){
  const [stats,setStats]=useState<any>(null)
  const [recentDocs,setRecentDocs]=useState<any[]>([])
  const [query,setQuery]=useState('')
  const nav = useNavigate()

  useEffect(()=>{
    api.get('/stats').then(r=>setStats(r.data)).catch(()=>{})
    api.get('/documents/').then(r=>setRecentDocs(r.data.slice(0,6))).catch(()=>{})
  },[])

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>){
    const f = e.target.files?.[0]
    if(!f) return
    const fd = new FormData()
    fd.append('file', f)
    const {data} = await api.post('/documents/upload', fd, {headers:{'Content-Type':'multipart/form-data'}})
    nav(`/editor/${data.id}`)
  }

  async function onSearch(e: React.FormEvent){
    e.preventDefault()
    if(!query.trim()) return
    nav(`/documents?search=${encodeURIComponent(query)}`)
  }

  return (
    <div className="p-8 max-w-[1280px] mx-auto">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">Welcome back — manage, edit and transform PDFs with AI.</p>
        </div>
        <div className="flex gap-2">
          <label className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium cursor-pointer">
            <Upload className="w-4 h-4"/> Upload PDF
            <input type="file" accept="application/pdf" className="hidden" onChange={onUpload} />
          </label>
          <Link to="/documents" className="inline-flex items-center gap-2 bg-white border border-slate-200 px-4 py-2.5 rounded-xl text-sm font-medium">
            <FilePlus2 className="w-4 h-4"/> New PDF
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mt-8">
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">Total Documents</div>
          <div className="text-3xl font-bold mt-2">{stats?.total_documents ?? '—'}</div>
          <div className="text-xs text-emerald-600 mt-1">+2 this week</div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">Edited PDFs</div>
          <div className="text-3xl font-bold mt-2">{stats?.edited_pdfs ?? '—'}</div>
          <div className="text-xs text-slate-500 mt-1">Versions created</div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">AI Operations</div>
          <div className="text-3xl font-bold mt-2">{stats?.ai_operations ?? '—'}</div>
          <div className="text-xs text-indigo-600 mt-1">via OpenAI-compatible API</div>
        </div>
        <div className="bg-gradient-to-br from-indigo-600 to-violet-600 rounded-2xl p-5 text-white">
          <div className="flex items-center gap-2 text-white/80 text-xs uppercase tracking-widest font-semibold"><Sparkles className="w-4 h-4"/> AI Assistant</div>
          <div className="text-sm mt-2 leading-relaxed">Try: “Replace ABC Limited with ABC Private Limited”</div>
          <Link to="/documents" className="inline-block mt-3 text-xs bg-white text-indigo-700 px-3 py-1.5 rounded-full font-semibold">Open Editor →</Link>
        </div>
      </div>

      <form onSubmit={onSearch} className="mt-8 bg-white border border-slate-200 rounded-2xl p-2 flex items-center gap-2">
        <Search className="w-5 h-5 text-slate-400 ml-3"/>
        <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search documents, text, annotations, AI operations..." className="flex-1 py-2.5 px-2 outline-none text-sm"/>
        <button className="bg-slate-900 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Search</button>
      </form>

      <div className="grid grid-cols-3 gap-6 mt-8">
        <div className="col-span-2 bg-white rounded-2xl border border-slate-200">
          <div className="p-5 flex items-center justify-between">
            <h3 className="font-semibold">Recent Files</h3>
            <Link to="/documents" className="text-sm text-indigo-600 font-medium">View all</Link>
          </div>
          <div className="px-5 pb-5 grid gap-3">
            {recentDocs.length===0 && <div className="text-sm text-slate-500 py-10 text-center">No documents yet. Upload a PDF to get started.</div>}
            {recentDocs.map(d=>(
              <Link key={d.id} to={`/editor/${d.id}`} className="flex items-center gap-4 p-3 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-200">
                <div className="w-12 h-14 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center"><FileText className="w-6 h-6 text-red-500"/></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{d.filename}</div>
                  <div className="text-xs text-slate-500">{d.page_count} pages • v{d.current_version} • {new Date(d.updated_at).toLocaleDateString()}</div>
                </div>
                <div className="text-xs px-2 py-1 rounded-full bg-slate-100">{d.is_favorite ? '★ Favorite' : 'Edited'}</div>
              </Link>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <h3 className="font-semibold">Recent Activity</h3>
          <div className="mt-4 space-y-3">
            {(stats?.recent_activity||[]).map((a:any,i:number)=>(
              <div key={i} className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center"><Clock className="w-4 h-4 text-slate-500"/></div>
                <div>
                  <div className="text-sm font-medium">{a.action}</div>
                  <div className="text-xs text-slate-500 line-clamp-1">{a.detail}</div>
                  <div className="text-[11px] text-slate-400">{a.created_at ? new Date(a.created_at).toLocaleString() : ''}</div>
                </div>
              </div>
            ))}
            {(!stats?.recent_activity || stats.recent_activity.length===0) && <div className="text-sm text-slate-500">No activity yet</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
