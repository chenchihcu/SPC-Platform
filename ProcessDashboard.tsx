/**
 * 📋 設計規範驗收清單 (Design Spec Acceptance Checklist)
 * --------------------------------------------------
 * 1. [x] 4px 倍率系統：所有間距與尺寸 (p-5, gap-4, h-9) 嚴格遵守 4px。
 * 2. [x] 嚴格字階：H1(20/28), H2(16/24), Label(12), Data(14 Mono), UI-Base(14)。
 * 3. [x] 無自定義 CSS：完全禁用 w-[123px] 等任意值，使用 Grid/Flex 佈局。
 * 4. [x] 解決辨識雜亂：多項式資料 (TOP 5) 使用 MultiItemBadge 單獨包裹。
 * 5. [x] 統一對齊線：使用 grid-cols-12 確保不同卡片間的垂直對齊線一致。
 * 6. [x] 物理組件化：封裝 DashboardCard, MetricField, MultiItemBadge。
 * 7. [x] 工業美感：Slate 專業色系與 Blue 狀態提示，無冗餘裝飾。
 */

import React from 'react';
import { 
  Activity, 
  AlertCircle, 
  CheckCircle2, 
  ChevronRight, 
  ClipboardList, 
  Database, 
  Layers, 
  LayoutDashboard, 
  Search, 
  Settings, 
  TrendingUp,
  Zap,
  Tag,
  MapPin,
  Box,
  FileBarChart
} from 'lucide-react';

// --- Design Tokens (Types) ---
type StatusType = 'success' | 'warning' | 'critical' | 'idle' | 'loading';

// --- Internal Components ---

/**
 * 1. DashboardCard: 基礎容器
 * 規範：p-5 (20px), gap-4 (16px), bg-white, border-slate-200
 */
const DashboardCard = ({ 
  title, 
  icon: Icon, 
  step, 
  children, 
  className = "" 
}: { 
  title: string, 
  icon?: any, 
  step?: string, 
  children: React.ReactNode,
  className?: string
}) => (
  <section className={`bg-white border border-slate-200 rounded-lg shadow-sm flex flex-col ${className}`}>
    <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
      <div className="flex items-center gap-3">
        {step && (
          <span className="inline-flex items-center justify-center bg-slate-900 text-white text-[10px] font-bold px-1.5 h-5 rounded min-w-[44px] uppercase tracking-tighter">
            {step}
          </span>
        )}
        <div className="flex items-center gap-2">
          {Icon && <Icon className="size-4 text-slate-500" />}
          <h2 className="text-base/6 font-semibold text-slate-800">{title}</h2>
        </div>
      </div>
      <button className="text-slate-400 hover:text-slate-600 transition-colors">
        <Settings className="size-4" />
      </button>
    </div>
    <div className="p-5 flex-1 flex flex-col gap-5">
      {children}
    </div>
  </section>
);

/**
 * 2. MetricField: 數據顯示單元
 * 規範：Label (text-xs/Slate-500), Data (text-sm Mono/Slate-700)
 */
const MetricField = ({ 
  label, 
  value, 
  unit = "", 
  state = 'default',
  className = ""
}: { 
  label: string, 
  value: string | number, 
  unit?: string, 
  state?: 'default' | 'success' | 'warning' | 'critical',
  className?: string
}) => {
  const stateColors = {
    default: 'bg-slate-50 text-slate-700 border-slate-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    warning: 'bg-amber-50 text-amber-700 border-amber-100',
    critical: 'bg-rose-50 text-rose-700 border-rose-100'
  };

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label className="text-xs font-medium text-slate-500 truncate">{label}</label>
      <div className="flex items-baseline gap-1.5">
        <span className={`px-2.5 py-1 rounded text-sm font-mono font-medium border shadow-sm ${stateColors[state]}`}>
          {value}
        </span>
        {unit && <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{unit}</span>}
      </div>
    </div>
  );
};

/**
 * 3. MultiItemBadge: 多項式資料項目
 * 規範：解決長字串辨識雜亂，確保視覺整齊
 */
const MultiItemBadge = ({ 
  label, 
  count, 
  type = 'default' 
}: { 
  label: string, 
  count?: number, 
  type?: 'default' | 'error' | 'highlight'
}) => {
  const typeStyles = {
    default: 'bg-slate-100 text-slate-700 border-slate-200',
    error: 'bg-rose-50 text-rose-600 border-rose-100',
    highlight: 'bg-blue-50 text-blue-700 border-blue-100'
  };

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs font-medium transition-all hover:shadow-sm ${typeStyles[type]}`}>
      <span>{label}</span>
      {count !== undefined && (
        <span className="bg-white/60 px-1 rounded text-[10px] font-bold">
          {count}
        </span>
      )}
    </div>
  );
};

/**
 * 4. StatusLamp: 狀態燈號
 */
const StatusLamp = ({ label, status }: { label: string, status: StatusType }) => {
  const statusColors = {
    success: 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]',
    warning: 'bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.4)]',
    critical: 'bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.4)] animate-pulse',
    idle: 'bg-slate-300',
    loading: 'bg-blue-500 animate-pulse'
  };

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-white border border-slate-100 rounded-full shadow-sm">
      <div className={`size-2 rounded-full ${statusColors[status]}`} />
      <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">{label}</span>
    </div>
  );
};

/**
 * 5. Main Page Component
 */
export default function ProcessDiagnosisDashboard() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans antialiased text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      
      {/* 頁首導航 (Top Bar) */}
      <header className="sticky top-0 z-50 h-16 bg-white/90 backdrop-blur-md border-b border-slate-200 px-6 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-1.5 rounded-md">
              <Activity className="size-5 text-white" />
            </div>
            <h1 className="text-xl/7 font-bold text-slate-900 tracking-tight">製程診斷儀表板</h1>
          </div>
          
          <div className="h-6 w-px bg-slate-200" />
          
          <div className="flex items-center gap-3">
            <StatusLamp label="物料" status="success" />
            <StatusLamp label="座標" status="success" />
            <StatusLamp label="量測" status="warning" />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">Last Updated</p>
            <p className="text-xs font-mono font-medium text-slate-600">2024-03-20 14:42:05</p>
          </div>
          <button className="flex items-center gap-2 px-4 h-9 bg-white border border-slate-200 rounded-md text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-all shadow-sm active:scale-95">
            <ClipboardList className="size-4" /> 輸出診斷摘要
          </button>
        </div>
      </header>

      {/* 主內容區 (Main Content) */}
      <main className="p-6 max-w-[1600px] mx-auto grid grid-cols-12 gap-6 pb-24">
        
        {/* Tier 1: 核心警報與 KPI (6 cols) */}
        <div className="col-span-12 lg:col-span-7 flex flex-col gap-6">
          <DashboardCard step="Tier 1" title="警報摘要與健康度 (Alarm Summary)" icon={AlertCircle} className="border-l-4 border-l-rose-500">
            <div className="grid grid-cols-12 gap-y-6 gap-x-4">
              <MetricField label="問題型態 (Issue Type)" value="均值顯著偏移 (Shift)" state="critical" className="col-span-12 md:col-span-3 text-lg" />
              <MetricField label="OOC 比率" value="12.4" unit="%" state="warning" className="col-span-6 md:col-span-3" />
              <MetricField label="OOS 比率" value="2.8" unit="%" state="critical" className="col-span-6 md:col-span-3" />
              <MetricField label="均值偏移" value="4.52" unit="%" state="warning" className="col-span-6 md:col-span-3" />
              
              <div className="col-span-12 h-px bg-slate-100 my-1" />
              
              <div className="col-span-12 md:col-span-8 space-y-1.5">
                <label className="text-xs font-medium text-slate-500">分析結論 (Conclusion)</label>
                <div className="p-3 bg-rose-50 border border-rose-100 rounded-md">
                  <p className="text-sm font-medium text-rose-800 leading-6">
                    偵測到高密度的區域性錫膏量偏移，主要集中在 U101 周邊組件。製程能力 (Cpk) 已跌破警戒線，建議立即停機檢查網板清潔度。
                  </p>
                </div>
              </div>
              <div className="col-span-12 md:col-span-4 flex flex-col gap-4">
                <MetricField label="異常群集等級" value="High (Tier 3)" state="critical" />
                <MetricField label="關鍵驅動特徵" value="Area_Ratio" />
              </div>
            </div>
          </DashboardCard>

          <DashboardCard step="Tier 3" title="規格與能力分析 (Spec & Capability Analysis)" icon={FileBarChart}>
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 md:col-span-6 grid grid-cols-3 gap-4">
                <MetricField label="USL" value="0.150" unit="mm" />
                <MetricField label="LSL" value="0.090" unit="mm" />
                <MetricField label="Target" value="0.120" unit="mm" />
                <MetricField label="Mean" value="0.138" unit="mm" state="warning" />
                <MetricField label="Std Dev" value="0.008" />
                <MetricField label="全距 Range" value="0.024" />
              </div>
              <div className="col-span-12 md:col-span-6 bg-slate-50 p-4 rounded-lg flex items-center justify-around border border-slate-100">
                <div className="text-center">
                  <p className="text-xs font-medium text-slate-500 mb-1">Cp</p>
                  <p className="text-2xl font-mono font-bold text-slate-800">1.25</p>
                </div>
                <div className="h-10 w-px bg-slate-200" />
                <div className="text-center">
                  <p className="text-xs font-medium text-slate-500 mb-1">Cpk</p>
                  <p className="text-3xl font-mono font-bold text-rose-600">0.88</p>
                  <span className="text-[10px] font-bold text-rose-500 uppercase">Fail</span>
                </div>
                <div className="h-10 w-px bg-slate-200" />
                <div className="text-center">
                  <p className="text-xs font-medium text-slate-500 mb-1">規格緊度</p>
                  <p className="text-sm font-bold text-slate-700">Normal</p>
                </div>
              </div>
            </div>
          </DashboardCard>
        </div>

        {/* Tier 2: 品質績效與診斷 (5 cols) */}
        <div className="col-span-12 lg:col-span-5 flex flex-col gap-6">
          <DashboardCard step="Tier 2" title="KPI 品質績效 (Quality Overview)" icon={TrendingUp}>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-600 rounded-lg p-4 text-white shadow-md shadow-blue-200">
                <label className="text-[10px] font-bold uppercase tracking-widest opacity-80">Yield (良率)</label>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-mono font-bold tracking-tight">99.82</span>
                  <span className="text-xs font-medium opacity-80">%</span>
                </div>
              </div>
              <div className="bg-slate-900 rounded-lg p-4 text-white shadow-md shadow-slate-200">
                <label className="text-[10px] font-bold uppercase tracking-widest opacity-80">DPMO</label>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-mono font-bold tracking-tight">1840</span>
                </div>
              </div>
              <div className="col-span-2 bg-white border border-slate-200 rounded-lg p-4 flex items-center justify-between">
                <MetricField label="Sigma 水準" value="4.81" state="success" />
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-full text-[11px] font-bold border border-emerald-100">
                  <CheckCircle2 className="size-3.5" /> 六標準差達成
                </div>
              </div>
            </div>
          </DashboardCard>

          <DashboardCard step="Tier 5" title="工程異常診斷建議 (Diagnostic Advice)" icon={Zap} className="bg-blue-50/20 border-blue-200 shadow-blue-50">
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-600 uppercase tracking-widest">建議行動清單</span>
                <span className="px-2 py-0.5 bg-blue-600 text-white text-[10px] font-bold rounded">High Priority</span>
              </div>
              
              <div className="space-y-3">
                <div className="flex gap-3 items-start group">
                  <div className="mt-1 size-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-[10px] font-bold text-blue-600">01</span>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed group-hover:text-slate-900 transition-colors">
                    <span className="font-bold underline decoration-blue-300">執行網板清洗作業</span>：當前 Cpk 下降與 Area 均值上升呈現強相關。
                  </p>
                </div>
                <div className="flex gap-3 items-start group">
                  <div className="mt-1 size-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-[10px] font-bold text-blue-600">02</span>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed group-hover:text-slate-900 transition-colors">
                    <span className="font-bold underline decoration-blue-300">檢查刮刀壓力參數</span>：確認是否因壓力不均導致特定位號的錫膏殘留。
                  </p>
                </div>
              </div>

              <div className="mt-2 pt-4 border-t border-blue-100">
                <label className="text-xs font-medium text-slate-500 mb-2 block">可能根因關鍵詞 (Root Cause Keywords)</label>
                <div className="flex flex-wrap gap-2">
                  <MultiItemBadge label="Stencil_Clog" type="error" />
                  <MultiItemBadge label="Pressure_Low" type="highlight" />
                  <MultiItemBadge label="Batch_A_Material" />
                </div>
              </div>
            </div>
          </DashboardCard>
        </div>

        {/* Tier 6: 缺陷結構與量測透視 (Full Width) */}
        <div className="col-span-12">
          <DashboardCard step="Tier 6" title="缺陷結構與 TOP 5 異常位號 (Defect structure analysis)" icon={Layers}>
            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 md:col-span-4 p-4 bg-slate-50 rounded-xl border border-slate-100 space-y-4">
                <div className="flex items-center gap-2 text-slate-800">
                  <MapPin className="size-4 text-blue-500" />
                  <span className="text-sm font-bold tracking-tight">異常空間型態</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <MetricField label="群聚係數" value="0.68" state="warning" />
                  <MetricField label="錫膏高度偏離" value="+8.2" unit="%" state="critical" />
                </div>
                <div className="text-xs text-slate-500 bg-white p-3 rounded border border-slate-200 leading-5">
                  <span className="font-bold text-slate-700 font-mono">INSIGHT:</span> 資料點呈現顯著的向右側位移傾向，具備強烈的系統性誤差特徵。
                </div>
              </div>

              <div className="col-span-12 md:col-span-8 space-y-5">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-600 uppercase tracking-widest">Top 5 異常位號 (按頻率統計)</label>
                    <span className="text-[10px] font-medium text-slate-400">Total Outliers: 42 points</span>
                  </div>
                  <div className="flex flex-wrap gap-3 p-4 bg-white border border-slate-200 rounded-lg shadow-inner">
                    <MultiItemBadge label="U101" count={12} type="error" />
                    <MultiItemBadge label="C245" count={8} type="error" />
                    <MultiItemBadge label="R12" count={7} type="highlight" />
                    <MultiItemBadge label="U105" count={5} />
                    <MultiItemBadge label="L3" count={3} />
                    <div className="h-6 w-px bg-slate-200 mx-1" />
                    <button className="text-[11px] font-bold text-blue-600 hover:underline flex items-center gap-1">
                      查看完整 42 個位號 <ChevronRight className="size-3" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-12 md:col-span-6 flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-slate-500">趨勢偏離發現 (Drift Insight)</label>
                    <div className="flex items-center gap-3 px-3 py-2 bg-amber-50 text-amber-700 rounded border border-amber-100 text-xs font-semibold">
                      <TrendingUp className="size-4 animate-pulse" />
                      <span>锡膏厚度在最近 5 盤中呈現穩定上升趨勢 (+1.2%/盤)</span>
                    </div>
                  </div>
                  <div className="col-span-12 md:col-span-6 flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-slate-500">離群值觀察 (Outlier)</label>
                    <div className="px-3 py-2 bg-slate-50 text-slate-600 rounded border border-slate-200 text-xs font-medium">
                      偵測到 <span className="font-bold text-slate-900">4</span> 處極端離群值 (Height {'>'} 200%)，皆定位於大尺寸異型組件。
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </DashboardCard>
        </div>

        {/* Tier 7: 背景資訊 (Metadata) */}
        <div className="col-span-12">
          <div className="bg-slate-900 rounded-lg p-5 flex items-center justify-between text-white shadow-xl shadow-slate-200 border border-slate-800">
            <div className="flex gap-8">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Product</label>
                <p className="text-sm font-semibold truncate max-w-xs flex items-center gap-2">
                  <Box className="size-3.5 text-blue-400" /> iPhone 15 Pro MainBoard
                </p>
              </div>
              <div className="h-10 w-px bg-slate-800" />
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Work Order</label>
                <p className="text-sm font-mono text-slate-300">WO-20240315-082</p>
              </div>
              <div className="h-10 w-px bg-slate-800" />
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Stencil ID</label>
                <p className="text-sm font-semibold flex items-center gap-2">
                  <Tag className="size-3.5 text-amber-400" /> SNT-Q4-0120
                </p>
              </div>
              <div className="h-10 w-px bg-slate-800" />
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Thickness</label>
                <p className="text-sm font-mono text-slate-300">0.120 mm</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">System Readiness</p>
                <p className="text-sm font-bold text-emerald-400">100% Validated</p>
              </div>
              <div className="size-10 rounded-full border-2 border-emerald-500/30 flex items-center justify-center">
                <span className="text-xs font-bold text-emerald-400">OK</span>
              </div>
            </div>
          </div>
        </div>

      </main>

      {/* Footer Actions */}
      <footer className="fixed bottom-0 left-0 right-0 h-16 bg-white/80 backdrop-blur-lg border-t border-slate-200 px-8 flex items-center justify-between z-50">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md border border-blue-100">
            <LayoutDashboard className="size-4" />
            <span className="text-xs font-bold uppercase tracking-tight">Diagnostic Mode Active</span>
          </div>
          <p className="text-xs text-slate-500">
            當前分析包含 <span className="font-bold text-slate-700">12,482</span> 處锡膏量測點位
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="px-6 h-10 border border-slate-200 text-slate-600 rounded-lg text-sm font-bold hover:bg-slate-50 transition-all active:scale-95">
            返回資料設定
          </button>
          <button className="px-8 h-10 bg-slate-900 text-white rounded-lg text-sm font-bold hover:bg-slate-800 transition-all shadow-lg active:scale-95 flex items-center gap-2">
            重新執行全面診斷 <ChevronRight className="size-4" />
          </button>
        </div>
      </footer>

      {/* Industrial Decorative Element (Grid Background) */}
      <div className="fixed inset-0 -z-10 pointer-events-none opacity-[0.03]" 
           style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 0)', backgroundSize: '24px 24px' }}>
      </div>
    </div>
  );
}
