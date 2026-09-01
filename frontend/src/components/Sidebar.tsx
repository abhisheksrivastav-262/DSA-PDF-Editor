import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Files, Clock3, Heart, Bot, Trash2, Settings, FileText, History, Search } from 'lucide-react'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/documents', label: 'Documents', icon: Files },
  { to: '/recent', label: 'Recent Files', icon: Clock3 },
  { to: '/favorites', label: 'Favorites', icon: Heart },
  { to: '/ai/history', label: 'AI History', icon: History },
  { to: '/templates', label: 'Templates', icon: FileText },
  { to: '/trash', label: 'Trash', icon: Trash2 },
  { to: '/settings/ai', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="w-[260px] shrink-0 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0">
      <div className="px-6 py-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-[16px]">E</div>
          <div>
            <div className="font-bold tracking-tight leading-none">EDITOR</div>
            <div className="text-[11px] text-slate-500 tracking-widest uppercase">AI PDF Editor</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {nav.map(i => (
          <NavLink key={i.to} to={i.to} className={({isActive})=> `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}>
            <i.icon className="w-[18px] h-[18px]" /> {i.label}
          </NavLink>
        ))}
        <div className="pt-4 mt-4 border-t border-slate-100">
          <div className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-widest">Storage</div>
          <div className="mx-3 mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div className="text-xs text-slate-600">Documents & Versions</div>
            <div className="mt-2 h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full w-[45%] bg-indigo-600" />
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Powered by pdf-edit-engine</div>
          </div>
        </div>
      </nav>
      <div className="p-4 border-t border-slate-100">
        <div className="flex items-center gap-3">
          <img src="https://i.pravatar.cc/100?img=12" className="w-8 h-8 rounded-full" />
          <div>
            <div className="text-sm font-medium">Admin</div>
            <div className="text-xs text-slate-500">admin@editor.local</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
