# 黑燈工廠 Reuse-First Development Policy

- Status: MANDATORY
- Effective: 2026-09-05
- Owner: CEO-002

## 核心原則
新專案、新 Agent、新 Workflow、新 Skill、新 API 串接、新工具功能開發，預設不得從零開始。

第一選擇：優先尋找可重用的既有方案，取得後依黑燈工廠需求改造。
只有在確認無合適方案、授權不允許、風險不可接受、品質不足或整合成本反而更高時，才允許進入從零開發。

## 強制 Reuse Discovery Gate
任何新開發進入 Coding Gate 前，必須完成以下搜尋：
1. 黑燈工廠內部 Registry / GitHub / 歷史專案 / Skill / Workflow / Agent / API 資產。
2. 已登錄外部資源庫（例如 Public APIs、500+ AI Agents Projects）。
3. GitHub 公開專案與官方範例。
4. 官方 SDK / API / Reference Implementation。
5. 必要時搜尋成熟開源框架與社群實作。

## 候選評估
每個候選至少檢查：
- 功能匹配度
- License / 商用權限
- 維護活躍度
- 安全風險與 secrets 處理
- 依賴與基礎設施需求
- 可修改性 / 可抽換性
- 測試與文件完整度
- 與 DAYONG 架構整合成本
- 本地模型 / API / GPU / CPU 相容性
- 是否有可驗證 Runtime Evidence

## 決策順序
Reuse As-Is → Fork/Adapt → Wrap/Integrate → Compose Existing Components → Build From Scratch

## Gate 規則
沒有 Reuse Discovery Evidence，不得進入正式 Coding Gate。
如果最後決定從零開發，必須留下原因與比較證據。

## 資料庫 / 技術圖書館政策
任何被發現且具有潛在價值的 API、Agent、Skill、Workflow、框架、工具、Reference Implementation、教學案例，都應收錄到黑燈工廠技術資料庫／GitHub Registry，至少保存：
- 名稱與來源 URL
- 類型與分類
- 功能摘要
- 授權
- 技術棧
- 適用產線
- 風險註記
- 驗證狀態
- 是否已 PoC
- 最後複查日期

## 一句話規範
先找現成、再改造成自己的；能重用就不重造，沒有搜尋證據不得從零開發。
