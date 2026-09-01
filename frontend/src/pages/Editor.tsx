import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../lib/api'
import PdfViewer from '../components/PdfViewer'
import AiPanel from '../components/AiPanel'
import { Search, Replace, Highlighter, StickyNote, EyeOff, Undo2, Redo2, ZoomIn, RotateCw, Files, Download, Save, History, ArrowLeft, Sparkles, PenLine, FileStack, Trash2, Copy } from 'lucide-react'

export default function Editor(){
  const { id } = useParams()
  const docId = Number(id)
  const [doc,setDoc]=useState<any>(null)
  const [versions,setVersions]=useState<any[]>([])
  const [url,setUrl]=useState('')
  const [selectedText,setSelectedText]=useState('')
  const [pageText,setPageText]=useState('')
  const [find,setFind]=useState('')
  const [replaceTxt,setReplaceTxt]=useState('')
  const [matches,setMatches]=useState<number|null>(null)
  const [compare,setCompare]=useState(false)
  const [tool,setTool]=useState<'select'|'edit'|'highlight'|'redact'|'draw'>('select')
  const [showVersions,setShowVersions]=useState(true)

  async function load(){
    const {data} = await api.get(`/documents/${docId}`)
    setDoc(data); setVersions(data.versions||[])
    // get latest file url
    setUrl(`/api/documents/${docId}/file?t=${Date.now()}`)
    const {data: td} = await api.get(`/documents/${docId}/text`)
    setPageText(td.text?.slice(0,8000)||'')
  }
  useEffect(()=>{ load() },[docId])

  async function doFind(){
    if(!find) return
    const {data} = await api.post(`/documents/${docId}/find`, {query: find})
    setMatches(data.count)
  }
  async function doReplace(dry=false){
    if(!find) return
    const {data} = await api.post(`/documents/${docId}/replace`, {find, replace: replaceTxt, dry_run: dry})
    if(dry){
      alert(`Preview: ${data.preview?.matches ?? 0} matches. Fidelity: ${JSON.stringify(data.preview?.fidelity||data.preview||{}).slice(0,400)}`)
    } else {
      alert(`Replaced — new version v${data.version}`)
      load()
    }
  }
  async function doHighlight(){
    if(!find) return alert('Enter text to highlight or use AI')
    const {data} = await api.post(`/documents/${docId}/find`, {query: find})
    if(data.matches?.length>0){
      const m = data.matches[0]
      await api.post(`/documents/${docId}/highlight`, {page: m.page_number, bbox: m.bounding_box})
      load()
    } else alert('No matches')
  }
  async function doRedact(){
    const bbox = prompt('Enter bbox x1,y1,x2,y2 (e.g. 100,500,300,520)')
    if(!bbox) return
    const nums = bbox.split(',').map(Number)
    let {data} = await api.post(`/documents/${docId}/redact`, {page:0, bbox: nums})
    if(data.preview){ if(confirm('Preview: white rectangle will cover. Apply?')){ data = (await api.post(`/documents/${docId}/redact`, {page:0, bbox: nums, confirm:true})).data; load()} }
    else load()
  }
  async function rotate(){ await api.post(`/documents/${docId}/pages/rotate`, {pages:[0], angle:90}); load() }
  async function deletePage(){ if(confirm('Delete first page?')){ await api.post(`/documents/${docId}/pages/delete`, {pages:[0]}); load()} }
  async function duplicatePage(){ await api.post(`/documents/${docId}/pages/duplicate`, {page:0}); load() }

  const onSelect = useCallback((t:string)=>setSelectedText(t),[])

  if(!doc) return <div className="p-10 text-sm text-slate-500">Loading document...</div>

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="h-[56px] bg-white border-b border-slate-200 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <Link to="/documents" className="p-2 rounded-lg hover:bg-slate-100"><ArrowLeft className="w-5 h-5"/></Link>
          <div>
            <div className="text-sm font-semibold flex items-center gap-2">{doc.filename} <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200">v{doc.current_version}</span></div>
            <div className="text-xs text-slate-500">{doc.page_count} pages • Original preserved • Transparent version history</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={()=>setCompare(!compare)} className={`px-3 py-2 rounded-xl text-xs font-medium border ${compare?'bg-indigo-600 text-white border-indigo-600':'bg-white border-slate-200'}`}>Compare</button>
          <a href={`/api/documents/${docId}/export?type=original`} className="px-3 py-2 rounded-xl text-xs font-medium bg-white border border-slate-200">Download Original</a>
          <a href={`/api/documents/${docId}/export?type=edited`} className="px-3 py-2 rounded-xl text-xs font-medium bg-slate-900 text-white">Export PDF</a>
        </div>
      </div>

      {/* Toolbar */}
      <div className="bg-white border-b border-slate-200 px-2 py-2 flex items-center gap-1 flex-wrap">
        {[
          ['select','Select'],
          ['edit','Edit Text'],
          ['highlight','Highlight'],
          ['redact','Redact'],
          ['draw','Draw'],
        ].map(([k,label])=>(
          <button key={k} onClick={()=>setTool(k as any)} className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 border ${tool===k?'bg-slate-900 text-white border-slate-900':'bg-white border-slate-200 text-slate-700'}`}>
            {k==='select' && <Search className="w-3.5 h-3.5"/>}
            {k==='edit' && <PenLine className="w-3.5 h-3.5"/>}
            {k==='highlight' && <Highlighter className="w-3.5 h-3.5"/>}
            {k==='redact' && <EyeOff className="w-3.5 h-3.5"/>}
            {k==='draw' && <PenLine className="w-3.5 h-3.5"/>}
            {label}
          </button>
        ))}
        <div className="w-px h-6 bg-slate-200 mx-2"/>
        <div className="flex items-center gap-1">
          <button className="p-1.5 rounded-lg hover:bg-slate-100"><Undo2 className="w-4 h-4"/></button>
          <button className="p-1.5 rounded-lg hover:bg-slate-100"><Redo2 className="w-4 h-4"/></button>
        </div>
        <div className="w-px h-6 bg-slate-200 mx-2"/>
        <button onClick={rotate} className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-xs flex items-center gap-1"><RotateCw className="w-3.5 h-3.5"/> Rotate</button>
        <button onClick={deletePage} className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-xs flex items-center gap-1"><Trash2 className="w-3.5 h-3.5"/> Delete Page</button>
        <button onClick={duplicatePage} className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-xs flex items-center gap-1"><Copy className="w-3.5 h-3.5"/> Duplicate</button>
        <button onClick={()=>setShowVersions(!showVersions)} className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-xs flex items-center gap-1"><History className="w-3.5 h-3.5"/> Versions</button>
        <div className="ml-auto flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5">
          <input value={find} onChange={e=>setFind(e.target.value)} placeholder="Find" className="bg-transparent outline-none text-xs w-28"/>
          <input value={replaceTxt} onChange={e=>setReplaceTxt(e.target.value)} placeholder="Replace" className="bg-transparent outline-none text-xs w-28 border-l border-slate-200 pl-3"/>
          <button onClick={doFind} className="text-xs bg-white border border-slate-200 px-2.5 py-1 rounded-lg">Find {matches!==null?`(${matches})`:''}</button>
          <button onClick={()=>doReplace(false)} className="text-xs bg-indigo-600 text-white px-2.5 py-1 rounded-lg">Replace</button>
          <button onClick={()=>doReplace(true)} className="text-xs bg-white border border-slate-200 px-2.5 py-1 rounded-lg">Preview</button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left thumbnails */}
        <div className="w-[200px] border-r border-slate-200 bg-white hidden lg:flex flex-col">
          <div className="p-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Pages</div>
          <div className="flex-1 overflow-auto p-3 space-y-3">
            {Array.from({length: doc.page_count||1}).map((_,i)=>(
              <div key={i} className="rounded-xl border-2 border-slate-200 bg-slate-50 h-28 flex items-center justify-center text-xs text-slate-500 relative">
                {i+1}
                <div className="absolute inset-0 border-2 border-transparent hover:border-indigo-400 rounded-xl pointer-events-none"/>
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-slate-200 space-y-2">
            <button onClick={doHighlight} className="w-full py-2 rounded-xl bg-amber-400 hover:bg-amber-500 text-xs font-semibold flex items-center justify-center gap-1"><Highlighter className="w-3.5 h-3.5"/> Highlight Found</button>
            <button onClick={doRedact} className="w-full py-2 rounded-xl bg-white border border-slate-200 text-xs font-medium flex items-center justify-center gap-1"><EyeOff className="w-3.5 h-3.5"/> Redact Region</button>
          </div>
        </div>

        {/* PDF Viewer */}
        <div className="flex-1 min-w-0 bg-[#eef2f7]">
          {!compare ? (
            <PdfViewer url={url} onSelectText={onSelect} onPageChange={()=>{}}/>
          ) : (
            <div className="grid grid-cols-2 gap-0 h-full">
              <div className="border-r border-slate-300">
                <div className="text-xs font-semibold p-2 bg-white border-b">Before — Original (v1)</div>
                <PdfViewer url={`/api/documents/${docId}/file?version=1`}/>
              </div>
              <div>
                <div className="text-xs font-semibold p-2 bg-white border-b">After — Latest (v{doc.current_version})</div>
                <PdfViewer url={url}/>
              </div>
            </div>
          )}
        </div>

        {/* Version history */}
        {showVersions && (
          <div className="w-[260px] border-l border-slate-200 bg-white flex flex-col">
            <div className="p-3 border-b border-slate-200">
              <div className="font-semibold text-sm flex items-center gap-2"><History className="w-4 h-4"/> Version History</div>
              <div className="text-xs text-slate-500">Never overwrites original. Each edit creates a new version.</div>
            </div>
            <div className="flex-1 overflow-auto p-3 space-y-2">
              {versions.map(v=>(
                <a key={v.version} href={`/api/documents/${docId}/file?version=${v.version}`} target="_blank" className="block p-3 rounded-xl border bg-slate-50 border-slate-200 hover:border-indigo-300">
                  <div className="text-xs font-bold">v{v.version} — {v.operation}</div>
                  <div className="text-xs text-slate-600 line-clamp-2">{v.detail}</div>
                  <div className="text-[11px] text-slate-400 mt-1">{v.is_ai ? 'AI • ' : 'Manual • '}{new Date(v.created_at).toLocaleString()}</div>
                  {v.fidelity_report && <div className="text-[11px] mt-1 px-1.5 py-0.5 rounded bg-white border inline-block">{v.fidelity_report.font_preserved ? '✓ Font preserved' : '⚠ Font substituted'}</div>}
                </a>
              ))}
              <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-3">
                <div className="text-xs font-semibold text-indigo-800">Bank Statement Review</div>
                <div className="text-xs text-slate-600 mt-1">Supported: search, extraction, highlighting, highlight salary/EMI, redact account info — as normal PDFs.</div>
              </div>
            </div>
          </div>
        )}

        {/* AI Panel */}
        <AiPanel docId={docId} selectedText={selectedText} pageText={pageText} onApplied={load}/>
      </div>
    </div>
  )
}
