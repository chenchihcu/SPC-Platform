# SPI 鋼板開窗文件格式相容性

研究日期：2026-07-16\
用途：界定市售 SPI／鋼板 CAM 常見輸入、SPC Platform 已實作契約與安全拒絕邊界。

## 1. 結論

市售 SPI 的共同交集是 Paste Gerber；部分整線程式環境也直接接收 ODB++。IPC-2581
是公開 XML 製造資料交換格式，可包含 Paste Mask 幾何，但機台廠商公開頁面對它的直接
SPI 支援證據少於 Gerber/ODB++。DXF 常見於鋼板 CAM／雷射加工前處理，不應等同於每台
SPI 都能直接讀取。Centroid/CAD XY、mount data、BOM 與離線 model 則是輔助程式建立或
元件識別資料，不是鋼板開窗幾何的同義詞。

因此本專案採「幾何來源」與「Pad 對照」分離：開窗幾何可由 Gerber、ODB++、IPC-2581
或 DXF 取得；元件與 Pad 身分仍由明確欄位的 Pad CSV 提供。廠商專有 recipe/model 只在
取得公開契約或真實脫敏樣本後新增獨立 adapter，不猜測二進位格式。

## 2. 市場證據矩陣

| 廠商／生態 | 公開宣稱的程式輸入 | 分類 | 證據強度與限制 |
|---|---|---|---|
| Saki 3D SPI | Gerber + centroid CAD；較新型錄稱 Gerber 與 CAD/design data | 直接 SPI | 高；[自動程式新聞稿](https://www.sakicorp.com/en/news/newsrelease/823/)、[3D SPI 型錄](https://www.sakicorp.com/wp-content/uploads/2024/03/3D-SPI_SJ3906DCB1-07JA_1.0.0_mail.pdf) |
| Yamaha YSUP | Gerber、ODB++ 等設計資料，程式可在 printer/SPI/mounter/AOI 間轉用 | 整線程式環境 | 高；[iFactory/YSUP 官方頁](https://global.yamaha-motor.com/business/smt/software/ifactory/)，但「etc.」不是額外格式契約 |
| ViTrox V310i | Gerber RS-274X、RS-274D、CAD | 直接 SPI | 高；[V310i 官方功能頁](https://www.vitrox.com/vision-technology-machine-system/solder-paste-inspection-system-spi-v310i-features.php) |
| TRI TR7007D | Gerber RS-274X、RS-274D input | 直接 SPI | 高；[TR7007D 官方型錄](https://www.tri.com.tw/uploads/files/C-TR7007D-EN-1508.pdf) |
| PARMI | Gerber-based programming；支援案件要求 Gerber、BOM、offline model | 直接 SPI + 輔助資料 | 中高；[技術頁](https://parmi.com/advanced-inspection-solutions-spi-aoi-semiconductor-inspection-machines/)、[官方支援表單](https://parmi.com/inquiry/) |
| MIRTEC + Siemens Valor | Gerber、ODB++ 與常用 protocol 產生 AOI/SPI inspection program | 程式產生整合 | 中高；[MIRTEC 官方合作公告](https://www.mirtec.com/en/board/board.php?bo_table=pr&idx=251)，未列出所有 protocol |
| CKD／OMRON VP9000 | GERBER 與／或 mount data conversion、ePM program | 直接 SPI + 輔助資料 | 高；[OMRON VP9000 官方頁](https://automation.omron.com/en/ca/products/family/VP9000) |
| Koh Young | PCB Gerber import | 鄰近 AOI 證據 | 不作 SPI 支援主張；公開證據頁是 [AOI technology](https://kohyoung.com/en/automated-optical-inspection-technology/) |
| VisualCAM Stencils | Gerber、IPC-2581、ODB++、GenCAD、GerbTool、Barco DPF、PADS ASCII、CAM350、HPGL、DXF | 鋼板 CAM 生態 | 中；[VisualCAM Stencils 官方頁](https://www.flowcad.com/en/wise-stencil.htm)，不能推論所有 SPI 機台原生支援 |

跨格式的公開規格證據：

- Ucamco 將 Gerber 規格與測試資源集中於[官方下載頁](https://www.ucamco.com/en/guest/downloads/gerber-format)。
- ODB++ 規格定義 `SOLDER_PASTE` layer type，並提供[格式規格](https://odbplusplus.com/wp-content/uploads/sites/2/2021/02/odb_spec_user.pdf)及[官方範例](https://odbplusplus.com/wp-content/resource-docs/designodb_rigidflex.tgz)。
- IPC-2581 是涵蓋製造、組裝與檢驗資料的 XML 標準；見 [IPC-2581C 目錄](https://www.ipc.org/TOC/IPC-2581C-toc.pdf)、[官方測試案例](https://www.ipc2581.com/b-test-cases/)與[驗證工具](https://www.ipc2581.com/ipc-2581-file-validation-tool/)。
- Siemens 將 Gerber、ODB++、IPC-2581 列為常見製造輸出，並指出 Gerber 的接受度最廣；見[官方技術文章](https://blogs.sw.siemens.com/electronic-systems-design/2025/03/18/design-for-manufacturing-output-files/)。

## 3. SPC Platform 支援矩陣

| 格式／容器 | 狀態 | 目前契約 | 明確不支援／拒絕條件 |
|---|---|---|---|
| Gerber RS-274X/X2 (`.gtp/.gbp/.gbr/.ger`) | 支援 | mm 幾何；讀取 X2 `FileFunction`、副檔名或可辨識檔名 Side；無 Side metadata 時加 `VERIFY` 警告 | RS-274D 外部 aperture wheel 未實作；宣告 Side 衝突即拒絕 |
| Legacy photoplotter Gerber (`.pho`) | 有界支援 | 僅接受檔名或 `%LN` 可明確判定為 `SMD/Paste/Cream/Stencil/Aperture` 且 Side 可判定者；只正規化已驗證的短式 G/D、modal D、零值 I/J、空 AD 與舊 LN | `TXT/Text/Legend/Silk/Overlay`、角色不明、Side 不明／衝突、正規化後仍有 parser warning 即整份拒絕 |
| Gerber ZIP (`.zip`) | 支援 | 只選唯一符合 TOP/BOTTOM 的 Paste Gerber | 多個同 Side 候選、無法唯一判斷、archive traversal/symlink/大小超限即拒絕 |
| ODB++Design (`.tgz/.tar.gz/.tar/.zip`) | 有界支援 | 選唯一 `SOLDER_PASTE` layer；支援常用 pad/line/arc/surface 與 custom symbol，輸出 mm | 多 step paste feature、`features.Z`、resized pad、未知 symbol/record、模糊 Side 即拒絕 |
| IPC-2581 (`.xml/.ipc2581`) | 有界支援 | 安全 streaming XML；選唯一 TOP/BOTTOM `PASTEMASK`；支援 Contour、Polyline、segment/arc | DTD/entity/network 關閉；未知 Paste 幾何、多個有效 layer、缺 units/Side 即拒絕 |
| DXF (`.dxf`) | 有界支援 | 依 paste/side layer 唯一選取；支援 HATCH、閉合 polyline/path、circle、solid 與可 polygonize 的線段；轉 mm | `$INSUNITS` 缺失時必須人工選 mm/inch；多 layer 模糊、未閉合 linework、無法換算單位即拒絕 |
| Pad CSV | 支援（輔助） | 固定 `RefDes,Pad,X,Y,Width,Height,Rotation,Side`，匯入時明選 mm/inch | 缺欄、重複鍵、Side 不符不得猜 |
| Centroid/CAD XY、mount data、BOM、GenCAD、PADS ASCII | 尚未直接支援 | 列為後續 source-specific adapter 候選 | 不把欄位名稱相似的檔案自動套成全域 CSV alias |
| 廠商 recipe/offline model | 不支援 | 可識別為專有來源但不解析 | 無公開規格／授權／真實樣本時不得逆向猜測 |

「有界支援」表示只對已驗證子集承諾完整性；碰到子集外語法會整份失敗並回報原因，
不會輸出部分開窗。

## 4. 匯入與可追溯契約

1. 所有解析後幾何均轉為 mm Shapely polygon，再走既有 Pad 匹配、對位、厚度與名義值計算。
2. `validation_summary` 保存 `aperture_format`、`aperture_format_label`、
   `aperture_source_layer`、`aperture_warnings`；`parser_version` 鎖定解析器與關鍵相依版本。
3. SQLite 仍沿用 `gerber_path`／`gerber_sha256` 欄位名稱以保持舊資料與 consumer 相容；
   欄位值現在代表受管的 aperture source，不觸發 schema migration。
4. 格式解析通過不等於可啟用。啟用仍要求 Pad 完整匹配、厚度可解析、無未分類開窗，
   且操作員完成實際疊圖確認。
5. 任何 UNKNOWN/VERIFY、格式警告或未支援幾何必須出現在 UI 摘要；不得靜默丟棄。

## 5. 驗證基準與後續路線

- 本機以 Siemens 官方 ODB++ rigid-flex sample 驗證 TOP/BOTTOM Paste layer，分別讀取
  4,909／3,162 個 polygon。
- 以 IPC Consortium `testcase2.xml` 驗證 PASTETOP/PASTEBOT，分別讀取
  12,076／12,038 個 polygon；並以回歸測試鎖住 exporter 獨立量化弧端點的有界容差。
- 以 2026-06-08 現場 legacy PHO corpus 驗證同一 8-up panel：`SMDTOP.pho` 讀取
  1,260 個 polygon／334.497007 mm²，`SMDBOT.pho` 讀取 956 個 polygon／
  836.071201 mm²，兩者共同 bounds 為 `(4.95, 5.754)–(120.05, 110.854)` mm。
  `TXTTOP.pho`／`TXTBOT.pho` 經幾何目視與 layer name 交叉確認為文字／標記層，載入器
  明確拒絕，不會將筆畫誤作鋼板開窗。SMD 層仍含 panel 外框與 tooling holes；匯入後必須
  由既有疊圖例外流程將非元件幾何標記為 `NON_COMPONENT`，不得由 parser 靜默刪除。
- 下一階段優先蒐集實際機台輸出（去識別化）建立 vendor corpus，再依資料量決定
  centroid/mount-data、GenCAD/PADS ASCII 或專有 model adapter。每個 adapter 必須保留
  source/vendor provenance，不能擴大全域欄位猜測。
