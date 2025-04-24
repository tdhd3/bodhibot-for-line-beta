# 菩薩小老師 - 佛法LINE Bot

一個基於佛教智慧的LINE聊天機器人，能夠提供佛法指導、禪修方法，並以佛教觀點解讀時事。

## 主要功能

1. **佛法指導**：融合唯識學與菩薩道智慧，幫助用戶觀照習氣、認識因果、發菩提心
2. **六妙門禪修**：根據用戶修行經驗提供適合的禪修引導
3. **時事佛法省思**：從台灣主要新聞源獲取新聞，以佛教智慧角度提供分析和反思
4. **CBETA經典檢索**：精確引用佛教經典，支持用戶深入學習佛法

## 特色

- **個性化回應**：根據用戶的修行背景和提問歷史提供量身定制的指導
- **漸進式引導**：結合「三世因果 → 出離心 → 慈悲心 → 十善業 → 菩提心」修行次第
- **可視化介面**：使用LINE Flex消息提供美觀的新聞閱讀體驗
- **多元互動**：支持快速回復、禪修指導、新聞閱讀等多種互動方式

## 安裝步驟

1. 克隆儲存庫
```
git clone https://github.com/tdhd3/bodhibot-for-line-beta.git
cd bodhibot-for-line-beta
```

2. 創建虛擬環境
```
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或者
.venv\Scripts\activate  # Windows
```

3. 安裝依賴
```
pip install -r requirements.txt
```

4. 配置環境變量
```
cp .env.example .env
# 編輯.env文件添加LINE Channel Secret, Channel Access Token和OpenAI API Key
```

## 使用說明

1. 啟動服務器
```
python app.py
```

2. 使用ngrok進行隧道測試（開發環境）
```
ngrok http 8080
```

3. 將ngrok生成的URL設置為LINE Bot的Webhook URL
```
https://xxx.ngrok-free.app/webhook
```

## 使用LINE Bot的方式

1. **一般問答**：直接向機器人提問佛法相關問題
2. **請求禪修引導**：發送「請提供禪修引導」或相關命令
3. **獲取時事省思**：發送「請給我今日時事佛教省思」等命令
4. **分享修行經驗**：告訴機器人「我的修行經驗是...」，幫助它提供更適合的指導

## 技術架構

- **後端**：Flask
- **AI引擎**：OpenAI API + LangChain
- **消息平台**：LINE Messaging API
- **經典檢索**：CBETA佛教電子文獻集成
- **新聞源**：台灣主要媒體RSS + GNews API

## 授權

此專案為私人使用，未開放公共授權。

## 联系方式

如有任何問題或建議，請通過LINE與「菩薩小老師」聯繫。 