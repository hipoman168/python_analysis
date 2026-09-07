# 2026-09-07 GPT-6 Astra Skills / AGENTS.md Raw Share

Status: RAW_SHARE
Source: User-provided screenshots + full accompanying text in ChatGPT conversation
Date received: 2026-09-07
Routing: PATENT_COMMANDER + PAPER_COMMANDER
Handling rule: preserve source first; patent and paper commanders must analyze independently. Do not let CEO-002 pre-filtering replace their review.

## User-provided source text

OpenAI Codex DX：GPT-6 Astra 時代你的 Skills 和 AGENTS.md 可能需要大掃除，Eric Provencher 是 OpenAI 的 Codex DX 團隊成員。他在這篇文章裡指出，coding agent 的最佳實踐正在快速改變。過去需要大量手把手指導和腳手架的做法，現在已經不需要了。如果你在過去一年裡用 agent 做專案，很可能累積了一堆臃腫的指令，這些指令是你在引導模型產出好結果的過程中一點一點加上去的。每次模型更新都值得重新檢視這些假設，但到了 GPT-6 Astra，這件事變得比以往更重要。

這些指令可能出現在 Skills、AGENTS.md 和你的 task prompts 裡，它們都在塑造模型怎麼完成工作。

### Skill 檔案：少即是多

Skill 檔案本質上是存成 markdown 的 prompt，有時候會附帶腳本。它們最有用的場景是模型只在特定任務才需要的工作流程指引，或是使用 plugin 的指令。

Eric 指出很多人的預設做法是在專案裡下載一大堆 skills，但這是一個錯誤。每個 skill 都有一個名稱和描述會被載入模型的 context，讓模型知道什麼時候該用它。很多描述寫得太長，而且當你加太多 skills 的時候，Codex 會開始縮短描述來塞進去。模型最後看到的每個描述都變少了，更難判斷該選哪一個。

更糟糕的是，描述之間可能互相矛盾，或者有太多「選我選我」的語氣，導致模型載入了其實對任務沒幫助的指令。

### 寫好 Skill 的三個原則

Eric 提到 OpenAI 最近更新了 $skill-creator 的指引，來解決他們在實務中看到的多種失敗模式。

第一，skill 描述應該盡可能短，同時讓模型清楚知道什麼時候該用它。他舉了一個例子：壞的描述會讓模型在任何碰到資料庫的時候都用這個 skill，好的描述只在需要處理 migration 的時候才觸發。

第二，好 skill 的關鍵標記是漸進式揭露（progressive disclosure）。讀一個 skill 會佔用 context，讓你更接近 compaction，而且引入可能不適用當前任務的指引。對有多個工作流程的 skill，把根文件做成一個最小的 router，指向支援文件和腳本。給模型足夠的指引知道去哪裡找，但不強迫它讀不相關的東西。

第三，很多 skill 被寫成精心安排的行程表或食譜。模型在理解細微差異和模糊性方面已經好很多了，所以過度具體的指引現在反而會妨礙結果，而不是像以前那樣幫助結果。

Eric 也提到 repository skills 同時也在指引其他貢獻者的 agent，這些 agent 可能用不同的模型。對 Sol 或 Luna 有幫助的指引可能會過度限制 GPT-6 Astra，所以要考慮哪些模型會使用你留下的指令。

### AGENTS.md：重新檢視每一條指令

因為 AGENTS.md 在模型每次在你的 repo 裡工作時都會套用，Eric 建議重新檢視每一條指令，問自己這個任務是不是還需要它。

他舉了幾個具體的例子。要求在每次編輯之前讀一堆文件或完整的 repo map，對一個修錯字的任務來說太過了。GPT-6 Astra 可以自己判斷需要讀什麼，不需要被強迫在每次改動之前先 review 整個專案。

提示模型在每次編輯之前讀檔案，是一個快速燃燒 context 和拖慢工作的好方法。指向一些文件仍然有幫助，但前提是要有 context 相關性。也要確保你的文件是更新的。

過去的模型需要鼓勵才會跑測試和檢查自己的工作。GPT-6 Astra 會自己做這些事，所以同樣的指令可能導致不必要的測試。

### 決策邊界：GPT-6 Astra 的判斷力更好

Eric 特別提醒要注意你怎麼描述邊界。如果之前的模型未經你同意就做了事情，你可能加了很強硬的語言讓它先問。這很有用，但 GPT-6 Astra 有好得多的判斷力，你應該以此對待它。它也會認真看待你的邊界，可能在你其實樂意讓它繼續的地方就停下來。

### 持續性：定義什麼是完成

如果你習慣 GPT-5.6 Sol 接到一個請求後就持續跑很長一段，GPT-6 Astra 在什麼時候該停下來這件事上可能感覺更猶豫。它可能做到第一版 implementation 就回來找你 review，但其實還有工作要做。

Eric 建議在開始之前就定義什麼是完成。如果任務包含讓 implementation 跑起來、檢查結果、修正失敗的部分，就把這些都寫進請求裡。如果你要求它在第一版 implementation 後停下來 review，會把模型拉向更早的停止點，所以要檢查這是不是你真的需要做的決定。

如果你想讓它在第一版之後繼續探索，就說清楚你想要它探索什麼以及應該在哪裡停下來。

### 結語：讓 GPT-6 Astra 幫你做大掃除

Eric 在文章最後建議，新模型是清理門戶的好機會。讓 GPT-6 Astra 根據這篇文章討論的內容做一次 audit，然後去建造一些你以前不敢嘗試的東西。

## Attached screenshots referenced by user

Nine screenshots were attached in the same chat turn, showing the 1/8–8/8 visual summary cards plus the Eric Provencher/X article screenshot. The source images remain in the chat attachment record; this markdown preserves the accompanying source text and routing metadata.
