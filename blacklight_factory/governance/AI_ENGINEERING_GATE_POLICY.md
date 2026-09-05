# 黑燈工廠 AI Engineering Gate Policy

Status: MANDATORY
Effective: 2026-09-05
Authority: CHAIRMAN-001
Scope: CEO-002、D1、D2、所有主管 Agent、執行 Agent、Workflow、Runner、開發任務、部署任務、資料庫修改、API 串接、TTS/STT、影片產線、研究實驗與其他正式技術工作。

## 核心原則

不靠 AI 記得規則，而是把規則做成開發流程；有證據才能往下走，出問題也能回到最後正常版本。

Prompt 決定意圖，Gate 決定能不能執行；Evidence 決定能不能宣告完成。

Agent Request ≠ 執行權。

## 強制 Gate 流程

1. Start / Bootstrap Gate
   - 確認專案、環境、Harness、依賴、版本有效。
   - 不符合條件不得開始修改。

2. Git / LKG / Clean-Dirty / Pre-change Gate
   - 確認 Git 狀態可追溯。
   - 確認最後已知正常版本（LKG）可回復。
   - 區分本次未提交變更與既有工作。
   - 修改前建立基準快照或等價 Evidence。

3. Requirement / Goal / No-Touch / Coding Gate
   - 固定需求、成功條件、不可修改範圍、測試與失敗回復方式。
   - 未知風險或邊界不清不得正式進入開發。

4. Ownership / Permission / Write Gate
   - 每個修改必須在被授權範圍內。
   - 必須知道修改原因、影響範圍、回復方式。
   - 禁止越權修改、順手重構、未授權資料變更。

5. Test / Integration / Real-entry / Requirement Trace Gate
   - 單元測試、整合測試、實際使用入口驗證。
   - 逐項將需求對應到修改、測試與驗收 Evidence。
   - 只有模擬通過、沒有 Runtime Evidence，不算完成。

6. Reviewer / High-risk Gate
   - 高風險變更需獨立 reviewer context 或 Human Approval。
   - 涉及權限、憑證、正式資料、不可逆操作、對外發布時必須升級 Gate。

7. Fingerprint / Close Gate
   - 確認審查後程式未被再次修改。
   - Evidence、Audit、測試結果、版本狀態完整後，才可宣告完成。

8. Commit / Acceptance / New LKG Gate
   - 只有 Close PASS 才能提交正式版本。
   - 再次驗證實際入口。
   - 通過後標記為新的 LKG，作為下一輪安全起點。

## 完成宣告規則

以下任一情況存在時，不得使用「完成、已上線、已修好、驗收通過」等表述：
- 無 Runtime Evidence
- 無真實入口驗證
- 關鍵測試未完成
- 仍有未揭露 blocker
- 版本不可回復
- 無法證明修改範圍
- 高風險 Gate 尚未通過

正確狀態必須如實標示：OPEN / IN_PROGRESS / BLOCKED / PENDING_ACCEPTANCE / PASS / COMPLETED。

## 所有人必須遵守

本規則不是建議，而是黑燈工廠正式工程治理規範。任何主管 Agent、執行 Agent、Workflow 或外部模型接入後，都不得繞過 Gate；若任務本身沒有建立對應 Gate，先建立最小必要 Gate，再執行工作。

## 一句話標準

不靠 AI 記得規則，而是把規則做成流程；Prompt 是意圖，不是權限；有 Evidence 才能往下走，有 Runtime Evidence 才能宣告完成。
