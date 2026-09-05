# 大用科技核心主管會議標準 v1.0

> 董事長核准：會議必須以真實工單與上一場會議追蹤為核心，不以 Agent 數量或空泛討論取代工作報告。

## 會前準備

每位主管（CEO-002、D1-003 小晴、D2-004 阿凱）必須先依自己手上的工單索引產生一份工作報告。報告重點不是工單數量，而是：

- 本期實際完成了哪些事情
- 目前有什麼重要進度
- 收集到哪些有價值的資料
- 哪些事情遇到問題或失敗，以及原因
- 哪些事項需要上級決策
- 下一步要做什麼
- 對應 WorkOrder / Evidence 在哪裡

## 會議流程

### 第一階段：本期新工作報告

主持人開場後依序請：

1. CEO-002 陳啟航
2. D1-003 小晴
3. D2-004 阿凱

各自報告新的工單進度、成果、問題、失敗原因、待決策事項與下一步。不得只報「派出多少 Agent、成功多少、失敗多少」。

### 第二階段：上一場會議追蹤

自動載入上一份正式 Markdown 會議紀錄，逐項檢查仍未完成、Blocked、待決策、待驗證與需要持續追蹤的事項。

每一項追蹤至少回答：

- 上次決議是什麼
- 負責人是誰
- 目前做到哪裡
- 是否已有 Evidence
- 沒完成的原因
- 本次是否需要新決策
- 下一步與新的期限/工單

## 會議秘書輸出

會議結束後由會議秘書產生新的 Markdown 紀錄，至少包含：

```md
# 大用科技核心主管會議

## 一、本期新工作報告
### CEO-002 陳啟航
### D1-003 小晴
### D2-004 阿凱

## 二、上一場會議追蹤

## 三、本次主要問題

## 四、決策事項

## 五、未決事項

## 六、後續工單

## 七、下次必須追蹤事項
```

新會議紀錄必須連到上一份紀錄，形成連續會議鏈。下次會議不得重新從零開始。

## 資料層

- `ai_agent_workorder_ledger`：正式工單主檔
- `ai_agent_workorder_events`：工單狀態與 Evidence 事件
- `ai_agent_workorder_rollups`：事情層級彙總
- `ai_agent_management_reports`：主管會前工作報告
- `ai_family_meeting_minutes`：正式會議 Markdown 紀錄
- `ai_family_meeting_followups`：跨會議追蹤項目
- `ai_family_meeting_agenda_index`：兩階段會議索引
- `dayong_build_family_meeting_packet()`：會前一次取得新工作報告 + 舊案追蹤的 meeting packet

## 開源設計參考

本機制參考 `nikhilm55/beyondmeetings`（MIT License）所採用的 structured meeting notes、decision/action item 與 follow-up meeting chaining 思路；大用科技版本進一步以 WorkOrder、Evidence、主管工作報告與兩階段會議制度整合。