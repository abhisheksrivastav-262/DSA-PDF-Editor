import { useEffect, useState } from 'react'
import api from '../lib/api'
import { Settings as SettingsIcon, Shield, Database, Palette, Keyboard, Check, X, Eye, EyeOff, AlertTriangle } from 'lucide-react'

export default function Settings(){
  const [form,setForm]=useState({ AI_BASE_URL:'', AI_API_KEY:'', AI_MODEL:'', AI_TEMPERATURE:'0.2', AI_MAX_TOKENS:'4096' })
  const [showKey,setShowKey]=useState(false)
  const [status,setStatus]=useState<{ok:boolean, msg:string}|null>(null)
  const [testing,setTesting]=useState(false)
  const [tab,setTab]=useState('ai')

  useEffect(()=>{
    api.get('/settings/ai').then(r=>{
      setForm({
        AI_BASE_URL: r.data.AI_BASE_URL||'',
        AI_API_KEY: r.data.AI_API_KEY||'',
        AI_MODEL: r.data.AI_MODEL||'',
        AI_TEMPERATURE: r.data.AI_TEMPERATURE||'0.2',
        AI_MAX_TOKENS: r.data.AI_MAX_TOKENS||'4096',
      })
    })
  },[])

  async function save(){
    await api.post('/settings/ai', form)
    setStatus({ok:true, msg:'Settings saved securely on server. Key never exposed to client JS.'})
    setTimeout(()=>setStatus(null),3000)
  }
  async function test(){
    setTesting(true); setStatus(null)
    try{
      const {data}= await api.post('/ai/test-connection', {base_url: form.AI_BASE_URL, api_key: form.AI_API_KEY?.startsWith('****')?'':form.AI_API_KEY, model: form.AI_MODEL})
      if(data.ok) setStatus({ok:true, msg:`✓ Connected — ${data.response || 'EDITOR CONNECTION OK'}`})
      else setStatus({ok:false, msg:`✕ ${data.error}: ${data.detail||''}`})
    } catch(e:any){
      setStatus({ok:false, msg: e.response?.data?.detail || e.message})
    } finally{ setTesting(false) }
  }

  return (
    <div className="p-8 max-w-[1080px] mx-auto">
      <h1 className="text-2xl font-bold">Settings</h1>
      <p className="text-sm text-slate-500">Configure your AI provider, security, storage and appearance. API keys are stored server-side only.</p>

      <div className="mt-6 flex gap-6">
        <div className="w-[200px] shrink-0 space-y-1">
          {[
            ['ai','AI Provider', SettingsIcon],
            ['general','General', SettingsIcon],
            ['storage','Storage', Database],
            ['security','Security', Shield],
            ['appearance','Appearance', Palette],
            ['shortcuts','Shortcuts', Keyboard],
          ].map(([id,label,Icon]:any)=>(
            <button key={id} onClick={()=>setTab(id)} className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium text-left ${tab===id?'bg-indigo-50 text-indigo-700 border border-indigo-200':'text-slate-600 hover:bg-slate-50'}`}>
              <Icon className="w-4 h-4"/> {label}
            </button>
          ))}
        </div>

        <div className="flex-1 bg-white rounded-2xl border border-slate-200 p-6">
          {tab==='ai' && (
            <div>
              <h3 className="font-semibold flex items-center gap-2">OpenAI-Compatible AI Provider <span className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-0.5 rounded-full">No Ollama • No local LLM</span></h3>
              <p className="text-xs text-slate-500 mt-1">Provide your own free API endpoint. The app proxies requests server-side — the key is never exposed via NEXT_PUBLIC or client JS.</p>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">Provider</label>
                  <input value="OpenAI Compatible" disabled className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm"/>
                  <div className="text-[11px] text-slate-500 mt-1">Uses POST /chat/completions — works with any OpenAI-compatible endpoint (OpenAI, Groq, OpenRouter, etc.)</div>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">API Base URL</label>
                  <input value={form.AI_BASE_URL} onChange={e=>setForm({...form, AI_BASE_URL:e.target.value})} placeholder="https://api.openai.com/v1 or https://example-provider.com/v1" className="mt-1 w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm"/>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">API Key</label>
                  <div className="mt-1 flex gap-2">
                    <input type={showKey?'text':'password'} value={form.AI_API_KEY} onChange={e=>setForm({...form, AI_API_KEY:e.target.value})} placeholder="sk-..." className="flex-1 border border-slate-200 rounded-xl px-3 py-2.5 text-sm"/>
                    <button onClick={()=>setShowKey(!showKey)} className="px-3 py-2 rounded-xl border border-slate-200 bg-white">{showKey?<EyeOff className="w-4 h-4"/>:<Eye className="w-4 h-4"/>}</button>
                  </div>
                  <div className="text-[11px] text-amber-600 flex items-center gap-1 mt-1"><AlertTriangle className="w-3 h-3"/> Stored server-side only. Never put AI_API_KEY in client JS or NEXT_PUBLIC.</div>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">Model</label>
                  <input value={form.AI_MODEL} onChange={e=>setForm({...form, AI_MODEL:e.target.value})} placeholder="gpt-4o-mini / llama-3.1-70b / free-model-name" className="mt-1 w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm"/>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">Temperature</label>
                    <input value={form.AI_TEMPERATURE} onChange={e=>setForm({...form, AI_TEMPERATURE:e.target.value})} className="mt-1 w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm"/>
                  </div>
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">Max Tokens</label>
                    <input value={form.AI_MAX_TOKENS} onChange={e=>setForm({...form, AI_MAX_TOKENS:e.target.value})} className="mt-1 w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm"/>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex gap-3">
                <button onClick={save} className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2"><Check className="w-4 h-4"/> Save Settings</button>
                <button onClick={test} disabled={testing} className="bg-white border border-slate-200 px-6 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50">{testing?'Testing...':'Test Connection'}</button>
              </div>
              {status && <div className={`mt-4 p-3 rounded-xl text-sm border flex items-center gap-2 ${status.ok?'bg-emerald-50 border-emerald-200 text-emerald-800':'bg-red-50 border-red-200 text-red-700'}`}>{status.ok?<Check className="w-4 h-4"/>:<X className="w-4 h-4"/>}{status.msg}</div>}

              <div className="mt-8 rounded-xl bg-slate-50 border border-slate-200 p-4">
                <div className="text-xs font-bold">How Test Works</div>
                <div className="text-xs text-slate-600 mt-1">Sends minimal request: “Respond with: EDITOR CONNECTION OK”. Surfaces errors: Invalid API key, Invalid base URL, Model not found, Rate limit, Timeout, Invalid response, Provider unavailable.</div>
              </div>
            </div>
          )}

          {tab!=='ai' && <div className="py-10 text-center text-sm text-slate-500">{tab} settings coming soon — core AI settings above are fully functional.</div>}
        </div>
      </div>
    </div>
  )
}
