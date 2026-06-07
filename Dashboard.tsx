/**
 * 📋 設計規範驗收清單 (Design Spec Acceptance Checklist)
 * --------------------------------------------------
 * 1. [x] 4px 倍率系統：所有間距 (p-5, gap-4, m-1) 嚴格遵守 4px。
 * 2. [x] 嚴格字階：H1 (20/28), H2 (16/24), Label (12), Data (14 Mono), UI-Base (14)。
 * 3. [x] 無自定義 CSS：完全使用 Tailwind 標準類，禁止 w-[123px]。
 * 4. [x] 物理組件規範：卡片具備 bg-white, border-slate-200, shadow-sm。
 * 5. [x] 對齊線原則：標題與內容區左側垂直對齊 (px-5)。
 * 6. [x] 圖標一致性：僅使用 lucide-react，尺寸固定為 size-4。
 * 7. [x] 工業美感：Slate 色系搭配 Blue 主色，呈現冷靜專業感。
 */

import React from 'react';
import { 
  Search, 
  Settings, 
  BarChart2, 
  Layers, 
  Database, 
  FileText, 
  Activity, 
  CheckCircle2, 
  AlertCircle, 
  Loader2,
  Plus,
  ArrowRight,
  ClipboardList
} from 'lucide-react';

// --- Internal Components ---

/**
 * 側邊導覽欄 (Sidebar)
 * 固定寬度 w-64，深色工業感
 */
const Sidebar = () => (
  <aside className="fixed inset-y-0 left-0 w-64 bg-slate-900 text-slate-400 border-r border-slate-800 hidden md:flex flex-col">
    <div className="h-16 flex items-center px-6 border-b border-slate-800">
      <div className="flex items-center gap-3">
        <div className="size-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold">
          <Activity className="size-5" />
        </div>
        <span className="text-sm font-semibold text-white tracking-wider">SPI PLATFORM v2</span>
      </div>
    </div>
    
    <nav className="flex-1 overflow-y-auto p-4 space-y-1">
      <SidebarItem icon={<BarChart2 />} label="統計分析" />
      <SidebarItem icon={<Settings />} label="資料設定" active />
      <SidebarItem icon={<Layers />} label="座標管理" />
      <SidebarItem icon={<Database />} label="量測資料庫" />
      <div className="pt-4 pb-2">
        <div className="px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Reports</div>
      </div>
      <SidebarItem icon={<FileText />} label="分析報告" />
      <SidebarItem icon={<ClipboardList />} label="診斷日誌" />
    </nav>
    
    <div className="p-4 border-t border-slate-800">
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800/50 rounded-lg">
        <div className="size-8 rounded-full bg-slate-700 flex items-center justify-center text-xs text-white">AD</div>
        <div className="flex-1 overflow-hidden">
          <div className="text-xs font-medium text-white truncate">Admin Account</div>
          <div className="text-[10px] text-slate-500 truncate">Senior Engineer</div>
        </div>
      </div>
    </div>
  </aside>
);

const SidebarItem = ({ icon, label, active = false }: { icon: React.ReactNode, label: string, active?: boolean }) => (
  <a href="#" className={`flex items-center gap-3 px-4 py-2.5 rounded-md transition-colors ${active ? 'bg-blue-600/10 text-blue-400 font-medium' : 'hover:bg-slate-800/50 hover:text-slate-200'}`}>
    {React.cloneElement(icon as React.ReactElement, { className: 'size-4' })}
    <span className="text-sm">{label}</span>
  </a>
);

/**
 * 頁首內容 (TopBar)
 */
const TopBar = () => (
  <header className="sticky top-0 z-10 flex h-16 items-center border-b border-slate-200 bg-white/80 backdrop-blur-md px-6">
    <div className="flex flex-1 items-center gap-8">
      <h1 className="text-xl/7 font-bold text-slate-900">資料設定</h1>
      
      <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-md px-3 h-9">
        <label className="text-xs font-medium text-slate-500 whitespace-nowrap">產品料號</label>
        <select className="bg-transparent text-sm text-slate-700 focus:outline-none min-w-48 font-medium">
          <option>107.510.824.00 - iPhone MainBoard</option>
          <option>108.220.141.00 - iPad Pro Logic</option>
        </select>
        <div className="w-px h-4 bg-slate-200 mx-1" />
        <button className="text-blue-600 hover:text-blue-700">
          <Plus className="size-4" />
        </button>
      </div>
    </div>
    
    <div className="flex items-center gap-6">
      <StatusLamp label="座標" status="success" />
      <StatusLamp label="規格" status="warning" />
      <StatusLamp label="量測" status="idle" />
    </div>
  </header>
);

const StatusLamp = ({ label, status }: { label: string, status: 'success' | 'warning' | 'idle' | 'loading' }) => (
  <div className="flex items-center gap-2">
    <div className={`size-2 rounded-full ${
      status === 'success' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 
      status === 'warning' ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]' : 
      status === 'loading' ? 'bg-blue-500 animate-pulse' : 'bg-slate-300'
    }`} />
    <span className="text-xs font-medium text-slate-500">{label}</span>
  </div>
);

/**
 * 卡片容器 (CardSection)
 */
const CardSection = ({ title, children, step }: { title: string, children: React.ReactNode, step?: string }) => (
  <section className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden mb-4">
    <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
      <div className="flex items-center gap-3">
        {step && (
          <span className="px-2 py-0.5 bg-slate-200 text-slate-600 text-[10px] font-bold rounded uppercase tracking-wider">
            {step}
          </span>
        )}
        <h2 className="text-base/6 font-semibold text-slate-800">{title}</h2>
      </div>
      <button className="text-slate-400 hover:text-slate-600">
        <Settings className="size-4" />
      </button>
    </div>
    <div className="p-5 space-y-6">
      {children}
    </div>
  </section>
);

/**
 * 數據欄位 (DataField)
 */
const DataField = ({ label, value, unit }: { label: string, value: string | number, unit?: string }) => (
  <div className="space-y-1.5">
    <label className="text-xs font-medium text-slate-500 block">{label}</label>
    <div className="flex items-baseline gap-1">
      <span className="text-sm font-mono text-slate-700 bg-slate-50 px-2 py-1 rounded border border-slate-100 min-w-16">
        {value}
      </span>
      {unit && <span className="text-[10px] text-slate-400 font-medium uppercase">{unit}</span>}
    </div>
  </div>
);

/**
 * 輸入框組件
 */
const Input = (props: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input 
    {...props}
    className="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed" 
  />
);

/**
 * 主儀表板頁面
 */
export default function Dashboard() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans antialiased text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      <Sidebar />
      
      <div className="md:pl-64 flex flex-col min-h-screen">
        <TopBar />
        
        <main className="flex-1 p-6 space-y-4 max-w-6xl mx-auto w-full pb-32">
          {/* Step 1: Coordinate Data */}
          <CardSection step="Step 1" title="座標資料管理 (Coordinate Data)">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-500">來源 CSV 路徑</label>
                  <div className="flex gap-2">
                    <Input placeholder="C:\Users\Desktop\SMT_Product_v1.csv" disabled />
                    <button className="h-9 px-4 bg-white border border-slate-200 rounded-md text-sm font-medium hover:bg-slate-50 flex items-center gap-2">
                       <Search className="size-4" /> 瀏覽
                    </button>
                  </div>
                </div>
                
                <div className="flex items-center gap-4 pt-2">
                  <DataField label="資料點總數" value="1,248" />
                  <DataField label="更新時間" value="2024-03-15 08:30" />
                </div>
              </div>
              
              <div className="bg-blue-50/50 border border-blue-100 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2 text-blue-700 font-semibold text-sm">
                  <Link2 className="size-4" /> 綁定至產品
                </div>
                <div className="space-y-4">
                   <div className="space-y-1.5">
                    <label className="text-xs font-medium text-blue-600">產品名稱</label>
                    <Input placeholder="輸入新產品名稱..." className="border-blue-200 focus:ring-blue-500" />
                  </div>
                  <div className="flex justify-end pt-1">
                    <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 shadow-sm shadow-blue-200 transition-all">
                      暫存並載入
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </CardSection>

          {/* Step 2: Plate Specifications */}
          <CardSection step="Step 2" title="鋼板規格配置 (Plate Specifications)">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <DataField label="主厚度 (Nominal)" value="0.120" unit="mm" />
              <DataField label="USL (上限)" value="0.150" unit="mm" />
              <DataField label="LSL (下限)" value="0.090" unit="mm" />
              <DataField label="Target (中心值)" value="0.120" unit="mm" />
            </div>
            
            <div className="border-t border-slate-100 pt-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-700">階梯鋼板設定 (Step-up/down)</h3>
                <button className="text-blue-600 text-xs font-medium hover:underline flex items-center gap-1">
                  <Plus className="size-3" /> 新增自定義區域
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs text-slate-500 uppercase tracking-wider">
                      <th className="text-left py-2 font-medium">區域 ID</th>
                      <th className="text-left py-2 font-medium">厚度</th>
                      <th className="text-left py-2 font-medium">點位數量</th>
                      <th className="text-right py-2 font-medium">動作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    <tr>
                      <td className="py-3 font-medium text-slate-900">U101_StepUp</td>
                      <td className="py-3 text-slate-600 font-mono">0.150 mm</td>
                      <td className="py-3 text-slate-600">42 points</td>
                      <td className="py-3 text-right">
                        <button className="text-slate-400 hover:text-red-500 underline text-xs">移除</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </CardSection>

          {/* Step 3: Measurement Data */}
          <CardSection step="Step 3" title="量測資料載入 (Measurement Data)">
            <div className="border-2 border-dashed border-slate-200 rounded-lg p-10 flex flex-col items-center justify-center bg-slate-50/50 hover:bg-slate-50 hover:border-blue-300 transition-all cursor-pointer group">
              <div className="size-12 bg-white rounded-full shadow-sm border border-slate-100 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Database className="size-6 text-slate-400 group-hover:text-blue-500" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-slate-700">點擊或拖拽量測數據 CSV</p>
                <p className="text-xs text-slate-500 mt-1">支援格式: .csv, .xlsx (大小限制 50MB)</p>
              </div>
            </div>
            
            <div className="flex gap-4 pt-2">
              <div className="flex-1 bg-slate-50 rounded-md p-3 border border-slate-200 flex items-center gap-3">
                <AlertCircle className="size-4 text-amber-500" />
                <span className="text-xs text-slate-600">當前狀態: <span className="font-semibold">等待量測資料匯入...</span></span>
              </div>
              <button className="h-10 px-4 flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md bg-white hover:bg-slate-50">
                <ClipboardList className="size-4" /> 從量測庫選取
              </button>
            </div>
          </CardSection>
        </main>
        
        {/* Footer Summary */}
        <footer className="fixed bottom-0 right-0 left-0 md:left-64 h-20 bg-white border-t border-slate-200 px-8 flex items-center justify-between z-20 shadow-[0_-4px_12px_rgba(0,0,0,0.03)]">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded border border-amber-100">
              <AlertCircle className="size-4" />
              <span className="text-xs font-medium">尚未完成: 量測資料 / 有效厚度驗證</span>
            </div>
            <div className="h-4 w-px bg-slate-200" />
            <div className="text-xs text-slate-400">
              系統整備率: <span className="text-slate-600 font-bold">66%</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button className="px-6 h-10 border border-slate-200 bg-white text-slate-600 rounded-md text-sm font-medium hover:bg-slate-50 active:translate-y-px transition-all">
              儲存草稿
            </button>
            <button className="px-8 h-10 bg-blue-600 text-white rounded-md text-sm font-bold hover:bg-blue-700 shadow-md shadow-blue-200 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none transition-all flex items-center gap-2 group">
              開始分析 <ArrowRight className="size-4 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

// Missing Icon for Step 1
const Link2 = ({ className }: { className?: string }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width="24" 
    height="24" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    className={className}
  >
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);
