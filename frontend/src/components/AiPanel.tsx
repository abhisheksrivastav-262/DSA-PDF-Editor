import { useState } from 'react'
import api from '../lib/api'
import { Sparkles, Send, Eye, Check, AlertTriangle, Search, ListChecks } from 'lucide-react'

export default function AiPanel({ docId, selectedText, pageText, onApplied }: { docId:number, selectedText:string, pageText:string, onApplied:()=>void }){
  const [prompt,setPrompt]=useState('')
  const [context,setContext]=useState<'selected_text'|'current_page'|'entire_document'|'selected_pages'>('current_page')
  const [loading,setLoading]=useState(false)
  const [response,setResponse]=useState<any>(null)
  const [preview,setPreview]=useState<any>(null)
  const [error,setError]=useState<string>('')

  async function send(){
    if(!prompt.trim()) return
    setLoading(true); setError(''); setResponse(null); setPreview(null)
    try{
      const {data} = await api.post('/ai/chat', {prompt, document_id: docId, context, selected_text: selectedText, page_text: pageText})
      const res = data.response || data
      // data may have {response: {...}, mock:true}
      const actual = data.response || res
      setResponse(actual)
      // auto preview
      const {data: pv} = await api.post('/ai/preview', {document_id: docId, ai_response: actual})
      setPreview(pv)
    } catch(e:any){
      setError(e.response?.data?.detail || e.message || 'AI error')
    } finally{ setLoading(false) }
  }

  async function apply(){
    if(!response) return
    setLoading(true)
    try{
      await api.post('/ai/apply', {document_id: docId, ai_response: response})
      setResponse(null); setPreview(null); setPrompt('')
      onApplied()
    } catch(e:any){ setError(e.response?.data?.detail || e.message) }
    finally{ setLoading(false) }
  }

  const suggestions = [
    'Find every occurrence of ABC Limited',
    'Replace ABC Limited with ABC Private Limited',
    'Highlight all salary transactions',
    'Redact the account number on page 2',
    'Extract the table from page 1',
    'Summarize this document',
  ]

  return (
    <div className="w-[360px] border-l border-slate-200 bg-white flex flex-col h-full">
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center gap-2 font-semibold"><Sparkles className="w-5 h-5 text-indigo-600"/> EDITOR AI</div>
        <div className="text-xs text-slate-500 mt-1">Natural language PDF editing. Structured JSON → Preview → Apply</div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div>
          <div className="text-xs font-semibold text-slate-600 uppercase tracking-widest">Context</div>
          <div className="grid grid-cols-2 gap-2 mt-2">
            {([
              ['selected_text','Selected text'],
              ['current_page','Current page'],
              ['selected_pages','Selected pages'],
              ['entire_document','Entire document'],
            ] as const).map(([v,l])=>(
              <label key={v} className={`text-xs px-3 py-2 rounded-xl border cursor-pointer flex items-center gap-2 ${context===v?'bg-indigo-50 border-indigo-300 text-indigo-700':'bg-white border-slate-200'}`}>
                <input type="radio" name="ctx" checked={context===v} onChange={()=>setContext(v as any)} className="hidden"/> {l}
              </label>
            ))}
          </div>
          {selectedText && <div className="mt-2 text-xs bg-amber-50 border border-amber-200 rounded-lg p-2 line-clamp-3">Selected: {selectedText.slice(0,300)}</div>}
        </div>

        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-600 uppercase tracking-widest">Suggestions</div>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map(s=>(
              <button key={s} onClick={()=>setPrompt(s)} className="text-xs px-2.5 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-200">{s}</button>
            ))}
          </div>
        </div>

        {response && (
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-3">
            <div className="text-xs font-bold text-indigo-800 flex items-center gap-2"><ListChecks className="w-4 h-4"/> AI Proposed Change</div>
            <div className="text-xs text-slate-700 mt-2"><span className="font-semibold">Intent:</span> {response.intent} <span className="ml-2 px-1.5 py-0.5 rounded bg-white border text-[11px]">{Math.round((response.confidence||0)*100)}% confidence</span></div>
            <div className="text-xs text-slate-600 mt-1">{response.explanation}</div>
            <div className="mt-2 space-y-1.5">
              {response.operations?.map((op:any,i:number)=>(
                <div key={i} className="text-xs bg-white border border-slate-200 rounded-lg p-2">
                  <div className="font-mono font-semibold">{op.type}</div>
                  {op.find && <div>Find: <span className="font-mono bg-yellow-50 px-1">{op.find}</span></div>}
                  {op.replace!==undefined && <div>Replace: <span className="font-mono bg-green-50 px-1">{op.replace}</span></div>}
                  {op.bbox && <div>BBox: [{op.bbox.join(', ')}]</div>}
                </div>
              ))}
            </div>
            {preview?.previews && (
              <div className="mt-3 bg-white rounded-lg border p-2 space-y-1">
                {preview.previews.map((p:any,i:number)=>(
                  <div key={i} className="text-xs flex items-center gap-2"><Search className="w-3 h-3"/>{p.type}: {p.matches!==undefined ? `${p.matches} matches` : p.detail || 'ready'}</div>
                ))}
              </div>
            )}
            <div className="flex gap-2 mt-3">
              <button onClick={()=>{setResponse(null); setPreview(null)}} className="flex-1 bg-white border border-slate-200 rounded-xl py-2 text-xs font-medium">Cancel</button>
              <button onClick={()=>api.post('/ai/preview',{document_id:docId, ai_response:response}).then(r=>setPreview(r.data))} className="flex-1 bg-slate-900 text-white rounded-xl py-2 text-xs font-medium flex items-center justify-center gap-1"><Eye className="w-3 h-3"/> Preview</button>
              <button onClick={apply} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl py-2 text-xs font-bold flex items-center justify-center gap-1"><Check className="w-3 h-3"/> Apply Change</button>
            </div>
          </div>
        )}

        {error && <div className="rounded-xl bg-red-50 border border-red-200 p-3 text-xs text-red-700 flex gap-2"><AlertTriangle className="w-4 h-4 shrink-0"/>{error}</div>}

        {!response && (
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3">
            <div className="text-xs font-semibold">How it works</div>
            <div className="text-xs text-slate-600 mt-1 leading-relaxed">
              User Prompt → Document Context Extraction → AI API (OpenAI-compatible) → Structured JSON → Validation → Operation Preview → User Approval → PDF Engine → New Version → Fidelity Check
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-slate-200 bg-white">
        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-2xl px-3 py-2">
          <input value={prompt} onChange={e=>setPrompt(e.target.value)} onKeyDown={e=>e.key==='Enter' && send()} placeholder="Ask AI: Replace, find, highlight, redact..." className="flex-1 bg-transparent outline-none text-sm"/>
          <button onClick={send} disabled={loading} className="w-8 h-8 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center disabled:opacity-50">
            {loading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"/> : <Send className="w-4 h-4"/>}
          </button>
        </div>
        <div className="text-[11px] text-slate-400 mt-2 text-center">AI uses your configured provider. Never sends entire PDF blindly — only selected context.</div>
      </div>
    </div>
  )
}
