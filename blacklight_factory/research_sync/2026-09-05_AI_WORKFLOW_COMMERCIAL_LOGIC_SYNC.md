# AI 工作流商業邏輯參考｜專利／論文雙向同步

日期：2026-09-05
來源：何董事長提供之工作流平台截圖與說明
同步對象：AI Agent 發明專利專案指揮官、AI Agent 國際期刊論文專案指揮官
狀態：RESEARCH_INPUT / 待查證，不直接視為專利新穎性證據或論文正式文獻

## 董事長提供的核心觀察

好的 AI 工具必須配合企業既有商業邏輯，而不是讓企業流程遷就工具。透過可視化節點，把市場分析、人物誌、產品定位、AIDA 文案、短影音腳本、圖片提示詞、音樂提示詞、產品開發五層次等能力組合成可執行工作流；使用者輸入基礎資料後，由節點依依賴關係逐步產生策略與內容。

截圖顯示的代表性工作流包括：
- 影片／圖片／與音樂生成鏈：文字／主題 → AI 短影片提示詞 → AI 繪圖提示詞；並有音樂提示詞生成與文字輸入輸出節點。
- 產品銷售影片腳本鏈：產品／目標市場／市場背景 → 市場分析 → 人物誌／產品定位 → AIDA 文案／短影音腳本 → 圖片提示詞／影片腳本。
- 新品開發鏈：輸入 → 五星評論／客戶痛點分析 → 人物誌 → 產品開發五層次 → 產品／服務撰寫。

## 給專利指揮官

這份資料應作為 Prior Art / Architecture Signal，而非直接宣稱為本公司發明。可視化節點、工作流串接、AI 文案與行銷自動化本身已有大量既有技術，不能作為黑燈工廠主要新穎性來源。

應比較並凸顯黑燈工廠更高一層的治理／執行架構：Agent Request ≠ 執行權；Identity → Role → Permission → Resource Scope → Risk → Approval Gate → Tool Execution → Evidence → Audit；以及 Demand × Model × Capability × Risk 驅動的 Agent/Workflow 拓樸、跨模型勞動力調度、Credential Broker、Data Egress Gate、WorkOrder 與可驗證 Evidence 閉環。

專利檢索新增方向：visual AI workflow builder、node-based AI orchestration、business-logic workflow automation、AI marketing workflow、multi-agent workflow orchestration。檢索後判斷哪些屬已知 workflow 編排，哪些可反向強化本案『治理層與執行層分離』的差異。

## 給論文指揮官

可作為研究問題與實驗設計參考：比較『單一 Agent 自由執行』與『商業邏輯被顯式化為 Workflow/State Machine』時的任務成功率、重試率、Token/API 成本、人工介入次數、錯誤傳播、Evidence 完整率與可恢復性。

可形成論文中的重要理論區分：LLM/Agent 提供認知與生成能力；Workflow 將企業程序、依賴、狀態與控制點顯式化；治理層再控制權限、風險與 Evidence。這與黑燈工廠『少量主管 Agent + 大量 Workflow + State Machine + Tools』架構一致，但正式論文引用仍需另外搜尋可引用之官方文件與學術文獻，不能引用本截圖作為技術事實證據。

## 同步規則

此項資料同時進入專利與論文研究池。專利專案優先做先前技術比對與揭露控制；論文專案只吸收可公開且不影響專利申請的新內容。任何可能構成新發明點的細節，在專利申請前不得因論文或公開材料先行揭露。
