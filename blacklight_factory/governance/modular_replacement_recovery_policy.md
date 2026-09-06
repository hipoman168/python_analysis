# Modular Replacement Recovery Policy

Status: MANDATORY
Effective: 2026-09-06
Authority: CHAIRMAN-001
Owner: CEO-002 / 黑燈工廠

## 目的

黑燈工廠所有節點、Runner、Gateway、Worker、Service、Handler、Credential Mount、Runtime Adapter 與部署模組，一旦發生長時間不穩定、反覆修補、狀態漂移、相依污染或無法形成可重複 Runtime Evidence 時，禁止持續採取無限期的局部補丁式除錯。

核心原則：

> 哪個模組壞了，就替換哪個模組；若模組邊界已污染，就把該邊界整體重建。不要在未知舊狀態上無限堆補丁。

## 適用範圍

適用於：
- 雲端節點與地端節點
- Linux / Windows Runner
- DB_PULL / Command Seat / Worker Transport
- systemd / Windows Service
- Voice / STT / TTS / Video / Publisher handlers
- Credential mount / runtime env / identity binding
- API Gateway / MCP / Federation adapters
- Heartbeat / Evidence / Audit / Auto Update 元件

## Recovery Decision Gate

出現以下任一條件，進入 Replacement Review，而不是繼續局部追 bug：
1. 同一故障經過 2 次以上修補仍再次出現。
2. 修補需要同時修改 2 個以上非預期模組。
3. 無法明確證明目前實際載入的版本、env、service unit 或 executable。
4. 節點身分、設定、憑證或路徑存在 drift。
5. 舊設定、drop-in、service、script 彼此覆蓋，無法形成單一來源。
6. 問題已造成使用者反覆人工 SSH、貼指令、截圖或陪同除錯。
7. 已有成熟可替換模組或可重新 bootstrap 的乾淨版本。

## Recovery 順序

固定採以下順序：

`Identify Module Boundary → Preserve Required Secrets/Data → Snapshot LKG → Disable Old Module → Deploy Clean Replacement → Bind Identity/Credentials → Runtime Test → Evidence → Promote New LKG → Remove Obsolete Residue`

不得把「舊模組繼續跑 + 新模組疊上去」當作正式完成狀態。

## 憑證原則

- 必要 API Key / Secret 可以保留，但不得在聊天、log、Evidence 中輸出原值。
- 憑證與程式模組分離。
- Credential Mount 出問題時，直接重建 Credential Mount，不修改業務 handler 來繞過。
- 任何新模組只能取得最小必要憑證。

## 模組邊界

正式節點至少拆分為：
- Bootstrap
- Node Identity
- Transport / Runner
- Policy Gate
- Credential Mount
- Service Runtime
- Business Handler
- Health / Heartbeat
- Evidence / Audit
- Auto Update / Rollback

每個模組必須可單獨升級、停用、替換與回滾。

## Last Known Good

所有正式模組必須保存：
- version
- commit / artifact SHA256
- deployment timestamp
- runtime evidence
- rollback target

更新失敗時優先回滾到 LKG，不在失敗版本上連續疊補丁。

## 人工操作限制

如果可透過既有 Runner、Cloud Assistant、Command Seat、API、GitHub Actions、Workflow 或安全 bootstrap 完成，禁止要求使用者反覆手動操作。

需要人工時，應壓縮為一次性 bootstrap / login / credential authorization，而不是把使用者當 terminal operator。

## 完成條件

替換完成必須同時具備：
- 新模組實際運行
- 舊模組已停用或隔離
- 真實入口 Runtime Evidence PASS
- Evidence / Audit 可追溯
- 新 LKG 已建立
- 無必要的 legacy residue 已清除

沒有 Runtime Evidence，不得宣告修復完成。

## 與既有政策關係

本政策與以下規則共同強制執行：
- AI Engineering Gate Policy
- Reuse-First Development Policy

Reuse-First 決定「先找成熟替代件」；本政策決定「故障時優先換模組而非無限補丁」；AI Engineering Gate 決定「沒有 Evidence 不得宣告完成」。
