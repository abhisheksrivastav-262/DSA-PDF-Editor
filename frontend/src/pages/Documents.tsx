import { useEffect, useState } from 'react'
import api from '../lib/api'
import { Link, useSearchParams } from 'react-router-dom'
import { FileText, Star, Trash2, Copy, Download, LayoutGrid, List, Search, Upload, Filter } from 'lucide-react'

export default function Documents(){
  const [docs,setDocs]=useState<any[]>([])
  const [q,setQ]=useState('')
  const [view,setView]=useState<'grid'|'list'>('grid')
  const [params] = useSearchParams()
  const searchParam = params.get('search') || ''

  async function load(){
    const {data} = await api.get('/documents/', {params: {q: q || searchParam || undefined}})
    setDocs(data)
  }
  useEffect(()=>{ if(searchParam) setQ(searchParam); },[searchParam])
  useEffect(()=>{ load() },[q, searchParam])

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>){
    const f = e.target.files?.[0]; if(!f) return
    const fd=new FormData(); fd.append('file',f)
    await api.post('/documents/upload', fd, {headers:{'Content-Type':'multipart/form-data'}})
    load()
  }
  async function toggleFav(d:any){
    await api.put(`/documents/${d.id}`, {is_favorite: !d.is_favorite}); load()
  }
  async function del(d:any){ if(confirm('Move to trash?')){ await api.delete(`/documents/${d.id}`); load() } }
  async function dup(d:any){ await api.post(`/documents/${d.id}/duplicate`); load() }

  return (
    <div className="p-8 max-w-[1280px] mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Documents</h1>
        <label className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium cursor-pointer">
          <Upload className="w-4 h-4"/> Upload PDF <input type="file" accept="application/pdf" className="hidden" onChange={onUpload}/>
        </label>
      </div>

      <div className="mt-6 flex items-center gap-3">
        <div className="flex-1 flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3">
          <Search className="w-4 h-4 text-slate-400"/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search by name or text..." className="flex-1 py-2.5 outline-none text-sm"/>
        </div>
        <div className="flex items-center bg-white border border-slate-200 rounded-xl p-1">
          <button onClick={()=>setView('grid')} className={`p-2 rounded-lg ${view==='grid'?'bg-slate-900 text-white':'text-slate-500'}`}><LayoutGrid className="w-4 h-4"/></button>
          <button onClick={()=>setView('list')} className={`p-2 rounded-lg ${view==='list'?'bg-slate-900 text-white':'text-slate-500'}`}><List className="w-4 h-4"/></button>
        </div>
        <button className="bg-white border border-slate-200 px-4 py-2.5 rounded-xl text-sm flex items-center gap-2"><Filter className="w-4 h-4"/> Filter</button>
      </div>

      {view==='grid' ? (
        <div className="grid grid-cols-4 gap-4 mt-6">
          {docs.map(d=>(
            <div key={d.id} className="bg-white rounded-2xl border border-slate-200 overflow-hidden hover:shadow-sm transition">
              <Link to={`/editor/${d.id}`} className="block p-6 flex flex-col items-center">
                <div className="w-20 h-24 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center"><FileText className="w-10 h-10 text-red-500"/></div>
                <div className="mt-4 text-sm font-medium text-center line-clamp-2">{d.filename}</div>
                <div className="text-xs text-slate-500">{d.page_count} pages • v{d.current_version}</div>
              </Link>
              <div className="px-3 py-2 border-t border-slate-100 flex items-center justify-between">
                <div className="flex gap-1">
                  <button onClick={()=>toggleFav(d)} className={`p-1.5 rounded-lg ${d.is_favorite?'text-amber-500 bg-amber-50':'text-slate-400 hover:bg-slate-50'}`}><Star className="w-4 h-4"/></button>
                  <button onClick={()=>dup(d)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-50"><Copy className="w-4 h-4"/></button>
                  <button onClick={()=>del(d)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-50"><Trash2 className="w-4 h-4"/></button>
                </div>
                <Link to={`/editor/${d.id}`} className="text-xs bg-slate-900 text-white px-3 py-1.5 rounded-full">Open</Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 mt-6 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-widest"><tr><th className="text-left p-3">Name</th><th>Pages</th><th>Modified</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {docs.map(d=>(
                <tr key={d.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="p-3 flex items-center gap-3"><FileText className="w-5 h-5 text-red-500"/>{d.filename}</td>
                  <td className="text-center">{d.page_count}</td>
                  <td className="text-center text-slate-500">{new Date(d.updated_at).toLocaleString()}</td>
                  <td className="text-center"><span className="text-xs px-2 py-1 rounded-full bg-slate-100">v{d.current_version}</span></td>
                  <td className="text-center flex justify-center gap-1 p-2">
                    <button onClick={()=>toggleFav(d)} className="p-1.5"><Star className={`w-4 h-4 ${d.is_favorite?'fill-amber-400 text-amber-400':''}`}/></button>
                    <Link to={`/editor/${d.id}`} className="p-1.5"><Download className="w-4 h-4"/></Link>
                    <button onClick={()=>dup(d)} className="p-1.5"><Copy className="w-4 h-4"/></button>
                    <button onClick={()=>del(d)} className="p-1.5"><Trash2 className="w-4 h-4"/></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {docs.length===0 && <div className="p-10 text-center text-slate-500 text-sm">No documents found</div>}
        </div>
      )}
    </div>
  )
}
