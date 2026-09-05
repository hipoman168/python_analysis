# 大用科技第一次一家人工作會議紀錄

- 日期：2026-09-05
- Meeting ID：7858c0b2-0446-4020-9375-d2294b034146
- Minutes ID：cc1e5245-7fcb-422b-a439-0f56635d7777
- 會議標準：DAYONG_TWO_PHASE_WORK_MEETING_V1
- 主席：何董事長（CHAIRMAN-001）
- 工作報告：陳啟航（CEO-002）、小晴（D1-003）、阿凱（D2-004）

## 會議定位
今天是第一次正式工作會議。本次紀錄作為下一次會議舊案追蹤與討論基準。

## 董事長指示
1. 各主管只針對實際工作與工單報告。
2. 明確提出工單問題、無法執行事項、失敗原因與需要支援的地方。
3. 各主管建議事項一併列入會議紀錄。

## 002 陳啟航工作報告
- Family Room：真實工單與主管報告已進入 Meeting Packet，但 Family Room runtime 尚未正式讀取 packet。
- Open Notebook：已啟動完整學習，尚需完成 API、MCP、架構、安全、部署與 Known Issues 複核。
- NGINX 1.31.5：PoC 規格已建立；隔離 sandbox 因 DNS 無法下載 source，屬環境阻塞，不是 NGINX build failure。
- 需要支援：取得可出網隔離 Linux runner；不碰 production gateway。

## D1 小晴工作報告
- 1號機硬體/環境驗證已完成：RTX 2070 8GB。
- NVIDIA PAIR：節點控制、配對、UUID、mTLS、排程與故障遲滯已完成技術學習，PoC 尚待執行。
- 主管工作報告生成器：首批真實報告已建立，但自動從 ledger/event/rollup 生成尚未完成。
- 阻塞：已核准俏皮女聲 exact Voice ID/runtime artifact 尚未定位。
- 需要支援：回查既有 TTS artifact、工作流與日誌，不要求董事長重做聲音設定。

## D2 阿凱工作報告
- 2號機硬體/環境驗證已完成：GTX 1660 SUPER 6GB，runtime probe PASS。
- Gemini 3.5 Transcribe：已建立 STT 驗證工單，尚待單人、雙人、三人、中英混語與 Live 測試。
- 會議秘書：第一份正式 MD 已建立；下一階段為自動生成、follow-up 與下次回讀閉環。
- 聲音：目前阿凱男聲真人驗收 FAIL，仍有機器人感且與 002 區辨不足。
- 需要支援：改用受控 TTS，完成 002 與阿凱可閉眼辨識的不同男聲。

## 本次主要問題與支援需求
1. Family Room runtime 尚未接入 Meeting Packet。
2. NGINX PoC 缺可出網隔離 Linux 執行環境。
3. PAIR Node Control 尚未做真機 PoC。
4. 小晴 exact Voice ID 尚未定位。
5. Gemini STT 尚未完成實測。
6. 002 與阿凱固定自然男聲尚未通過真人驗收。
7. 會議秘書的自動 MD/follow-up/下次回讀尚未形成完整自動閉環。

## 建議事項
- 會議一律以真實 WorkOrder/主管報告為輸入，不使用假腳本。
- 第一次會議建立基準；第二次起固定先報新工作，再逐項追蹤上一份會議紀錄未完成事項。
- 聲音、STT、會議紀錄均須有 runtime Evidence 才能標示完成。

## 下次會議必追蹤
- Family Room Meeting Packet 接線結果。
- Gemini STT 測試結果。
- 002/阿凱固定男聲與小晴聲線恢復結果。
- 會議 MD 與 follow-up 自動化結果。
- PAIR/NGINX/Open Notebook 研究或 PoC 進度。
