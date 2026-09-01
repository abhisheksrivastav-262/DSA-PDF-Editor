import { useEffect, useRef, useState } from 'react'
import * as pdfjs from 'pdfjs-dist'
// Use CDN worker
// @ts-ignore
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

export default function PdfViewer({ url, onSelectText, onPageChange }: { url: string, onSelectText?: (t:string)=>void, onPageChange?: (n:number)=>void }){
  const containerRef = useRef<HTMLDivElement>(null)
  const [numPages,setNumPages]=useState(0)
  const [scale,setScale]=useState(1.2)
  const [page,setPage]=useState(1)

  useEffect(()=>{
    let cancelled=false
    async function render(){
      if(!url || !containerRef.current) return
      containerRef.current.innerHTML=''
      const pdf = await pdfjs.getDocument(url).promise
      if(cancelled) return
      setNumPages(pdf.numPages)
      for(let i=1;i<=pdf.numPages;i++){
        const pg = await pdf.getPage(i)
        const viewport = pg.getViewport({scale})
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')!
        canvas.width = viewport.width
        canvas.height = viewport.height
        canvas.style.width = '100%'
        canvas.style.maxWidth = `${viewport.width}px`
        canvas.style.marginBottom='16px'
        canvas.style.boxShadow='0 10px 30px rgba(0,0,0,0.08)'
        canvas.style.borderRadius='12px'
        canvas.style.background='white'
        canvas.dataset.page = String(i)
        await pg.render({canvasContext: ctx, viewport}).promise
        // text layer for selection
        const textContent = await pg.getTextContent()
        const textDiv = document.createElement('div')
        textDiv.style.position='relative'
        textDiv.style.marginBottom='16px'
        // wrap canvas + selectable transparent layer
        const wrap = document.createElement('div')
        wrap.style.position='relative'
        wrap.appendChild(canvas)
        // overlay text layer
        const textLayerDiv = document.createElement('div')
        textLayerDiv.style.position='absolute'
        textLayerDiv.style.left='0'; textLayerDiv.style.top='0'
        textLayerDiv.style.width=`${viewport.width}px`; textLayerDiv.style.height=`${viewport.height}px`
        textLayerDiv.style.transformOrigin='0 0'
        textLayerDiv.style.pointerEvents='auto'
        textLayerDiv.className='textLayer'

        containerRef.current!.appendChild(wrap)
        // simple click to set current page
        wrap.addEventListener('click',()=>{ setPage(i); onPageChange?.(i)})
      }
    }
    render()
    return ()=>{ cancelled=true }
  },[url, scale])

  useEffect(()=>{
    const onMouseUp=()=>{
      const sel = window.getSelection()?.toString() || ''
      if(sel.trim() && onSelectText) onSelectText(sel.trim().slice(0,2000))
    }
    document.addEventListener('mouseup', onMouseUp)
    return ()=>document.removeEventListener('mouseup', onMouseUp)
  },[onSelectText])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="text-xs text-slate-600">Page {page} / {numPages}</div>
        <div className="flex items-center gap-2">
          <button onClick={()=>setScale(s=>Math.max(0.6,s-0.15))} className="px-2 py-1 rounded bg-slate-100 text-sm">−</button>
          <span className="text-xs w-12 text-center">{Math.round(scale*100)}%</span>
          <button onClick={()=>setScale(s=>Math.min(2.5,s+0.15))} className="px-2 py-1 rounded bg-slate-100 text-sm">+</button>
        </div>
      </div>
      <div ref={containerRef} className="flex-1 overflow-auto p-6 bg-[#eef2f7] flex flex-col items-center">
        <div className="text-sm text-slate-400 py-10">Loading PDF...</div>
      </div>
    </div>
  )
}
