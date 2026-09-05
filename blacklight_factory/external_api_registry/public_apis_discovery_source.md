# Public APIs — 黑燈工廠 External API Discovery Source

- Status: APPROVED_DISCOVERY_SOURCE
- Added: 2026-09-05
- Owner: CEO-002 / 黑燈工廠外交部
- Source: https://github.com/public-apis/public-apis
- Role: External API Discovery Source（API 發現／候選目錄）

## 定位
Public APIs 作為黑燈工廠尋找外部資料與功能 API 的候選來源，不代表其中 API 已獲准直接進入正式產線。

## 標準流程
需求 → 官方 API → 既有 API Registry → Public APIs 候選搜尋 → Gate 審查 → Sandbox/PoC → 正式 Registry → Workflow/Agent 使用。

## Gate 必查
1. 官方來源與維護狀態
2. HTTPS
3. Auth / API Key / OAuth
4. Rate limit / 免費額度 / 成本
5. 商用與授權條款
6. CORS（若為前端）
7. 資料新鮮度與品質
8. 穩定性與失效 fallback
9. 隱私、安全、credential 管理
10. 實際 runtime PoC Evidence

## 優先應用
- 日本旅遊情報／天氣／交通／地理資料
- 旅行小蜜
- 新聞與政府公開資料
- 匯率、字典、書籍等工具型服務
- 客戶快速 PoC 與小工具

## 治理原則
Public APIs 只負責「發現候選」，不授予執行權。任何 API 接入仍需經黑燈工廠 Policy Gatekeeper / Credential Broker / Evidence / Audit 流程。
