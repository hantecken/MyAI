# 向量搜尋 AI 分析功能說明

## 功能概述

本系統已成功整合 **Gemini AI** 到向量搜尋功能中，現在向量搜尋結果不僅能顯示相似性數據，還能提供智能的 AI 分析見解。

## 新增功能

### 1. AI 智能分析選項
- 每個搜尋功能都新增了「啟用 AI 智能分析」的選項
- 用戶可以選擇是否要 AI 分析搜尋結果
- 預設啟用 AI 分析功能

### 2. 產品搜尋 AI 分析
- **搜尋結果評估**：分析搜尋結果的相關性和完整性
- **產品洞察**：識別產品組合的特點和趨勢
- **商業建議**：基於搜尋結果提供具體的業務建議
- **改進方向**：建議如何優化產品搜尋和推薦

### 3. 客戶搜尋 AI 分析
- **客戶群體特徵**：分析搜尋結果中客戶的共同特點
- **市場洞察**：識別客戶需求的趨勢和模式
- **營銷建議**：基於客戶分析提供精準營銷建議
- **服務優化**：建議如何改善客戶服務和體驗

## 技術實作

### 1. 後端整合
- 在 `routes/vector_routes.py` 中新增 Gemini AI 整合
- 使用 `google-generativeai` 套件調用 Gemini Pro 模型
- 智能構建分析提示詞，針對不同搜尋類型提供專業分析

### 2. 前端介面
- 在 `templates/vector_search.html` 中新增 AI 分析選項
- 美觀的 AI 分析結果顯示區域
- 實時顯示 AI 分析狀態和結果

### 3. API 擴展
- 產品搜尋 API：`POST /api/vector/search/products`
- 客戶搜尋 API：`POST /api/vector/search/customers`
- 新增 `include_analysis` 參數控制是否啟用 AI 分析

## 使用方法

### 1. 啟用 AI 分析
```javascript
// 在搜尋請求中包含 AI 分析
const searchData = {
    query: "筆記型電腦",
    limit: 5,
    include_analysis: true  // 啟用 AI 分析
};
```

### 2. 處理 AI 分析結果
```javascript
// 檢查 AI 分析結果
if (data.ai_analysis && data.ai_analysis.success) {
    console.log("AI 分析:", data.ai_analysis.analysis);
    console.log("使用模型:", data.ai_analysis.model);
}
```

### 3. 錯誤處理
```javascript
// 處理 AI 分析失敗的情況
if (data.ai_analysis && !data.ai_analysis.success) {
    console.error("AI 分析失敗:", data.ai_analysis.error);
}
```

## 環境設定

### 1. 必要環境變數
```bash
# .env 檔案
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. 依賴套件
```bash
# 安裝必要套件
pip install google-generativeai python-dotenv
```

### 3. 檢查 requirements.txt
確保 `requirements.txt` 包含：
```
google-generativeai>=0.3.0
python-dotenv>=1.0.0
```

## 測試功能

### 1. 運行測試腳本
```bash
python test_vector_ai.py
```

### 2. 手動測試
1. 啟動向量應用：`python app_vector.py`
2. 訪問：`http://127.0.0.1:5010/vector-search-test`
3. 在產品或客戶搜尋中啟用 AI 分析
4. 執行搜尋並查看 AI 分析結果

## 功能特點

### 1. 智能提示詞
- 根據搜尋類型自動生成專業的分析提示詞
- 針對產品、客戶等不同維度提供專屬分析框架
- 確保分析結果的專業性和實用性

### 2. 錯誤處理
- 完善的錯誤處理機制
- 當 Gemini API 不可用時提供友好的錯誤訊息
- 不影響基本的向量搜尋功能

### 3. 性能優化
- AI 分析只在需要時執行
- 可選擇性啟用，不影響搜尋性能
- 分析結果快取，避免重複請求

## 未來擴展

### 1. 更多分析維度
- 銷售事件 AI 分析
- 異常檢測 AI 解釋
- 趨勢預測 AI 建議

### 2. 分析歷史記錄
- 保存 AI 分析結果
- 分析結果比較和追蹤
- 用戶反饋和改進

### 3. 自定義分析
- 用戶可自定義分析重點
- 多語言分析支援
- 分析結果匯出功能

## 注意事項

1. **API 配額**：Gemini API 有使用配額限制，請合理使用
2. **網路延遲**：AI 分析需要額外的 API 調用時間
3. **結果品質**：AI 分析結果基於 Gemini 模型，品質可能因查詢而異
4. **隱私保護**：搜尋查詢會發送到 Gemini API，請注意數據隱私

## 故障排除

### 1. AI 分析無法使用
- 檢查 `GOOGLE_API_KEY` 是否正確設定
- 確認網路連接正常
- 檢查 Gemini API 服務狀態

### 2. 分析結果為空
- 檢查搜尋查詢是否有效
- 確認搜尋結果不為空
- 查看後端日誌中的錯誤訊息

### 3. 分析品質不佳
- 嘗試更精確的搜尋關鍵字
- 調整結果數量限制
- 檢查提示詞是否適合當前查詢

---

**版本**：1.0.0  
**更新日期**：2025年1月  
**維護者**：AI 智慧技術與應用人才專題
