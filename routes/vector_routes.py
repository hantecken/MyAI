# routes/vector_routes.py
# 向量搜尋相關路由

from flask import Blueprint, request, jsonify, render_template
# import logging  # 註解掉 logging 模組
import os
import google.generativeai as genai
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def register_vector_routes(app, hybrid_data_manager):
    """
    註冊向量搜尋相關路由
    
    Args:
        app: Flask 應用實例
        hybrid_data_manager: 混合資料管理器實例
    """
    
    # logger = logging.getLogger(__name__)  # 註解掉 logger
    
    # 初始化 Gemini
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            GEMINI_AVAILABLE = True
        else:
            GEMINI_AVAILABLE = False
            # logger.warning("未設定 GOOGLE_API_KEY，Gemini 功能將被停用")  # 註解掉 logging
            pass
    except Exception as e:
        GEMINI_AVAILABLE = False
        # logger.error(f"Gemini 初始化失敗: {e}")  # 註解掉 logging
        pass
    
    def analyze_with_gemini(query_text, search_results, analysis_type):
        """使用 Gemini 分析搜尋結果"""
        if not GEMINI_AVAILABLE:
            return {
                'success': False,
                'error': 'Gemini API 不可用'
            }
        
        try:
            # 構建分析提示詞
            if analysis_type == 'products':
                prompt = f"""
你是一位資深的產品分析專家，請分析以下產品搜尋結果並提供專業見解：

搜尋查詢：{query_text}
搜尋結果數量：{len(search_results)} 個產品

產品資料：
{chr(10).join([f"- {item.get('product_name', 'N/A')} (類別: {item.get('category', 'N/A')}, 品牌: {item.get('brand', 'N/A')}, 相似度: {item.get('score', 0):.2%})" for item in search_results])}

請提供以下分析：
1. **搜尋結果評估**：分析搜尋結果的相關性和完整性
2. **產品洞察**：識別產品組合的特點和趨勢
3. **商業建議**：基於搜尋結果提供具體的業務建議
4. **改進方向**：建議如何優化產品搜尋和推薦

請用繁體中文回答，控制在300字以內。
"""
            elif analysis_type == 'customers':
                prompt = f"""
你是一位資深的客戶分析專家，請分析以下客戶搜尋結果並提供專業見解：

搜尋查詢：{query_text}
搜尋結果數量：{len(search_results)} 個客戶

客戶資料：
{chr(10).join([f"- {item.get('customer_name', 'N/A')} (性別: {item.get('gender', 'N/A')}, 年齡: {item.get('age', 'N/A')}, 相似度: {item.get('score', 0):.2%})" for item in search_results])}

請提供以下分析：
1. **客戶群體特徵**：分析搜尋結果中客戶的共同特點
2. **市場洞察**：識別客戶需求的趨勢和模式
3. **營銷建議**：基於客戶分析提供精準營銷建議
4. **服務優化**：建議如何改善客戶服務和體驗

請用繁體中文回答，控制在300字以內。
"""
            else:
                prompt = f"""
你是一位資深的數據分析專家，請分析以下搜尋結果並提供專業見解：

搜尋查詢：{query_text}
搜尋結果數量：{len(search_results)} 筆資料

請提供以下分析：
1. **結果評估**：分析搜尋結果的質量和相關性
2. **數據洞察**：識別數據中的關鍵模式和趨勢
3. **業務建議**：基於分析結果提供實用的業務建議
4. **改進方向**：建議如何優化搜尋和分析流程

請用繁體中文回答，控制在300字以內。
"""
            
            # 調用 Gemini API
            response = model.generate_content(prompt)
            
            return {
                'success': True,
                'analysis': response.text,
                'model': 'gemini-pro'
            }
            
        except Exception as e:
            # logger.error(f"Gemini 分析失敗: {e}")  # 註解掉 logging
            return {
                'success': False,
                'error': f'AI 分析失敗: {str(e)}'
            }
    
    @app.route('/vector-search-test')
    def vector_search_test():
        """向量搜尋測試頁面"""
        return render_template('vector_search.html')
    
    @app.route('/api/vector/search/products', methods=['POST'])
    def search_products():
        """搜尋相似產品 API"""
        try:
            data = request.get_json()
            
            if not data or 'query' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少查詢參數'
                }), 400
            
            query_text = data['query']
            limit = data.get('limit', 10)
            include_analysis = data.get('include_analysis', False)
            
            # 執行產品相似性搜尋
            result = hybrid_data_manager.search_similar_products(query_text, limit)
            
            # 如果要求 AI 分析且搜尋成功
            if include_analysis and result.get('success') and result.get('results'):
                ai_analysis = analyze_with_gemini(query_text, result['results'], 'products')
                result['ai_analysis'] = ai_analysis
            
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"產品搜尋 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vector/search/customers', methods=['POST'])
    def search_customers():
        """搜尋相似客戶 API"""
        try:
            data = request.get_json()
            
            if not data or 'query' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少查詢參數'
                }), 400
            
            query_text = data['query']
            limit = data.get('limit', 10)
            include_analysis = data.get('include_analysis', False)
            
            # 執行客戶相似性搜尋
            result = hybrid_data_manager.search_similar_customers(query_text, limit)
            
            # 如果要求 AI 分析且搜尋成功
            if include_analysis and result.get('success') and result.get('results'):
                ai_analysis = analyze_with_gemini(query_text, result['results'], 'customers')
                result['ai_analysis'] = ai_analysis
            
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"客戶搜尋 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vector/search/sales', methods=['POST'])
    def search_sales():
        """搜尋相似銷售事件 API"""
        try:
            data = request.get_json()
            
            if not data or 'quantity' not in data or 'amount' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少查詢參數 (quantity, amount)'
                }), 400
            
            quantity = float(data['quantity'])
            amount = float(data['amount'])
            limit = data.get('limit', 10)
            
            # 執行銷售事件相似性搜尋
            result = hybrid_data_manager.search_similar_sales(quantity, amount, limit)
            
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"銷售事件搜尋 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vector/recommend/products', methods=['POST'])
    def recommend_products():
        """產品推薦 API"""
        try:
            data = request.get_json()
            
            if not data or 'customer_id' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少客戶ID參數'
                }), 400
            
            customer_id = int(data['customer_id'])
            limit = data.get('limit', 5)
            
            # 執行產品推薦
            result = hybrid_data_manager.recommend_products_for_customer(customer_id, limit)
            
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"產品推薦 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vector/detect/anomalies', methods=['POST'])
    def detect_anomalies():
        """異常檢測 API"""
        try:
            data = request.get_json() or {}
            
            threshold_score = data.get('threshold', 0.3)
            limit = data.get('limit', 20)
            
            # 執行異常檢測
            result = hybrid_data_manager.detect_sales_anomalies(threshold_score, limit)
            
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"異常檢測 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vector/status', methods=['GET'])
    def vector_database_status():
        """向量資料庫狀態 API"""
        try:
            result = hybrid_data_manager.get_vector_database_status()
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"向量資料庫狀態 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vector/refresh', methods=['POST'])
    def refresh_vector_database():
        """重新整理向量資料庫 API"""
        try:
            result = hybrid_data_manager.refresh_vector_database()
            return jsonify(result)
            
        except Exception as e:
            # logger.error(f"向量資料庫重新整理 API 錯誤: {e}")  # 註解掉 logging
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # logger.info("向量搜尋路由註冊完成")  # 註解掉 logging

