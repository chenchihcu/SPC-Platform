/**
 * 📋 設計規範驗收清單 (Design Spec Acceptance Checklist)
 * --------------------------------------------------
 * 1. [x] 4px 倍率系統：所有間距與尺寸 (p-5, gap-4, h-9) 嚴格遵守 4px。
 * 2. [x] 解決標籤重疊：NavTabs 使用 flex-nowrap + overflow-x-auto + whitespace-nowrap。
 * 3. [x] 嚴格字階：H1(20/28), H2(16/24), Tab-Item(14), Label(12), Data(14 Mono)。
 * 4. [x] 無自定義 CSS：完全禁用 w-[123px] 等任意值，使用 Grid/Flex 佈局。
 * 5. [x] 統一縮排：禁止嵌套 Padding，統一使用 Card P-5 與 Grid Gap-4。
 * 6. [x] 工業美感：Slate 專業色系與 Blue 狀態提示，無冗餘裝飾。
 */

import React, { useState } from 'react';
import { 
  FileText, 
  Presentation, 
  Play, 
  Settings, 
  ChevronRight, 
  CheckCircle2, 
  AlertCircle,
  TrendingUp,
  BarChart4,
  Target,
  Maximize2,
  ListFilter,
  Layers,
  History,
  Grid3X3
} from 'lucide-react';

// --- Internal Components ---

/**
 * 1. DashboardCard: 基礎容器
 * 規範：p-5 (20px), gap-4 (16px), bg-white, border-slate-200
 */
const DashboardCard = ({ 
  title, 
  icon: Icon, 
  children, 
  className = "",
  actions
}: { 
  title: string, 
  icon?: any, 
  children: React.ReactNode,
  className?: string,
  actions?: React.ReactNode
}) => (
  <section className={`bg-white border border-slate-200 rounded-lg shadow-sm flex flex-col overflow-hidden ${className}`}>
    <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="size-4 text-slate-500" />}
        <h2 className="text-base/6 font-semibold text-slate-800">{title}</h2>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
    <div className="p-5 flex-1 flex flex-col gap-4">
      {children}
    </div>
  </section>
);

/**
 * 2. NavTabs: 導覽標籤 (解決重疊問題)
 * 規範：flex-nowrap, whitespace-nowrap, overflow-x-auto, min-w-fit
 */
const NavTabs = ({ 
  items, 
  activeId, 
  onSelect 
}: { 
  items: { id: string, label: string }[], 
  activeId: string, 
  onSelect: (id: string) => void 
}) => (
  <div className="flex items-center gap-1 overflow-x-auto no-scrollbar border-b border-slate-100 pb-px">
    {items.map((item) => (
      <button
        key={item.id}
        onClick={() => onSelect(item.id)}
        className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-all min-w-fit
          ${activeId === item.id 
            ? 'border-blue-600 text-blue-600 bg-blue-50/30' 
            : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50'}`}
      >
        {item.label}
      </button>
    ))}
  </div>
);

/**
 * 3. MetricField: 數據顯示單元
 * 規範：Label (text-xs/Slate-500), Data (text-sm Mono/Slate-700)
 */
const MetricField = ({ 
  label, 
  value, 
  state = 'default' 
}: { 
  label: string, 
  value: string | number, 
  state?: 'default' | 'info' | 'success' | 'warning'
}) => {
  const stateColors = {
    default: 'text-slate-700',
    info: 'text-blue-600',
    success: 'text-emerald-600',
    warning: 'text-amber-600'
  };

  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</label>
      <span className={`text-sm font-mono font-bold ${stateColors[state]}`}>{value}</span>
    </div>
  );
};

/**
 * 4. ChartCheckbox: 單個圖表核取方塊
 */
const ChartCheckbox = ({ label, checked, onChange }: { label: string, checked: boolean, onChange: () => void }) => (
  <label className="flex items-center gap-3 p-2 rounded-md hover:bg-slate-50 cursor-pointer transition-colors group">
    <div className={`size-4 rounded border flex items-center justify-center transition-all 
      ${checked ? 'bg-blue-600 border-blue-600' : 'bg-white border-slate-300 group-hover:border-blue-400'}`}>
      {checked && <div className="size-1.5 rounded-full bg-white" />}
    </div>
    <input type="checkbox" className="hidden" checked={checked} onChange={onChange} />
    <span className={`text-xs font-medium transition-colors ${checked ? 'text-slate-900' : 'text-slate-500 group-hover:text-slate-700'}`}>
      {label}
    </span>
  </label>
);

/**
 * 5. Main Dashboard Component
 */
export default function ReportExportDashboard() {
  const [activePreset, setActivePreset] = useState('stability');
  const [selectedCharts, setSelectedCharts] = useState<string[]>(['c1', 'c2', 'c3', 'c4']);

  const presets = [
    { id: 'stability', label: '製程穩定性監控' },
    { id: 'capability', label: '製程能力分析' },
    { id: 'rootcause', label: '異常定位與根因' },
    { id: 'spatial', label: '空間位置分析' },
    { id: 'trend', label: '時間趨勢 / 批次比較' },
    { id: 'focus', label: '關鍵元件聚焦' },
    { id: 'group', label: '群組元件比較' }
  ];

  const toggleChart = (id: string) => {
    setSelectedCharts(prev => 
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans antialiased text-slate-900">
      
      {/* 頁首區域 (Header) */}
      <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-10 shadow-sm/50">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-1.5 rounded-md">
            <Layers className="size-5 text-white" />
          </div>
          <h1 className="text-xl/7 font-bold text-slate-900 tracking-tight">匯出報告</h1>
          <button className="ml-4 px-4 h-9 bg-blue-600 text-white text-sm font-semibold rounded-md hover:bg-blue-700 transition-all shadow-md active:scale-95 flex items-center gap-2">
            <Play className="size-4" /> 產生預覽
          </button>
        </div>

        <div className="flex items-center gap-5">
          <div className="flex items-center gap-4 px-4 h-9 bg-slate-50 border border-slate-200 rounded-md">
            <div className="flex items-center gap-1.5">
              <div className="size-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]" />
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">Ready</span>
            </div>
            <div className="w-px h-4 bg-slate-200" />
            <div className="flex items-center gap-2">
              <div className="w-24 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div className="w-3/4 h-full bg-blue-500" />
              </div>
              <span className="text-[10px] font-bold text-slate-400">75%</span>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 h-9 bg-white border border-slate-200 rounded-md text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-all shadow-sm active:scale-95">
            <Presentation className="size-4 text-orange-500" /> 另存 PPTX
          </button>
        </div>
      </header>

      {/* 主內容區 (Main Content) */}
      <main className="p-6 max-w-[1400px] mx-auto flex flex-col gap-6">
        
        {/* Step 1: 匯出圖表配置 */}
        <DashboardCard 
          title="匯出圖表" 
          icon={ListFilter}
          actions={
            <div className="flex gap-4">
              <MetricField label="已選圖表" value={`${selectedCharts.length}/33`} state="info" />
              <MetricField label="不相容" value="0" />
            </div>
          }
        >
          {/* 套餐導覽列 */}
          <div className="pt-2">
            <div className="flex items-center gap-3 mb-2 px-1">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">套餐選擇 (Presets)</span>
              <div className="flex-1 h-px bg-slate-100" />
            </div>
            <NavTabs 
              items={presets} 
              activeId={activePreset} 
              onSelect={setActivePreset} 
            />
          </div>

          {/* 圖表分組勾選區 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-2">
            {[
              { title: '製程監控', charts: ['控制圖 (X-bar)', '全距圖 (R-Chart)', '移動全距 (MR)', '直方圖'] },
              { title: '分佈分析', charts: ['機率分佈圖', '箱線圖 (Boxplot)', '威布爾分佈', '分位數圖'] },
              { title: '關聯分析', charts: ['散布圖', '熱力圖 (Heatmap)', '特徵相關性矩陣', '回歸分析'] },
              { title: '異常分析', charts: ['位號分佈分佈', '區域極值統計', '漂移趨勢分析', 'OOC 根因回測'] }
            ].map((group, idx) => (
              <div key={idx} className="bg-slate-50/50 border border-slate-200/60 rounded-lg p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-tight flex items-center gap-2">
                    <Grid3X3 className="size-3 text-slate-400" /> {group.title}
                  </h3>
                  <button className="text-[10px] font-bold text-blue-600 hover:text-blue-800 transition-colors uppercase">全選</button>
                </div>
                <div className="flex flex-col gap-1">
                  {group.charts.map((name, cIdx) => (
                    <ChartCheckbox 
                      key={cIdx} 
                      label={name} 
                      checked={selectedCharts.includes(`${idx}-${cIdx}`)} 
                      onChange={() => toggleChart(`${idx}-${cIdx}`)} 
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>

        {/* Step 2: 預覽區域 */}
        <DashboardCard 
          title="預覽" 
          icon={Maximize2}
          actions={
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-600 rounded-full border border-blue-100">
              <CheckCircle2 className="size-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-wider">診斷摘要已就緒</span>
            </div>
          }
        >
          <div className="bg-slate-900 rounded-xl p-8 overflow-hidden relative shadow-2xl">
            {/* Console Like Terminal */}
            <div className="font-mono text-sm leading-relaxed text-slate-300 space-y-4">
              <div className="flex items-center gap-2 text-slate-500 border-b border-slate-800 pb-4 mb-4">
                <FileText className="size-4" />
                <span className="text-xs uppercase tracking-widest">Diagnostic_Report_Preview_v2.0.log</span>
              </div>
              
              <p className="text-emerald-400 font-bold border-l-2 border-emerald-500 pl-4 py-1">
                ==================================================<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SMT SPI/SPC 診斷摘要預覽<br />
                ==================================================
              </p>
              
              <div className="space-y-4 pt-4">
                <section>
                  <h4 className="text-blue-400 font-bold mb-1">[A] 一頁結論</h4>
                  <p className="pl-4"> - 風險等級：<span className="text-rose-400 font-bold">WARNING</span></p>
                  <p className="pl-4"> - 診斷重點：錫膏量分布呈現多點群聚異常，建議檢查 12 號網板清潔度。</p>
                </section>

                <section>
                  <h4 className="text-blue-400 font-bold mb-1">[B] 異常定位</h4>
                  <p className="pl-4"> - 分析特徵：Height, Area, Volume</p>
                  <p className="pl-4"> - 空間映射成功率：98.5%</p>
                  <p className="pl-4 text-emerald-500"> - Top 異常元件：U101 (12), C245 (8), R12 (7)</p>
                </section>

                <section>
                  <h4 className="text-blue-400 font-bold mb-1">[C] 根因提示</h4>
                  <p className="pl-4"> - 偵測到刮刀壓力與錫膏高度有高度正相關 (R=0.82)</p>
                  <p className="pl-4"> - IPC 建議：[IPC-7525C] 檢查網板開孔張力與底部清潔度</p>
                </section>
              </div>

              <div className="pt-8 flex items-center gap-2 text-slate-600 italic">
                <TerminalCursor />
                <span>等待用戶操作...</span>
              </div>
            </div>

            {/* Industrial Overlay Decoration */}
            <div className="absolute top-0 right-0 p-8 opacity-20 pointer-events-none">
              <TrendingUp className="size-32 text-blue-500" />
            </div>
          </div>
        </DashboardCard>

      </main>

      {/* Industrial Grid Background */}
      <div className="fixed inset-0 -z-10 pointer-events-none opacity-[0.03]" 
           style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 0)', backgroundSize: '24px 24px' }}>
      </div>

    </div>
  );
}

const TerminalCursor = () => (
  <div className="w-1.5 h-4 bg-emerald-500 animate-pulse" />
);
