import { useEffect, useState } from 'react'
import api from '../lib/api'
import { History, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function AiHistory(){
  const [rows,setRows]=useState<any[]>([])
  useEffect(()=>{ api.get('/ai/history').then(r=>setRows(r.data)).catch(()=>{}) },[])
  return (
    <div className="p-8 max-w-[1080px] mx-auto">
      <h1 className="text-2xl font-bold flex items-center gap-2"><History className="w-6 h-6"/> AI History</h1>
      <p className="text-sm text-slate-500">All AI prompts, models, operations and status. Open associated version to inspect.</p>
      <div className="mt-6 bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-widest text-slate-500"><tr><th className="text-left p-3">Timestamp</th><th className="text-left">Prompt</th><th>Model</th><th>Operation</th><th>Status</th><th>Doc</th></tr></thead>
          <tbody>
            {rows.map(r=>(
              <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</td>
                <td className="max-w-[260px] truncate text-xs">{r.prompt}</td>
                <td className="text-center text-xs font-mono">{r.model||'—'}</td>
                <td className="text-center text-xs">{r.operation}</td>
                <td className="text-center"><span className={`text-xs px-2 py-1 rounded-full inline-flex items-center gap-1 ${r.status==='applied'?'bg-emerald-50 text-emerald-700 border border-emerald-200': r.status==='failed'?'bg-red-50 text-red-700 border border-red-200':'bg-amber-50 text-amber-700 border border-amber-200'}`}>{r.status==='applied'?<CheckCircle className="w-3 h-3"/>: r.status==='failed'?<XCircle className="w-3 h-3"/>:<Clock className="w-3 h-3"/>}{r.status}</span></td>
                <td className="text-center">{r.document_id ? <Link to={`/editor/${r.document_id}`} className="text-indigo-600 text-xs">#{r.document_id}</Link> : '—'}</td>
              </tr>
            ))}
            {rows.length===0 && <tr><td colSpan={6} className="p-10 text-center text-slate-500 text-sm">No AI operations yet</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
