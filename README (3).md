# NLMA都市計畫/國家公園使用分區圖連線 / NLMA Land-use Map Connections

A QGIS plugin for adding Taiwan NLMA urban planning and national park land-use zoning maps as XYZ layers, checking connections, and refreshing service tokens when needed.

**Version:** 1.2.2 · **QGIS metadata compatibility:** 3.24–4.2.x · **License:** GPL-2.0-or-later · **Status:** Non-experimental

## 功能 / Features

- 加入「都市計畫使用分區」及「國家公園使用分區」XYZ 圖層。
- 辨識專案中支援的既有圖層，更新其連線資訊。
- 每 5 分鐘檢查連線，每 30 分鐘或偵測授權失效時嘗試更新 token。
- 從外掛選單手動執行「立即更新支援圖層連線」。
- 更新前驗證服務設定及代表性圖磚；服務驗證失敗時保留既有連線。
- 更新時保留圖層名稱及樣式；切換專案時取消舊請求。

Urban planning and national park zoning layers, periodic connection checks, automatic token refresh, manual updates, and service/tile validation before applying new connections.

## 安裝 / Installation

1. Download the plugin ZIP from this project's Releases (when published).
2. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the ZIP, install, and enable **NLMA都市計畫/國家公園使用分區圖連線**.

QGIS：外掛 → 管理與安裝外掛 → 從 ZIP 安裝。正式通過審核並上架官方外掛庫後亦可搜尋安裝。

The ZIP must contain a single `nlma_token_refresh/` directory with `metadata.txt` and `__init__.py`. No third-party Python packages need to be installed separately.

## 操作 / Usage

1. 在外掛選單中開啟 **NLMA都市計畫/國家公園使用分區圖連線**。
2. 選擇 **加入都市計畫使用分區** 或 **加入國家公園使用分區**。
3. 等待服務驗證及圖層加入，將地圖移至相應都市計畫區或國家公園範圍，並調整縮放級別查看。
4. 外掛會定期檢查支援圖層；需要立即檢查時，選擇 **立即更新支援圖層連線**。

Use the plugin menu to add either zoning layer, navigate to the relevant area, and let the plugin check connections periodically. Use the manual update action when needed.

- [版本更新 / Changelog](CHANGELOG.md)
- [原始碼 / Source code](https://github.com/LiXing183/NLMA-land-use-map-connections)

## 資料來源與限制 / Data and limitations

Data source: **內政部國土管理署 / National Land Management Agency, Taiwan**.

- 適用臺灣都市計畫區與國家公園使用分區；實際涵蓋範圍與圖資更新以官方服務為準。
- 需要 Internet access，連線至 [官方圖台](https://nsp.nlma.gov.tw/ngis/) 及 `giss.nlma.gov.tw` 圖磚服務。服務可用性、token 有效期、圖磚內容及存取限制由原服務提供者決定。
- 此為獨立開發工具，非國土管理署官方產品。程式授權不授予額外圖資或服務使用權。
- 外掛不會繞過網站驗證或存取限制。連線失敗時請查看 QGIS 訊息及官方圖台；尚未成功加入的圖層需在連線恢復後手動重試。
- XYZ 圖磚為影像資料；本外掛不提供向量分區下載、地籍查詢或法定界線判定。
- 連線 token 可能隨圖層來源儲存在 QGIS 專案中；分享專案前請注意連線資訊可能外流或過期。外掛日誌不會主動輸出 token。
- QGIS 3.40.6（Linux 無顯示器模式）通過 7 項自動測試，使用本地測試圖磚；不代表官方圖台連線已由該環境驗證。使用者已在 QGIS 4.2.3 回報可用。其他版本及作業系統未逐一驗證；metadata 版本範圍不代表每個版本皆已測試。

## 問題回報 / Issues

Please use [GitHub Issues](https://github.com/LiXing183/NLMA-land-use-map-connections/issues). Include plugin/QGIS versions, operating system, steps to reproduce, the affected layer, and the relevant error message. Remove tokens and personal information from screenshots, project files, or diagnostic files before submitting.

## 授權 / License

This plugin is licensed under the **GNU General Public License v2.0 or later (GPL-2.0-or-later)**. See [LICENSE](LICENSE). Third-party data and service terms remain with their respective providers.

Author: Xing Li.  
Maintainer email: li.xing.183.github@icloud.com
