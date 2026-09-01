import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import Editor from './pages/Editor'
import Settings from './pages/Settings'
import AiHistory from './pages/AiHistory'

function Placeholder({title}:{title:string}){
  return <div className="p-10 text-center text-slate-500"><div className="text-lg font-semibold">{title}</div><div className="text-sm mt-2">Coming soon</div></div>
}

export default function App(){
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar/>
        <div className="flex-1 min-w-0 bg-[#f8fafc]">
          <Routes>
            <Route path="/" element={<Dashboard/>}/>
            <Route path="/documents" element={<Documents/>}/>
            <Route path="/recent" element={<Documents/>}/>
            <Route path="/favorites" element={<Documents/>}/>
            <Route path="/trash" element={<Placeholder title="Trash"/>}/>
            <Route path="/templates" element={<Placeholder title="Templates"/>}/>
            <Route path="/editor/:id" element={<Editor/>}/>
            <Route path="/settings/ai" element={<Settings/>}/>
            <Route path="/settings" element={<Navigate to="/settings/ai"/>}/>
            <Route path="/ai/history" element={<AiHistory/>}/>
            <Route path="*" element={<div className="p-10">Not found</div>}/>
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
