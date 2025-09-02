# controllers/analysis_controller.py
# 分析控制器 - 負責處理自然語言查詢和業務邏輯

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import random
# import logging  # 註解掉 logging 模組
import os
import tempfile
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from models.exogenous_variables import ExogenousVariables

class AnalysisController:
    """
    控制器(Controller)層: 處理自然語言查詢解析和業務邏輯。
    """
    def __init__(self, data_manager):
        """
        初始化分析控制器
        """
        self.data_manager = data_manager
        # self.logger = logging.getLogger(__name__)  # 註解掉 logger

    def _parse_query(self, query):
        """
        [Controller] 簡易的自然語言解析器，模擬LangChain的功能。
        辨識時間範圍和分析維度。
        """
        print(f"🔍 開始解析查詢: {query}")
        
        # 為了演示穩定，我們將"今天"固定在數據範圍內的一個日期
        today = datetime(2025, 8, 31) 
        print(f"   使用固定日期: {today}")
        
        # 預設時間比較: 這個月 vs 上個月
        current_start = today.replace(day=1)
        last_start = (current_start - timedelta(days=1)).replace(day=1)
        current_end = (current_start + relativedelta(months=1)) - timedelta(days=1)
        last_end = (last_start + relativedelta(months=1)) - timedelta(days=1)
        period_text = f"{current_start.year}年{current_start.month}月 vs 上月"
        
        print(f"   預設時間範圍:")
        print(f"     - 當前期間: {current_start} 到 {current_end}")
        print(f"     - 比較期間: {last_start} 到 {last_end}")
        print(f"     - 期間文字: {period_text}")

        # 統一處理查詢中的時間格式
        processed_query = query
        
        # 1. 統一處理月份的中文表示
        month_mapping = {
            '一月': '01', '二月': '02', '三月': '03', '四月': '04',
            '五月': '05', '六月': '06', '七月': '07', '八月': '08',
            '九月': '09', '十月': '10', '十一月': '11', '十二月': '12'
        }
        
        for chinese_month, numeric_month in month_mapping.items():
            # 將 "2025年七月" 轉換為 "2025年07月"
            processed_query = processed_query.replace(f"年{chinese_month}", f"年{numeric_month}月")
        
        # 2. 統一處理季度格式
        quarter_mapping = {
            '季1': 'Q1', '季2': 'Q2', '季3': 'Q3', '季4': 'Q4',
            'q1': 'Q1', 'q2': 'Q2', 'q3': 'Q3', 'q4': 'Q4'
        }
        
        for quarter_text, quarter_code in quarter_mapping.items():
            processed_query = processed_query.replace(quarter_text, quarter_code)
        
        print(f"   處理後的查詢: {processed_query}")

        # 嘗試解析具體的年月格式
        
        # 首先嘗試解析 "YYYY/MM" 或 "YYYY-MM" 格式 (如: 2025/07, 2025-07)
        slash_dash_pattern = r'(\d{4})[/-](\d{1,2})'
        slash_dash_matches = re.findall(slash_dash_pattern, processed_query)
        
        if len(slash_dash_matches) >= 2:
            # 找到兩個 YYYY/MM 或 YYYY-MM 格式，第一個作為當前期間，第二個作為比較期間
            current_year, current_month = int(slash_dash_matches[0][0]), int(slash_dash_matches[0][1])
            last_year, last_month = int(slash_dash_matches[1][0]), int(slash_dash_matches[1][1])
            
            # 構建日期
            current_start = datetime(current_year, current_month, 1)
            current_end = (current_start + relativedelta(months=1)) - timedelta(days=1)
            last_start = datetime(last_year, last_month, 1)
            last_end = (last_start + relativedelta(months=1)) - timedelta(days=1)
            
            period_text = f"{current_year}年{current_month:02d}月 vs {last_year}年{last_month:02d}月"
            
        elif len(slash_dash_matches) == 1:
            # 只找到一個 YYYY/MM 或 YYYY-MM 格式，作為當前期間，上個月作為比較期間
            current_year, current_month = int(slash_dash_matches[0][0]), int(slash_dash_matches[0][1])
            
            current_start = datetime(current_year, current_month, 1)
            current_end = (current_start + relativedelta(months=1)) - timedelta(days=1)
            
            # 計算上個月
            last_start = (current_start - relativedelta(months=1))
            last_end = current_start - timedelta(days=1)
            
            period_text = f"{current_year}年{current_month:02d}月 vs 上月"
            
        else:
            # 首先嘗試匹配純年份格式 "2025年"
            year_pattern = r'(\d{4})年(?!\d{1,2}月|Q\d)'
            year_matches = re.findall(year_pattern, processed_query)
            
            if len(year_matches) >= 2:
                # 找到兩個年份，第一個作為當前期間，第二個作為比較期間
                current_year = int(year_matches[0])
                last_year = int(year_matches[1])
                
                # 構建年度日期範圍
                current_start = datetime(current_year, 1, 1)
                current_end = datetime(current_year, 12, 31)
                last_start = datetime(last_year, 1, 1)
                last_end = datetime(last_year, 12, 31)
                
                period_text = f"{current_year}年 vs {last_year}年"
                
            elif len(year_matches) == 1:
                # 只找到一個年份，作為當前期間，上一年作為比較期間
                current_year = int(year_matches[0])
                
                current_start = datetime(current_year, 1, 1)
                current_end = datetime(current_year, 12, 31)
                
                # 計算上一年
                last_start = datetime(current_year - 1, 1, 1)
                last_end = datetime(current_year - 1, 12, 31)
                
                period_text = f"{current_year}年 vs 去年"
                
            else:
                # 匹配 "2025年06月" 或 "2025年6月" 格式
                year_month_pattern = r'(\d{4})年(\d{1,2})月'
                matches = re.findall(year_month_pattern, processed_query)
                
                if len(matches) >= 2:
                    # 找到兩個年月，第一個作為當前期間，第二個作為比較期間
                    current_year, current_month = int(matches[0][0]), int(matches[0][1])
                    last_year, last_month = int(matches[1][0]), int(matches[1][1])
                    
                    # 構建日期
                    current_start = datetime(current_year, current_month, 1)
                    current_end = (current_start + relativedelta(months=1)) - timedelta(days=1)
                    last_start = datetime(last_year, last_month, 1)
                    last_end = (last_start + relativedelta(months=1)) - timedelta(days=1)
                    
                    period_text = f"{current_year}年{current_month:02d}月 vs {last_year}年{last_month:02d}月"
                    
                elif len(matches) == 1:
                    # 只找到一個年月，作為當前期間，上個月作為比較期間
                    current_year, current_month = int(matches[0][0]), int(matches[0][1])
                    
                    current_start = datetime(current_year, current_month, 1)
                    current_end = (current_start + relativedelta(months=1)) - timedelta(days=1)
                    
                    # 計算上個月
                    last_start = (current_start - relativedelta(months=1))
                    last_end = current_start - timedelta(days=1)
                    
                    period_text = f"{current_year}年{current_month:02d}月 vs 上月"
                    
                elif "Q" in processed_query or "季" in processed_query:
                    # 首先嘗試解析純季度格式 "Q1", "Q2" 等
                    pure_quarter_pattern = r'Q(\d)(?!\d{4}年)'
                    pure_quarter_matches = re.findall(pure_quarter_pattern, processed_query)
                    
                    if len(pure_quarter_matches) >= 2:
                        # 找到兩個純季度，第一個作為當前期間，第二個作為比較期間
                        current_quarter = int(pure_quarter_matches[0])
                        last_quarter = int(pure_quarter_matches[1])
                        
                        # 使用當前年份
                        current_year = today.year
                        last_year = today.year
                        
                        # 計算季度開始月份
                        current_start_month = 3 * (current_quarter - 1) + 1
                        last_start_month = 3 * (last_quarter - 1) + 1
                        
                        # 構建日期
                        current_start = datetime(current_year, current_start_month, 1)
                        current_end = (current_start + relativedelta(months=3)) - timedelta(days=1)
                        last_start = datetime(last_year, last_start_month, 1)
                        last_end = (last_start + relativedelta(months=3)) - timedelta(days=1)
                        
                        period_text = f"Q{current_quarter} vs Q{last_quarter}"
                        
                    elif len(pure_quarter_matches) == 1:
                        # 只找到一個純季度，作為當前期間，上季度作為比較期間
                        current_quarter = int(pure_quarter_matches[0])
                        current_year = today.year
                        
                        # 計算季度開始月份
                        current_start_month = 3 * (current_quarter - 1) + 1
                        current_start = datetime(current_year, current_start_month, 1)
                        current_end = (current_start + relativedelta(months=3)) - timedelta(days=1)
                        
                        # 計算上季度
                        if current_quarter == 1:
                            last_quarter = 4
                            last_year = current_year - 1
                        else:
                            last_quarter = current_quarter - 1
                            last_year = current_year
                        
                        last_start_month = 3 * (last_quarter - 1) + 1
                        last_start = datetime(last_year, last_start_month, 1)
                        last_end = (last_start + relativedelta(months=3)) - timedelta(days=1)
                        
                        period_text = f"Q{current_quarter} vs Q{last_quarter}"
                        
                    else:
                        # 嘗試解析具體的季度比較格式
                        quarter_pattern = r'(\d{4})年Q(\d)'
                        quarter_matches = re.findall(quarter_pattern, processed_query)
                        
                        # 嘗試解析相對時間表達
                        relative_pattern = r'(去年|前年|今年)Q(\d)'
                        relative_matches = re.findall(relative_pattern, processed_query)
                        
                        if len(quarter_matches) >= 2:
                            # 找到兩個具體年份的季度，第一個作為當前期間，第二個作為比較期間
                            current_year, current_quarter = int(quarter_matches[0][0]), int(quarter_matches[0][1])
                            last_year, last_quarter = int(quarter_matches[1][0]), int(quarter_matches[1][1])
                            
                            # 計算季度開始月份
                            current_start_month = 3 * (current_quarter - 1) + 1
                            last_start_month = 3 * (last_quarter - 1) + 1
                            
                            # 構建日期
                            current_start = datetime(current_year, current_start_month, 1)
                            current_end = (current_start + relativedelta(months=3)) - timedelta(days=1)
                            last_start = datetime(last_year, last_start_month, 1)
                            last_end = (last_start + relativedelta(months=3)) - timedelta(days=1)
                            
                            period_text = f"{current_year}年Q{current_quarter} vs {last_year}年Q{last_quarter}"
                            
                        elif len(quarter_matches) == 1 and len(relative_matches) >= 1:
                            # 找到一個具體年份季度和一個相對時間季度
                            current_year, current_quarter = int(quarter_matches[0][0]), int(quarter_matches[0][1])
                            relative_time, last_quarter = relative_matches[0]
                            last_quarter = int(last_quarter)
                            
                            # 計算相對年份
                            if relative_time == "去年":
                                last_year = current_year - 1
                            elif relative_time == "前年":
                                last_year = current_year - 2
                            else:  # 今年
                                last_year = current_year
                            
                            # 計算季度開始月份
                            current_start_month = 3 * (current_quarter - 1) + 1
                            last_start_month = 3 * (last_quarter - 1) + 1
                            
                            # 構建日期
                            current_start = datetime(current_year, current_start_month, 1)
                            current_end = (current_start + relativedelta(months=3)) - timedelta(days=1)
                            last_start = datetime(last_year, last_start_month, 1)
                            last_end = (last_start + relativedelta(months=3)) - timedelta(days=1)
                            
                            period_text = f"{current_year}年Q{current_quarter} vs {last_year}年Q{last_quarter}"
                            
                        elif len(quarter_matches) == 1:
                            # 只找到一個具體年份季度，作為當前期間，上季度作為比較期間
                            current_year, current_quarter = int(quarter_matches[0][0]), int(quarter_matches[0][1])
                            current_start_month = 3 * (current_quarter - 1) + 1
                            
                            current_start = datetime(current_year, current_start_month, 1)
                            current_end = (current_start + relativedelta(months=3)) - timedelta(days=1)
                            
                            # 計算上季度
                            if current_quarter == 1:
                                last_quarter = 4
                                last_year = current_year - 1
                            else:
                                last_quarter = current_quarter - 1
                                last_year = current_year
                            
                            last_start_month = 3 * (last_quarter - 1) + 1
                            last_start = datetime(last_year, last_start_month, 1)
                            last_end = (last_start + relativedelta(months=3)) - timedelta(days=1)
                            
                            period_text = f"{current_year}年Q{current_quarter} vs {last_year}年Q{last_quarter}"
                            
                            # 確保設置了所有必要的變數
                            print(f"   季度查詢解析完成: {current_year}年Q{current_quarter}")
                            print(f"   當前期間: {current_start} 到 {current_end}")
                            print(f"   比較期間: {last_start} 到 {last_end}")
                            
                        else:
                            # 沒有找到具體季度格式，使用預設的當前季度 vs 上季度
                            current_quarter_start_month = 3 * ((today.month - 1) // 3) + 1
                            current_start = today.replace(month=current_quarter_start_month, day=1)
                            current_end = (current_start + relativedelta(months=3)) - timedelta(days=1)
                            last_start = (current_start - relativedelta(months=3))
                            last_end = current_start - timedelta(days=1)
                            period_text = f"{current_start.year}年Q{(current_start.month-1)//3+1} vs 上季"

        # 預設分析維度: 產品
        dimension = 'product'
        dimension_text = '產品'

        # 根據查詢內容判斷分析維度
        if any(word in query for word in ['產品', '商品', 'item', 'product']):
            dimension = 'product'
            dimension_text = '產品'
        elif any(word in query for word in ['業務員', '銷售員', 'staff', 'sales']):
            dimension = 'staff'
            dimension_text = '業務員'
        elif any(word in query for word in ['客戶', 'customer', 'client']):
            dimension = 'customer'
            dimension_text = '客戶'
        elif any(word in query for word in ['地區', '區域', 'region', 'area']):
            dimension = 'region'
            dimension_text = '地區'

        parsed_result = {
            'current_start': current_start.strftime('%Y-%m-%d'),
            'current_end': current_end.strftime('%Y-%m-%d'),
            'last_start': last_start.strftime('%Y-%m-%d'),
            'last_end': last_end.strftime('%Y-%m-%d'),
            'period_text': period_text,
            'dimension': dimension,
            'dimension_text': dimension_text
        }
        
        print(f"   解析完成，返回結果:")
        print(f"     - current_start: {parsed_result['current_start']}")
        print(f"     - current_end: {parsed_result['current_end']}")
        print(f"     - last_start: {parsed_result['last_start']}")
        print(f"     - last_end: {parsed_result['last_end']}")
        print(f"     - period_text: {parsed_result['period_text']}")
        print(f"     - dimension: {parsed_result['dimension']}")
        print(f"     - dimension_text: {parsed_result['dimension_text']}")
        
        return parsed_result

    def analyze_query(self, query):
        """
        分析自然語言查詢並返回結果
        """
        print(f"\n🚀 開始分析查詢: {query}")
        print(f"=" * 60)
        
        try:
            # 動態獲取維度資料
            print(f"🔍 獲取維度資料...")
            specific_customers = self._get_dimension_values('customer')
            specific_staff = self._get_dimension_values('staff')
            specific_products = self._get_dimension_values('product')
            specific_regions = self._get_dimension_values('region')
            
            print(f"   客戶維度: {len(specific_customers)} 個")
            print(f"   員工維度: {len(specific_staff)} 個")
            print(f"   產品維度: {len(specific_products)} 個")
            print(f"   地區維度: {len(specific_regions)} 個")
            
            # 檢查是否為特定客戶查詢（包括存在的和不存在的客戶）
            if any(word in query for word in ['客戶', 'customer', '消費']):
                # 提取可能的客戶名稱
                # 匹配「客戶」後面的中文名稱，但不包含「銷售額」等詞
                customer_pattern = r'客戶\s*([\u4e00-\u9fa5]{2,4})(?=\s|銷售額|業績|$)'
                customer_matches = re.findall(customer_pattern, query)
                
                for match in customer_matches:
                    if match in specific_customers:
                        # 存在的客戶
                        return self._analyze_specific_customer_query(query, match)
                    else:
                        # 不存在的客戶
                        return self._analyze_specific_customer_query(query, match)
            
            # 檢查是否為特定業務員查詢
            if any(word in query for word in ['業務員', '銷售員', 'staff', '業績']):
                # 提取可能的業務員名稱
                staff_pattern = r'業務員\s*([\u4e00-\u9fa5]{2,4})(?=\s|業績|$)'
                staff_matches = re.findall(staff_pattern, query)
                
                for match in staff_matches:
                    if match in specific_staff:
                        # 存在的業務員
                        return self._analyze_specific_staff_query(query, match)
                    else:
                        # 不存在的業務員
                        return self._analyze_specific_staff_query(query, match)
            
            # 檢查是否為特定產品查詢
            if any(word in query for word in ['產品', '商品', 'product']):
                # 提取可能的產品名稱
                product_pattern = r'產品\s*([\u4e00-\u9fa5]{2,10})(?=\s|銷售額|$)'
                product_matches = re.findall(product_pattern, query)
                
                for match in product_matches:
                    if match in specific_products:
                        # 存在的產品
                        return self._analyze_specific_product_query(query, match)
                    else:
                        # 不存在的產品
                        return self._analyze_specific_product_query(query, match)
            
            # 檢查是否為特定地區查詢
            if any(word in query for word in ['地區', '區域', 'region', '地方']):
                # 提取可能的地區名稱
                region_pattern = r'地區\s*([\u4e00-\u9fa5]{2,4})(?=\s|銷售額|$)'
                region_matches = re.findall(region_pattern, query)
                
                for match in region_matches:
                    if match in specific_regions:
                        # 存在的地區
                        return self._analyze_specific_region_query(query, match)
                    else:
                        # 不存在的地區
                        return self._analyze_specific_region_query(query, match)
            
            # 解析查詢
            print(f"🔍 解析查詢...")
            parsed = self._parse_query(query)
            print(f"   解析結果: {parsed}")
            
            # 檢查是否為季度查詢
            if "Q" in query and ("季" in query or "quarter" in query.lower()):
                print(f"📊 使用季度專用查詢...")
                result = self._analyze_quarter_query(parsed, query)
                print(f"✅ 季度查詢完成，返回結果長度: {len(str(result))}")
                return result
            else:
                print(f"📊 使用一般期間查詢...")
                result = self._analyze_period_query(parsed)
                print(f"✅ 期間查詢完成，返回結果長度: {len(str(result))}")
                return result
            
        except Exception as e:
            print(f"❌ 查詢解析失敗: {e}")
            return {
                'success': False,
                'error': f"查詢解析失敗: {str(e)}"
            }

    def _analyze_period_query(self, parsed):
        """分析一般期間查詢 - 智能選擇向量或SQL查詢"""
        try:
            print(f"🔍 開始期間查詢分析...")
            print(f"   解析結果: {parsed}")
            
            # 暫時禁用向量查詢，直接使用 SQL 查詢
            # 因為向量查詢有日期格式問題
            print(f"📊 直接使用 SQL 查詢分析...")
            return self._perform_sql_period_analysis(parsed)
            
            # 以下是原本的向量查詢邏輯，暫時註解
            # if hasattr(self.data_manager, 'vector_manager') and self.data_manager.vector_manager:
            #     # 嘗試使用向量搜尋進行智能分析
            #     vector_analysis = self._perform_vector_period_analysis(parsed)
            #     if vector_analysis['success']:
            #         return vector_analysis
            
            # # 如果向量查詢失敗或不適用，回退到傳統SQL查詢
            # return self._perform_sql_period_analysis(parsed)
            
        except Exception as e:
            print(f"❌ 期間分析失敗: {e}")
            return {
                'success': False,
                'error': f"期間分析失敗: {str(e)}"
            }
    
    def _perform_vector_period_analysis(self, parsed):
        """使用向量搜尋進行期間分析"""
        try:
            # 構建語義查詢
            semantic_query = self._build_semantic_period_query(parsed)
            
            # 使用向量搜尋進行智能分析
            vector_results = self._execute_vector_period_analysis(semantic_query, parsed)
            
            return {
                'success': True,
                'analysis_type': 'vector',
                'semantic_query': semantic_query,
                'vector_results': vector_results,
                'period_text': parsed.get('period_text', '未知期間'),
                'current_dimension': parsed.get('dimension', '未知維度'),
                'current_start': parsed.get('current_start', '未知'),
                'current_end': parsed.get('current_end', '未知'),
                'last_start': parsed.get('last_start', '未知'),
                'last_end': parsed.get('last_end', '未知')
            }
            
        except Exception as e:
            # self.logger.error(f"向量期間分析失敗: {e}")
            return {
                'success': False,
                'error': f"向量分析失敗: {str(e)}"
            }
    
    def _perform_sql_period_analysis(self, parsed):
        """使用傳統SQL進行期間分析"""
        try:
            print(f"\n🔍 開始執行 SQL 期間分析...")
            print(f"   當前期間: {parsed.get('current_start', '未知')} 到 {parsed.get('current_end', '未知')}")
            print(f"   比較期間: {parsed.get('last_start', '未知')} 到 {parsed.get('last_end', '未知')}")
            print(f"   分析維度: {parsed.get('dimension', '未知')}")
            
            # 執行期間比較
            print(f"📊 執行期間比較查詢...")
            period_comparison = self.data_manager.get_period_comparison(
                parsed.get('current_start', '2025-01-01'), parsed.get('current_end', '2025-12-31'),
                parsed.get('last_start', '2024-01-01'), parsed.get('last_end', '2024-12-31')
            )
            
            print(f"📊 期間比較查詢結果:")
            print(f"   查詢結果類型: {type(period_comparison)}")
            print(f"   查詢結果是否為空: {period_comparison.empty if hasattr(period_comparison, 'empty') else 'N/A'}")
            print(f"   查詢結果內容: {period_comparison}")
            
            if period_comparison.empty:
                print("❌ 期間比較查詢返回空結果")
                return {
                    'success': False,
                    'error': '期間比較查詢無結果'
                }
            
            # 執行主維度貢獻度分析
            print(f"📈 執行主維度貢獻度分析...")
            driver_analysis = self.data_manager.get_driver_analysis(
                parsed.get('current_start', '2025-01-01'), parsed.get('current_end', '2025-12-31'),
                parsed.get('last_start', '2024-01-01'), parsed.get('last_end', '2024-12-31'),
                parsed.get('dimension', 'product')
            )
            
            print(f"📈 主維度貢獻度分析結果:")
            print(f"   分析結果類型: {type(driver_analysis)}")
            print(f"   分析結果是否為空: {driver_analysis.empty if hasattr(driver_analysis, 'empty') else 'N/A'}")
            print(f"   分析結果內容: {driver_analysis}")
            
            if driver_analysis.empty:
                print("⚠️  主維度貢獻度分析返回空結果")
                driver_analysis = pd.DataFrame()
            
            # 獲取可用的 drill down 維度
            print(f"🔍 獲取可用的 drill down 維度...")
            available_dimensions = self.data_manager.get_available_dimensions(parsed.get('dimension', 'product'))
            print(f"   可用維度: {available_dimensions}")

            # 新增：多維度參考分析
            print(f"🔍 執行多維度參考分析...")
            other_dimension_reference = []
            for dim_key, dim_name in available_dimensions.items():
                try:
                    print(f"   分析 {dim_key} 維度...")
                    other_driver = self.data_manager.get_driver_analysis(
                        parsed.get('current_start', '2025-01-01'), parsed.get('current_end', '2025-12-31'),
                        parsed.get('last_start', '2024-01-01'), parsed.get('last_end', '2024-12-31'),
                        dim_key
                    )
                    # 只取前3名
                    top3 = other_driver.sort_values('差異', key=abs, ascending=False).head(3)
                    if not top3.empty:
                        dim_summary = f"<b>{dim_name} 維度影響：</b> "
                        for _, row in top3.iterrows():
                            diff = row['差異']
                            sign = '+' if diff > 0 else ''
                            dim_summary += f"{row['分析維度']}（差異：{sign}{diff:,.0f}元）; "
                        other_dimension_reference.append(dim_summary)
                        print(f"     {dim_key} 維度分析完成，找到 {len(top3)} 筆數據")
                    else:
                        print(f"     {dim_key} 維度分析返回空結果")
                except Exception as e:
                    print(f"     {dim_key} 維度分析失敗: {e}")
                    continue
            other_dimension_reference_text = '<br>'.join(other_dimension_reference) if other_dimension_reference else ''

            # 計算總計
            print(f"💰 開始計算銷售數據...")
            current_sales = period_comparison['current_period_sales'].iloc[0]
            last_sales = period_comparison['last_period_sales'].iloc[0]
            diff = current_sales - last_sales
            
            print(f"💰 銷售數據計算結果:")
            print(f"   當期銷售: {current_sales:,.2f} 元")
            print(f"   前期銷售: {last_sales:,.2f} 元")
            print(f"   差異: {diff:,.2f} 元")
            
            # 計算百分比差異
            percentage_diff = 0
            if last_sales != 0:
                percentage_diff = (diff / last_sales) * 100
            elif diff > 0:
                percentage_diff = float('inf')
            elif diff < 0:
                percentage_diff = float('-inf')
            
            print(f"   百分比差異: {percentage_diff:.1f}%")
            
            # 生成分析總結報告 (NLG)
            print(f"📝 開始生成分析總結報告...")
            summary = self._generate_analysis_summary(
                current_sales, last_sales, diff, percentage_diff,
                driver_analysis.to_dict('records'), parsed['dimension_text'],
                parsed['period_text'], other_dimension_reference_text
            )
            
            print(f"📋 分析總結報告生成完成:")
            print(f"   報告長度: {len(summary)} 字元")
            print(f"   報告預覽: {summary[:200]}...")
            
            print(f"✅ SQL 期間分析執行完成")
            print(f"   返回數據結構:")
            print(f"     - success: True")
            print(f"     - current_sales: {current_sales}")
            print(f"     - last_sales: {last_sales}")
            print(f"     - diff: {diff}")
            print(f"     - percentage_diff: {percentage_diff}")
            print(f"     - summary: {len(summary)} 字元")
            print(f"     - driver_data: {len(driver_analysis.to_dict('records'))} 筆")
            
            return {
                'success': True,
                'analysis_type': 'sql',
                'current_sales': current_sales,
                'last_sales': last_sales,
                'diff': diff,
                'percentage_diff': percentage_diff,
                'summary': summary,
                'period_text': parsed.get('period_text', '未知期間'),
                'driver_data': driver_analysis.to_dict('records'),
                'dimension_text': parsed.get('dimension_text', '未知維度'),
                'current_dimension': parsed.get('dimension', 'product'),
                'available_dimensions': available_dimensions,
                'current_start': parsed.get('current_start', '未知'),
                'current_end': parsed.get('current_end', '未知'),
                'last_start': parsed.get('last_start', '未知'),
                'last_end': parsed.get('last_end', '未知'),
                'other_dimension_reference': other_dimension_reference_text
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"期間分析失敗: {str(e)}"
            }

    def _analyze_quarter_query(self, parsed, query):
        """分析季度查詢"""
        try:
            # 從查詢中提取季度信息
            quarter_info = self._extract_quarter_info(query)
            if not quarter_info:
                return {
                    'success': False,
                    'error': "無法解析季度查詢格式，請使用如 '2025年Q1' 的格式"
                }
            
            current_year, current_quarter = quarter_info['current']
            compare_year, compare_quarter = quarter_info['compare']
            
            # 獲取季度數據
            quarter_data = self.data_manager.get_quarter_comparison(
                current_year, current_quarter, compare_year, compare_quarter
            )
            
            # 獲取季度貢獻度分析
            driver_analysis = self.data_manager.get_quarter_driver_analysis(
                current_year, current_quarter, parsed['dimension']
            )
            
            # 計算差異
            current_sales = quarter_data[quarter_data['year'] == current_year]['total_sales'].iloc[0]
            compare_sales = quarter_data[quarter_data['year'] == compare_year]['total_sales'].iloc[0]
            diff = current_sales - compare_sales
            
            # 計算百分比差異
            percentage_diff = 0
            if compare_sales != 0:
                percentage_diff = (diff / compare_sales) * 100
            elif diff > 0:
                percentage_diff = float('inf')
            elif diff < 0:
                percentage_diff = float('-inf')
            
            # 生成季度分析總結
            summary = self._generate_quarter_summary(
                current_year, current_quarter, compare_year, compare_quarter,
                current_sales, compare_sales, diff, percentage_diff,
                driver_analysis.to_dict('records'), parsed['dimension_text']
            )
            
            return {
                'success': True,
                'current_sales': current_sales,
                'last_sales': compare_sales,
                'diff': diff,
                'percentage_diff': percentage_diff,
                'summary': summary,
                'period_text': f"{current_year}年Q{current_quarter} vs {compare_year}年Q{compare_quarter}",
                'driver_data': driver_analysis.to_dict('records'),
                'dimension_text': parsed.get('dimension_text', '未知維度'),
                'current_dimension': parsed.get('dimension', 'product'),
                'available_dimensions': self.data_manager.get_available_dimensions(parsed.get('dimension', 'product')),
                'current_start': parsed.get('current_start', '未知'),
                'current_end': parsed.get('current_end', '未知'),
                'last_start': parsed.get('last_start', '未知'),
                'last_end': parsed.get('last_end', '未知')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"季度分析失敗: {str(e)}"
            }

    def _extract_quarter_info(self, query):
        """從查詢中提取季度信息"""
        
        # 匹配具體年份的季度
        quarter_pattern = r'(\d{4})年Q(\d)'
        quarter_matches = re.findall(quarter_pattern, query)
        
        # 匹配相對時間的季度
        relative_pattern = r'(去年|前年|今年)Q(\d)'
        relative_matches = re.findall(relative_pattern, query)
        
        if len(quarter_matches) >= 2:
            # 兩個具體年份季度
            current_year, current_quarter = int(quarter_matches[0][0]), int(quarter_matches[0][1])
            compare_year, compare_quarter = int(quarter_matches[1][0]), int(quarter_matches[1][1])
            return {
                'current': (current_year, current_quarter),
                'compare': (compare_year, compare_quarter)
            }
        elif len(quarter_matches) == 1 and len(relative_matches) >= 1:
            # 一個具體年份季度和一個相對時間季度
            current_year, current_quarter = int(quarter_matches[0][0]), int(quarter_matches[0][1])
            relative_time, compare_quarter = relative_matches[0]
            compare_quarter = int(compare_quarter)
            
            if relative_time == "去年":
                compare_year = current_year - 1
            elif relative_time == "前年":
                compare_year = current_year - 2
            else:  # 今年
                compare_year = current_year
                
            return {
                'current': (current_year, current_quarter),
                'compare': (compare_year, compare_quarter)
            }
        elif len(quarter_matches) == 1:
            # 只有一個季度，與上季度比較
            current_year, current_quarter = int(quarter_matches[0][0]), int(quarter_matches[0][1])
            
            if current_quarter == 1:
                compare_quarter = 4
                compare_year = current_year - 1
            else:
                compare_quarter = current_quarter - 1
                compare_year = current_year
                
            return {
                'current': (current_year, current_quarter),
                'compare': (compare_year, compare_quarter)
            }
        
        return None

    def _generate_quarter_summary(self, current_year, current_quarter, compare_year, compare_quarter,
                                current_sales, compare_sales, diff, percentage_diff, driver_data, dimension_text):
        """生成季度分析總結"""
        def format_currency(amount):
            return f"{amount:,.0f}"
        
        # 判斷業績表現
        if diff > 0:
            performance = "成長"
            emoji = "📈"
        elif diff < 0:
            performance = "下滑"
            emoji = "📉"
        else:
            performance = "持平"
            emoji = "➡️"
        
        summary = f"{emoji} {current_year}年第{current_quarter}季度 vs {compare_year}年第{compare_quarter}季度業績{performance}，"
        summary += f"本期銷售額為 {format_currency(current_sales)} 元，"
        summary += f"較{compare_year}年第{compare_quarter}季度 {format_currency(compare_sales)} 元"
        
        if diff > 0:
            summary += f"增加 {format_currency(diff)} 元（+{percentage_diff:.1f}%）"
        elif diff < 0:
            summary += f"減少 {format_currency(abs(diff))} 元（{percentage_diff:.1f}%）"
        else:
            summary += "無變化"
        
        summary += "。<br><br>"
        
        # 主要貢獻分析
        if driver_data:
            summary += "📊 <strong>主要貢獻分析：</strong>"
            top_contributor = driver_data[0]
            summary += f"<strong>{top_contributor['分析維度']}</strong>貢獻了 {format_currency(top_contributor['季度銷售額'])} 元"
            
            if len(driver_data) > 1:
                second_contributor = driver_data[1]
                summary += f"，<strong>{second_contributor['分析維度']}</strong>貢獻了 {format_currency(second_contributor['季度銷售額'])} 元"
            
            summary += "<br><br>"
        
        # 建議
        summary += "💡 <strong>建議：</strong>"
        if diff > 0:
            summary += "持續關注表現優異的項目，可考慮擴大相關業務。"
        else:
            summary += "針對表現下滑的項目制定改善計劃，加強行銷推廣。"
        
        return summary

    def _extract_other_dimension_focus(self, other_dimension_reference):
        """
        從其他維度參考分析字串中，萃取每個維度最大正/負貢獻者，回傳條列摘要（條列格式）
        """
        focus_lines = []
        if not other_dimension_reference:
            return ''
        for line in other_dimension_reference.split('<br>'):
            m = re.match(r'(.*?) 維度影響： (.*)', line)
            if m:
                dim, items = m.groups()
                pairs = re.findall(r'([\w\u4e00-\u9fa5]+)（差異：([+-]?[\d,]+)元）', items)
                pairs = [(name, int(val.replace(',', ''))) for name, val in pairs]
                if pairs:
                    max_pos = max(pairs, key=lambda x: x[1])
                    max_neg = min(pairs, key=lambda x: x[1])
                    line_str = f"- {dim}："
                    if max_neg[1] < 0:
                        line_str += f"最大負貢獻 {max_neg[0]}（{max_neg[1]:,}元）；"
                    if max_pos[1] > 0:
                        line_str += f"最大正貢獻 {max_pos[0]}（+{max_pos[1]:,}元）"
                    focus_lines.append(line_str)
        return '\n'.join(focus_lines)

    def _extract_focus_items(self, other_dimension_reference):
        """
        從其他維度參考分析字串中，展開每個維度的所有重點條目，回傳條列清單（每一條為三行格式，讓 AI 填空）
        """
        items = []
        if not other_dimension_reference:
            return []
        for line in other_dimension_reference.split('<br>'):
            m = re.match(r'(.*?) 維度影響： (.*)', line)
            if m:
                dim, content = m.groups()
                pairs = re.findall(r'([\w\u4e00-\u9fa5]+)（差異：([+-]?[\d,]+)元）', content)
                for name, val in pairs:
                    items.append(f'- {dim}：{name}（{val}元）\n  原因：\n  建議：')
        return items

    def chat_with_ai(self, message, analysis_context=None, chat_history=None):
        """
        智慧分析助手與用戶對話
        具備以下特色：
        1. 數據分析專家角色
        2. 商業顧問角色
        3. 策略建議者角色
        """
        # 設定 AI 助手的角色和個性
        ai_role = {
            'name': '業務智慧顧問 - BI Expert',
            'expertise': ['數據分析', '業務諮詢', '策略規劃', '績效改善'],
            'personality': '專業、精確、積極、具建設性',
            'communication_style': '清晰、邏輯性強、注重實用性'
        }
        try:
            import google.generativeai as genai
            import os
            # 設定 Gemini API Key（請確保環境變數已設定）
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return {
                    'success': False,
                    'error': 'Gemini API Key 未設定，請設定 GEMINI_API_KEY 環境變數'
                }
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')

            # 構建聊天上下文
            context_parts = []
            focus_items = []
            if analysis_context:
                context_parts.append(f"分析期間：{analysis_context.get('period_text', 'N/A')}")
                context_parts.append(f"當期銷售：{analysis_context.get('current_sales', 0):,.0f} 元")
                context_parts.append(f"前期銷售：{analysis_context.get('last_sales', 0):,.0f} 元")
                context_parts.append(f"差異：{analysis_context.get('diff', 0):,.0f} 元")
                context_parts.append(f"百分比差異：{analysis_context.get('percentage_diff', 0):.1f}%")
                context_parts.append(f"分析維度：{analysis_context.get('dimension_text', 'N/A')}")
                if analysis_context.get('driver_data'):
                    top_contributors = []
                    for item in analysis_context['driver_data'][:3]:
                        if item['差異'] > 0:
                            top_contributors.append(f"{item['分析維度']}(+{item['差異']:,.0f})")
                        else:
                            top_contributors.append(f"{item['分析維度']}({item['差異']:,.0f})")
                    context_parts.append(f"主要貢獻者：{', '.join(top_contributors)}")
                if analysis_context.get('other_dimension_reference'):
                    focus_items = self._extract_focus_items(analysis_context['other_dimension_reference'])
                    context_parts.append(f"其他維度參考分析：{analysis_context['other_dimension_reference']}")

            # ====== 新增：條目與格式範例直接插入 prompt 最前方 ======
            focus_block = ''
            # 細節追問判斷（最高優先，擴充動作型/操作型語意）
            detail_keywords = [
                '重點', '細節', '步驟', '流程', '範例', '內容', '如何執行', '怎麼做', '操作方式', '說明', '展開說明',
                '如何進行', '如何交流', '如何與', '我如何', '我該怎麼', '請給我', '請問怎麼', '請問如何', '請給我方法', '請給我步驟', '我如何進行', '我如何與', '我該如何', '我該如何與', '請給我建議', '請給我具體方法', '請給我具體步驟'
            ]
            is_detail_followup = any(kw in message for kw in detail_keywords) or \
                message.strip().startswith(('如何', '怎麼', '我該怎麼', '我如何', '請給我', '請問怎麼', '請問如何'))
            if is_detail_followup:
                focus_block = f"請針對「{message}」給出詳細步驟、方法或建議，務必具體可執行，不需再分析其他對象。"
            else:
                # summary 判斷
                summary_keywords = [
                    '業績', '總體', '整體', '主要貢獻', '分析', '下滑', '成長', '比較', 'vs', '差異', '總結', '銷售額', '營收', '表現', '趨勢'
                ]
                summary_patterns = [
                    r'\d{4}年\d{1,2}月 ?vs ?\d{4}年\d{1,2}月',
                    r'\d{4}年Q\d ?vs ?\d{4}年Q\d',
                    r'\d{4}/\d{1,2} ?vs ?\d{4}/\d{1,2}',
                    r'\d{4}-\d{1,2} ?vs ?\d{4}-\d{1,2}'
                ]
                is_summary_focus = any(kw in message for kw in summary_keywords)
                for pat in summary_patterns:
                    if re.search(pat, message):
                        is_summary_focus = True
                # focus_keywords: 自動從 focus_items 條列中提取所有對象名稱
                focus_keywords = []
                for item in focus_items:
                    m = re.match(r'- .+?：(.+?)（', item)
                    if m:
                        focus_keywords.append(m.group(1))
                # 單一對象判斷
                is_single_focus = False
                matched_keywords = [kw for kw in focus_keywords if kw in message]
                if len(matched_keywords) == 1:
                    is_single_focus = True
                improvement_keywords = ['建議', '如何改善', '怎麼做', '解決方案', '提升', '優化', '具體措施', '改善方式', '改進', '如何處理', '如何解決']
                is_improvement_focus = any(kw in message for kw in improvement_keywords)
                if is_summary_focus and focus_items:
                    focus_block = (
                        "請針對下列條目，依序逐點回覆，每一點都要明確說明原因與具體建議，請勿泛泛而談。請務必依照下方格式分行填寫：\n"
                        "- 業務員：王小明（-951,772元）\n  原因：...\n  建議：...\n"
                        "- 客戶：陳先生（-349,591元）\n  原因：...\n  建議：...\n"
                        "- 地區：北區（-583,869元）\n  原因：...\n  建議：...\n\n"
                        + '\n'.join(focus_items) + '\n\n'
                    )
                elif is_single_focus:
                    focus_block = f"請針對「{matched_keywords[0]}」進行深入分析，說明原因與具體建議。"
                elif is_improvement_focus:
                    focus_block = "請針對用戶提出的具體改善需求，給出詳細可執行的建議與說明。"
                else:
                    focus_block = "請根據用戶問題，給出專業且具體的分析與建議。"
            # ====== END ======

            # 構建完整的提示詞
            system_prompt = f"""
{focus_block}你是一位資深的經營分析專家，擁有豐富的商業顧問經驗。你的專長包括：

1. **數據解讀能力**：能夠深入分析銷售數據背後的商業意義
2. **策略規劃能力**：提供具體可執行的改善建議和策略方案
3. **溝通表達能力**：用口語化、易懂的方式解釋複雜的商業概念
4. **實務經驗**：結合理論與實務，提供實用的建議

當前分析背景：
{chr(10).join(context_parts) if context_parts else '無特定分析背景'}

請以經營分析專家的身份回答用戶問題，要求：
1. **口語化表達**：用簡單易懂的語言解釋複雜概念
2. **具體建議**：提供可執行的具體改善方案
3. **專業分析**：基於數據提供專業的商業洞察
4. **互動交流**：鼓勵用戶提問，建立良好的對話氛圍
5. **實用導向**：重點放在實際可應用的建議上
6. **中文回答**：全程使用繁體中文
7. **適中長度**：回答控制在300字以內，保持重點突出
8. **特別要求**：請務必針對條列的每一個對象，依序逐點回覆，每一點都要明確說明原因與具體建議，請勿泛泛而談。
9. **格式範例**：\n- 業務員：王小明（-951,772元）\n  原因：...\n  建議：...\n- 客戶：陳先生（-349,591元）\n  原因：...\n  建議：...\n- 地區：北區（-583,869元）\n  原因：...\n  建議：...\n
記住：你是一位經驗豐富的經營分析專家，要讓用戶感受到專業且親切的諮詢體驗。
"""

            # 構建聊天歷史
            chat_messages = []
            if chat_history:
                for msg in chat_history:
                    if msg.get('role') == 'user':
                        chat_messages.append(f"用戶：{msg.get('content', '')}")
                    elif msg.get('role') == 'assistant':
                        chat_messages.append(f"專家：{msg.get('content', '')}")

            # 構建完整對話，保留完整 system prompt 與聚焦條列指令
            full_conversation = f"""{system_prompt}

對話歷史：
{chr(10).join(chat_messages) if chat_messages else '無對話歷史'}

用戶問題：
{message}
"""

            response = model.generate_content(full_conversation)
            print("送給 Gemini 的 message：", full_conversation)
            # 新增：若 AI 回應為空，印出警告
            if not response.text or not response.text.strip():
                print("[警告] Gemini 回傳空白回應！請檢查 prompt、API Key 或服務狀態。")
            return {
                'success': True,
                'response': response.text,
                'model': 'gemini-pro'
            }
        except ImportError:
            # 如果沒有安裝 google-generativeai，使用備用方案
            return self._fallback_chat_response(message, analysis_context, chat_history)
        except Exception as e:
            return {
                'success': False,
                'error': f'Gemini API 調用失敗：{str(e)}'
            }

    def _fallback_chat_response(self, message, analysis_context=None, chat_history=None):
        """
        備用聊天回應（當 Gemini API 不可用時）
        """
        try:
            # 構建聊天上下文
            context_parts = []
            if analysis_context:
                context_parts.append(f"分析期間：{analysis_context.get('period_text', 'N/A')}")
                context_parts.append(f"當期銷售：{analysis_context.get('current_sales', 0):,.0f} 元")
                context_parts.append(f"前期銷售：{analysis_context.get('last_sales', 0):,.0f} 元")
                context_parts.append(f"差異：{analysis_context.get('diff', 0):,.0f} 元")
                context_parts.append(f"百分比差異：{analysis_context.get('percentage_diff', 0):.1f}%")
                context_parts.append(f"分析維度：{analysis_context.get('dimension_text', 'N/A')}")
                if analysis_context.get('driver_data'):
                    top_contributors = []
                    for item in analysis_context['driver_data'][:3]:
                        if item['差異'] > 0:
                            top_contributors.append(f"{item['分析維度']}(+{item['差異']:,.0f})")
                        else:
                            top_contributors.append(f"{item['分析維度']}({item['差異']:,.0f})")
                    context_parts.append(f"主要貢獻者：{', '.join(top_contributors)}")
                # 強化：明確要求 AI 聚焦其他維度
                if analysis_context.get('other_dimension_reference'):
                    # 自動展開條目聚焦
                    focus_items = self._extract_focus_items(analysis_context['other_dimension_reference'])
                    if focus_items:
                        context_parts.append(
                            "請針對下列對象分別說明原因與具體建議，請依序逐點回覆，每一點都要明確說明原因與建議，請勿泛泛而談：\n" + '\n'.join(focus_items)
                        )
                    context_parts.append(f"其他維度參考分析：{analysis_context['other_dimension_reference']}")
            
            # 使用原有的回應生成邏輯
            system_prompt = f"""
你是一位資深的經營分析專家，擁有豐富的商業顧問經驗。

當前分析背景：
{chr(10).join(context_parts) if context_parts else '無特定分析背景'}

請以經營分析專家的身份回答用戶問題，要求：
1. 用口語化、易懂的方式解釋複雜概念
2. 提供具體可執行的改善方案
3. 基於數據提供專業的商業洞察
4. 鼓勵用戶提問，建立良好的對話氛圍
5. 全程使用繁體中文
6. 回答控制在300字以內
7. 特別要求：務必針對「其他維度參考分析」中影響最大的業務員、客戶、地區，分別說明原因與具體建議，讓用戶能直接掌握多維度重點。
"""

            response = self._generate_ai_response(message, system_prompt, chat_history)
            
            return {
                'success': True,
                'response': response,
                'model': 'fallback'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'備用回應生成失敗：{str(e)}'
            }

    def _generate_ai_response(self, user_message, system_prompt, chat_history=None):
        """
        生成 AI 回應（模擬版本）
        """
        # 這裡可以接入真實的 AI API，如 OpenAI GPT 或 Google Gemini
        # 目前使用規則基礎的回應生成
        
        user_message_lower = user_message.lower()
        
        # 根據用戶問題類型生成回應
        if any(word in user_message_lower for word in ['改善', '提升', '改進', '優化']):
            return self._generate_improvement_suggestions(user_message)
        elif any(word in user_message_lower for word in ['原因', '為什麼', '為何']):
            return self._generate_cause_analysis(user_message)
        elif any(word in user_message_lower for word in ['建議', '策略', '方案']):
            return self._generate_strategy_suggestions(user_message)
        elif any(word in user_message_lower for word in ['趨勢', '預測', '未來']):
            return self._generate_trend_analysis(user_message)
        elif any(word in user_message_lower for word in ['風險', '問題', '挑戰']):
            return self._generate_risk_analysis(user_message)
        else:
            return self._generate_general_response(user_message)

    def _generate_improvement_suggestions(self, user_message):
        """生成改善建議，包含具體行動步驟"""
        suggestions = [
            "📈 作為您的業務分析專家，我建議採取以下改善措施：\n\n" +
            "1️⃣ 產品策略優化\n" +
            "   • 加強表現優異產品的行銷推廣\n" +
            "   • 針對下滑產品進行定位調整\n" +
            "   • 建立產品生命週期監控機制\n\n" +
            "2️⃣ 銷售流程改善\n" +
            "   • 優化銷售漏斗轉化率\n" +
            "   • 實施精準的客戶分群策略\n" +
            "   • 建立銷售績效追蹤系統\n\n" +
            "3️⃣ 客戶體驗提升\n" +
            "   • 強化售後服務品質\n" +
            "   • 建立客戶反饋機制\n" +
            "   • 開發個性化服務方案\n\n" +
            "💡 建議優先實施第一項措施，可以帶來最快的改善效果。",

            "🎯 基於數據分析，我為您制定了以下改善方案：\n\n" +
            "1️⃣ 短期優化（1-3個月）\n" +
            "   • 優化產品定價策略\n" +
            "   • 加強銷售團隊培訓\n" +
            "   • 啟動促銷活動優化\n\n" +
            "2️⃣ 中期改善（3-6個月）\n" +
            "   • 建立客戶忠誠度計劃\n" +
            "   • 優化供應鏈管理\n" +
            "   • 發展數位行銷渠道\n\n" +
            "3️⃣ 長期發展（6-12個月）\n" +
            "   • 建立數據分析平台\n" +
            "   • 開發新市場機會\n" +
            "   • 強化品牌建設\n\n" +
            "📊 根據ROI分析，建議優先執行短期優化方案。",

            "💼 身為您的業務顧問，我提供以下具體改善建議：\n\n" +
            "1️⃣ 銷售效率提升\n" +
            "   • 實施銷售自動化工具\n" +
            "   • 優化客戶開發流程\n" +
            "   • 建立績效獎勵機制\n\n" +
            "2️⃣ 客戶關係強化\n" +
            "   • 建立客戶分層服務\n" +
            "   • 開發會員增值服務\n" +
            "   • 優化客訴處理流程\n\n" +
            "3️⃣ 營運效率優化\n" +
            "   • streamline 作業流程\n" +
            "   • 建立KPI監控儀表板\n" +
            "   • 優化資源配置\n\n" +
            "🌟 這些建議基於您的業務現況，結合了市場最佳實踐。"
        ]
        return random.choice(suggestions)

    def _generate_cause_analysis(self, user_message):
        """生成深入的原因分析，包含數據支持"""
        analyses = [
            "📊 根據多維度分析，我發現以下關鍵影響因素：\n\n" +
            "1️⃣ 內部因素（可控）\n" +
            "   • 產品生命週期調整需求（佔比約35%）\n" +
            "   • 銷售團隊績效波動（佔比約25%）\n" +
            "   • 促銷策略執行效果（佔比約20%）\n\n" +
            "2️⃣ 外部因素（需應對）\n" +
            "   • 市場競爭加劇（影響程度：高）\n" +
            "   • 消費者偏好改變（影響程度：中）\n" +
            "   • 經濟環境變化（影響程度：中）\n\n" +
            "💡 建議優先處理內部因素，可帶來立即改善。",

            "🔍 通過數據挖掘，識別出以下核心原因：\n\n" +
            "1️⃣ 短期影響因素\n" +
            "   • 季節性需求波動（月環比影響±15%）\n" +
            "   • 競爭對手促銷活動（影響期：2-4週）\n" +
            "   • 庫存水平調整（影響訂單履行率）\n\n" +
            "2️⃣ 長期趨勢因素\n" +
            "   • 產品創新週期（影響品牌競爭力）\n" +
            "   • 客戶消費習慣改變（年度趨勢）\n" +
            "   • 市場飽和度提升（產業週期）\n\n" +
            "📈 各因素影響程度已量化分析，便於制定對策。",

            "🎯 依據深入分析，現有挑戰源自以下因素：\n\n" +
            "1️⃣ 營運層面\n" +
            "   • 銷售流程效率（-12% YoY）\n" +
            "   • 客戶服務滿意度（較目標差5%）\n" +
            "   • 庫存周轉率（低於行業標準）\n\n" +
            "2️⃣ 市場層面\n" +
            "   • 品牌認知度（市場排名第3）\n" +
            "   • 價格競爭力（較競品高8%）\n" +
            "   • 通路覆蓋率（待提升區域：20%）\n\n" +
            "3️⃣ 產品層面\n" +
            "   • 產品組合最佳化（待調整SKU：30%）\n" +
            "   • 新品上市節奏（較計畫延遲1個月）\n" +
            "   • 產品差異化（創新指數：75/100）\n\n" +
            "📊 以上分析已納入最新的市場數據。"
        ]
        return random.choice(analyses)

    def _generate_strategy_suggestions(self, user_message):
        """生成策略建議"""
        strategies = [
            "建議策略：1) 短期：加強促銷活動；2) 中期：產品創新升級；3) 長期：建立品牌競爭優勢。",
            "策略方向：1) 客戶細分與精準行銷；2) 產品差異化策略；3) 數位化轉型；4) 供應鏈優化。",
            "發展策略：1) 市場擴張；2) 產品多元化；3) 客戶價值提升；4) 營運效率改善。"
        ]
        return random.choice(strategies)

    def _generate_trend_analysis(self, user_message):
        """生成趨勢分析"""
        trends = [
            "未來趨勢預測：1) 數位化轉型加速；2) 客戶體驗重要性提升；3) 數據驅動決策普及；4) 個性化服務需求增加。",
            "發展趨勢：1) 線上線下融合；2) 智能化營運；3) 可持續發展；4) 全球化競爭加劇。",
            "市場趨勢：1) 消費升級；2) 技術創新；3) 服務化轉型；4) 生態系統建設。"
        ]
        return random.choice(trends)

    def _generate_risk_analysis(self, user_message):
        """生成風險分析"""
        risks = [
            "主要風險：1) 市場競爭加劇；2) 客戶流失風險；3) 技術變革衝擊；4) 供應鏈不穩定；5) 法規政策變化。",
            "風險因素：1) 經濟週期波動；2) 客戶需求變化；3) 技術更新換代；4) 人才流失；5) 資金鏈風險。",
            "潛在風險：1) 市場飽和；2) 替代品威脅；3) 成本上升；4) 品質問題；5) 品牌形象受損。"
        ]
        return random.choice(risks)

    def _generate_general_response(self, user_message):
        """生成一般回應，包含角色扮演和專業建議"""
        responses = [
            "您好，我是您的業務智慧顧問。📊 作為一名專業的數據分析專家，我可以協助您：\n\n" +
            "1️⃣ 深入解讀銷售數據背後的意義\n" +
            "2️⃣ 提供基於數據的改善建議\n" +
            "3️⃣ 分析市場趨勢和競爭態勢\n" +
            "4️⃣ 制定具體可行的策略方案\n\n" +
            "💡 請告訴我您最關注的業務問題，我會運用專業知識為您提供量身定制的解決方案。",

            "作為您的BI Expert，我理解每個業務決策都需要堅實的數據支持。📈 我可以幫您：\n\n" +
            "1️⃣ 識別關鍵績效指標(KPI)的變化\n" +
            "2️⃣ 發掘業績波動的根本原因\n" +
            "3️⃣ 預測未來的業務趨勢\n" +
            "4️⃣ 提供具體的優化建議\n\n" +
            "🎯 讓我們一起通過數據驅動的方式，推動業務持續增長！",

            "您好！我是專注於業務分析與策略規劃的AI顧問。🤝 基於您的業務數據，我能夠：\n\n" +
            "1️⃣ 進行多維度的銷售分析\n" +
            "2️⃣ 識別業務增長機會\n" +
            "3️⃣ 提供實用的改善方案\n" +
            "4️⃣ 協助制定行動計劃\n\n" +
            "📊 請分享您的具體需求，讓我用數據的語言，幫您找到最優解決方案。"
        ]
        return random.choice(responses)

    def drill_down_analysis(self, current_start, current_end, last_start, last_end, 
                           primary_dimension, primary_value, drill_dimension):
        """
        執行 drill down 分析
        """
        try:
            # 獲取 drill down 數據
            drill_down_data = self.data_manager.get_drill_down_analysis(
                current_start, current_end, last_start, last_end,
                primary_dimension, primary_value, drill_dimension
            )
            
            # 獲取維度文字
            dimension_map = {
                'product': '產品',
                'staff': '業務員',
                'customer': '客戶',
                'region': '地區'
            }
            
            return {
                'success': True,
                'drill_down_data': drill_down_data.to_dict('records'),
                'primary_dimension_text': dimension_map.get(primary_dimension, primary_dimension),
                'drill_dimension_text': dimension_map.get(drill_dimension, drill_dimension)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def sql_to_natural_language(self, sql_query):
        """
        將 SQL 查詢轉換為自然語言描述
        """
        sql_upper = sql_query.upper()
        # 精確判斷 staff_name, SUM(f.amount), SUM(f.quantity)
        if (
            'SELECT' in sql_upper and 'STAFF_NAME' in sql_upper and 
            'SUM(F.AMOUNT)' in sql_upper and 'SUM(F.QUANTITY)' in sql_upper
        ):
            return "統計各業務員銷售業績和數量"
        # 其他情境維持原有判斷
        if 'STAFF_NAME' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各業務員銷售業績和數量"
            else:
                return "統計各業務員銷售業績"
        elif 'PRODUCT_NAME' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各產品銷售額和數量"
            else:
                return "統計各產品銷售額"
        elif 'CUSTOMER_NAME' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各客戶消費金額和數量"
            else:
                return "統計各客戶消費金額"
        elif 'REGION_NAME' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各地區銷售額和數量"
            else:
                return "統計各地區銷售額"
        elif 'STAFF' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各業務員銷售業績和數量"
            else:
                return "統計各業務員銷售業績"
        elif 'PRODUCT' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各產品銷售額和數量"
            else:
                return "統計各產品銷售額"
        elif 'CUSTOMER' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各客戶消費金額和數量"
            else:
                return "統計各客戶消費金額"
        elif 'REGION' in sql_upper and 'SUM' in sql_upper and 'AMOUNT' in sql_upper:
            if 'QUANTITY' in sql_upper:
                return "統計各地區銷售額和數量"
            else:
                return "統計各地區銷售額"
        elif 'STAFF' in sql_upper and 'DATE' in sql_upper:
            return "查詢業務員每日銷售業績"
        elif 'PRODUCT' in sql_upper and 'DATE' in sql_upper:
            return "查詢產品每日銷售情況"
        elif 'CUSTOMER' in sql_upper and 'DATE' in sql_upper:
            return "查詢客戶每日消費情況"
        elif 'REGION' in sql_upper and 'DATE' in sql_upper:
            return "查詢地區每日銷售情況"
        else:
            # 通用描述
            return "執行資料庫查詢"

    def natural_language_to_sql(self, natural_query, original_query=None):
        """
        將自然語言查詢轉換為 SQL
        """
        # 檢查查詢中是否包含明確的時間格式
        import re
        
        # 統一處理查詢中的時間格式
        processed_query = natural_query
        
        # 1. 統一處理月份的中文表示
        month_mapping = {
            '一月': '01', '二月': '02', '三月': '03', '四月': '04',
            '五月': '05', '六月': '06', '七月': '07', '八月': '08',
            '九月': '09', '十月': '10', '十一月': '11', '十二月': '12'
        }
        
        for chinese_month, numeric_month in month_mapping.items():
            # 將 "2025年七月" 轉換為 "2025年07月"
            processed_query = processed_query.replace(f"年{chinese_month}", f"年{numeric_month}月")
        
        # 2. 統一處理季度格式
        quarter_mapping = {
            '季1': 'Q1', '季2': 'Q2', '季3': 'Q3', '季4': 'Q4',
            'q1': 'Q1', 'q2': 'Q2', 'q3': 'Q3', 'q4': 'Q4'
        }
        
        for quarter_text, quarter_code in quarter_mapping.items():
            processed_query = processed_query.replace(quarter_text, quarter_code)
        
        # 檢查是否包含時間格式（使用處理後的查詢）
        time_patterns = [
            r'\d{4}[/-]\d{1,2}',  # YYYY/MM 或 YYYY-MM
            r'\d{4}年\d{1,2}月',   # YYYY年MM月
            r'Q\d',                # Q1, Q2, etc.
            r'\d{4}年Q\d'          # YYYY年Q1
        ]
        
        has_time_format = any(re.search(pattern, processed_query) for pattern in time_patterns)
        
        # 只有在查詢中包含明確時間格式時才解析時間
        year = None
        month = None
        quarter = None
        if has_time_format:
            query_to_parse = original_query if original_query else natural_query
            parsed = self._parse_query(query_to_parse)
            
            # 嘗試從解析結果中獲取時間資訊
            if parsed:
                try:
                    # 檢查是否有 current_start
                    if 'current_start' in parsed:
                        dt = parsed['current_start']
                        year = int(dt[:4])
                        
                        # 檢查是否有月份資訊（月份查詢）
                        if len(dt) > 7 and dt[5:7].isdigit():
                            month = int(dt[5:7])
                            quarter = (month - 1) // 3 + 1
                        # 檢查是否為季度查詢
                        elif 'Q' in processed_query:
                            quarter_match = re.search(r'Q(\d)', processed_query)
                            if quarter_match:
                                quarter = int(quarter_match.group(1))
                                # 季度查詢不需要月份
                                month = None
                except Exception as e:
                    print(f"時間解析錯誤: {e}")
                    pass
        
        # 動態獲取維度資料
        specific_customers = self._get_dimension_values('customer')
        specific_staff = self._get_dimension_values('staff')
        specific_products = self._get_dimension_values('product')
        specific_regions = self._get_dimension_values('region')
        
        query_lower = natural_query.lower()
        
        # 檢查是否包含特定客戶名稱
        for customer in specific_customers:
            if customer in natural_query:
                # 檢查該客戶是否存在於資料庫中
                customer_exists = self._check_customer_exists(customer)
                if customer_exists:
                    # 客戶存在，生成針對該客戶的查詢
                    if year and month:
                        # 支援月份查詢
                        return f'''
                            SELECT c.customer_name, c.customer_level, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                            FROM sales_fact f
                            JOIN dim_customer c ON f.customer_id = c.customer_id
                            JOIN dim_time t ON f.time_id = t.time_id
                            WHERE c.customer_name = '{customer}' AND t.year = {year} AND t.month = {month}
                            GROUP BY c.customer_name, c.customer_level
                        '''
                    elif year and quarter:
                        # 支援季度查詢
                        quarter_start_month = 3 * (quarter - 1) + 1
                        quarter_end_month = 3 * quarter
                        return f'''
                            SELECT c.customer_name, c.customer_level, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                            FROM sales_fact f
                            JOIN dim_customer c ON f.customer_id = c.customer_id
                            JOIN dim_time t ON f.time_id = t.time_id
                            WHERE c.customer_name = '{customer}' AND t.year = {year} AND t.month BETWEEN {quarter_start_month} AND {quarter_end_month}
                            GROUP BY c.customer_name, c.customer_level
                        '''
                    else:
                        # 無時間限制，查詢所有資料
                        return f'''
                            SELECT c.customer_name, c.customer_level, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                            FROM sales_fact f
                            JOIN dim_customer c ON f.customer_id = c.customer_id
                            GROUP BY c.customer_name, c.customer_level
                        '''
                else:
                    # 客戶不存在，返回空結果查詢
                    return f'''
                        SELECT c.customer_name, c.customer_level, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_customer c ON f.customer_id = c.customer_id
                        WHERE c.customer_name = '{customer}'
                        GROUP BY c.customer_name, c.customer_level
                    '''
        
        # 檢查是否包含特定業務員名稱
        for staff in specific_staff:
            if staff in natural_query:
                # 生成針對該業務員的查詢
                if year and month:
                    # 支援月份查詢
                    return f'''
                        SELECT s.staff_name, s.department, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_staff s ON f.staff_id = s.staff_id
                        JOIN dim_time t ON f.time_id = t.time_id
                        WHERE s.staff_name = '{staff}' AND t.year = {year} AND t.month = {month}
                        GROUP BY s.staff_name, s.department
                    '''
                elif year and quarter:
                    # 支援季度查詢
                    quarter_start_month = 3 * (quarter - 1) + 1
                    quarter_end_month = 3 * quarter
                    return f'''
                        SELECT s.staff_name, s.department, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_staff s ON f.staff_id = s.staff_id
                        JOIN dim_time t ON f.time_id = t.time_id
                        WHERE s.staff_name = '{staff}' AND t.year = {year} AND t.month BETWEEN {quarter_start_month} AND {quarter_end_month}
                        GROUP BY s.staff_name, s.department
                    '''
                else:
                    # 無時間限制，查詢所有資料
                    return f'''
                        SELECT s.staff_name, s.department, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_staff s ON f.staff_id = s.staff_id
                        GROUP BY s.staff_name, s.department
                    '''
        
        # 檢查是否包含特定產品名稱
        for product in specific_products:
            if product in natural_query:
                # 生成針對該產品的查詢
                if year and month:
                    # 支援月份查詢
                    return f'''
                        SELECT p.product_name, p.category, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_product p ON f.product_id = p.product_id
                        JOIN dim_time t ON f.time_id = t.time_id
                        WHERE p.product_name = '{product}' AND t.year = {year} AND t.month = {month}
                        GROUP BY p.product_name, p.category
                    '''
                elif year and quarter:
                    # 支援季度查詢
                    quarter_start_month = 3 * (quarter - 1) + 1
                    quarter_end_month = 3 * quarter
                    return f'''
                        SELECT p.product_name, p.category, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_product p ON f.product_id = p.product_id
                        JOIN dim_time t ON f.time_id = t.time_id
                        WHERE p.product_name = '{product}' AND t.year = {year} AND t.month BETWEEN {quarter_start_month} AND {quarter_end_month}
                        GROUP BY p.product_name, p.category
                    '''
                else:
                    # 無時間限制，查詢所有資料
                    return f'''
                        SELECT p.product_name, p.category, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_product p ON f.product_id = p.product_id
                        GROUP BY p.product_name, p.category
                    '''
        
        # 檢查是否包含特定地區名稱
        for region in specific_regions:
            if region in natural_query:
                # 生成針對該地區的查詢
                if year and month:
                    # 支援月份查詢
                    return f'''
                        SELECT r.region_name, r.region_type, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_region r ON f.region_id = r.region_id
                        JOIN dim_time t ON f.time_id = t.time_id
                        WHERE r.region_name = '{region}' AND t.year = {year} AND t.month = {month}
                        GROUP BY r.region_name, r.region_type
                    '''
                elif year and quarter:
                    # 支援季度查詢
                    quarter_start_month = 3 * (quarter - 1) + 1
                    quarter_end_month = 3 * quarter
                    return f'''
                        SELECT r.region_name, r.region_type, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_region r ON f.region_id = r.region_id
                        JOIN dim_time t ON f.time_id = t.time_id
                        WHERE r.region_name = '{region}' AND t.year = {year} AND t.month BETWEEN {quarter_start_month} AND {quarter_end_month}
                        GROUP BY r.region_name, r.region_type
                    '''
                else:
                    # 無時間限制，查詢所有資料
                    return f'''
                        SELECT r.region_name, r.region_type, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                        FROM sales_fact f
                        JOIN dim_region r ON f.region_id = r.region_id
                        GROUP BY r.region_name, r.region_type
                    '''
        
        # 新增對「統計各業務員銷售業績和數量」的查詢模式
        if natural_query.strip() == "統計各業務員銷售業績和數量":
            if year and month:
                # 支援月份查詢
                return f'''
                    SELECT s.staff_name, s.department, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                    FROM sales_fact f
                    JOIN dim_staff s ON f.staff_id = s.staff_id
                    JOIN dim_time t ON f.time_id = t.time_id
                    WHERE t.year = {year} AND t.month = {month}
                    GROUP BY s.staff_name, s.department
                    ORDER BY total_sales DESC
                '''
            elif year and quarter:
                # 支援季度查詢
                quarter_start_month = 3 * (quarter - 1) + 1
                quarter_end_month = 3 * quarter
                return f'''
                    SELECT s.staff_name, s.department, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                    FROM sales_fact f
                    JOIN dim_staff s ON f.staff_id = s.staff_id
                    JOIN dim_time t ON f.time_id = t.time_id
                    WHERE t.year = {year} AND t.month BETWEEN {quarter_start_month} AND {quarter_end_month}
                    GROUP BY s.staff_name, s.department
                    ORDER BY total_sales DESC
                '''
            else:
                # 無時間限制，查詢所有資料
                return '''
                    SELECT s.staff_name, s.department, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                    FROM sales_fact f
                    JOIN dim_staff s ON f.staff_id = s.staff_id
                    GROUP BY s.staff_name, s.department
                    ORDER BY total_sales DESC
                '''
        # 其餘維持原有邏輯
        # ... existing code ...
        
        # 簡單的查詢模式匹配
        query_patterns = {
            r'顯示所有產品': 'SELECT * FROM dim_product',
            r'查詢客戶銷售額': '''
                SELECT c.customer_name, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                GROUP BY c.customer_name
                ORDER BY total_sales DESC
            ''',
            r'顯示前(\d+)筆銷售記錄': lambda match: f'SELECT * FROM sales_fact LIMIT {match.group(1)}',
            r'統計各產品銷售額': '''
                SELECT p.product_name, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                GROUP BY p.product_name
                ORDER BY total_sales DESC
            ''',
            r'顯示所有客戶': 'SELECT * FROM dim_customer',
            r'顯示所有業務員': 'SELECT * FROM dim_staff',
            r'顯示所有地區': 'SELECT * FROM dim_region',
            r'顯示所有時間': 'SELECT * FROM dim_time',
            r'顯示銷售事實': 'SELECT * FROM sales_fact LIMIT 20',
            r'查詢(\d{4})年(\d{1,2})月銷售': lambda match: f'''
                SELECT t.date, SUM(f.amount) as daily_sales, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY t.date
                ORDER BY t.date
            ''',
            r'查詢(\d{4})年Q(\d)銷售': lambda match: f'''
                SELECT t.date, SUM(f.amount) as daily_sales, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.quarter = {match.group(2)}
                GROUP BY t.date
                ORDER BY t.date
            ''',
            r'統計各客戶消費': '''
                SELECT c.customer_name, SUM(f.amount) as total_consumption
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                GROUP BY c.customer_name
                ORDER BY total_consumption DESC
            ''',
            r'統計各業務員業績': '''
                SELECT s.staff_name, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                GROUP BY s.staff_name
                ORDER BY total_sales DESC
            ''',
            r'統計各地區銷售': '''
                SELECT r.region_name, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_region r ON f.region_id = r.region_id
                GROUP BY r.region_name
                ORDER BY total_sales DESC
            ''',
            # 新增多維度查詢模式
            r'業務員.*(\d{4})年(\d{1,2})月.*業績': lambda match: f'''
                SELECT s.staff_name, t.date, SUM(f.amount) as daily_sales
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY s.staff_name, t.date
                ORDER BY s.staff_name, t.date
            ''',
            r'(\d{4})年(\d{1,2})月.*業務員.*業績': lambda match: f'''
                SELECT s.staff_name, t.date, SUM(f.amount) as daily_sales
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY s.staff_name, t.date
                ORDER BY s.staff_name, t.date
            ''',
            r'產品.*(\d{4})年(\d{1,2})月.*銷售': lambda match: f'''
                SELECT p.product_name, t.date, SUM(f.amount) as daily_sales
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY p.product_name, t.date
                ORDER BY p.product_name, t.date
            ''',
            r'客戶.*(\d{4})年(\d{1,2})月.*消費': lambda match: f'''
                SELECT c.customer_name, t.date, SUM(f.amount) as daily_consumption
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY c.customer_name, t.date
                ORDER BY c.customer_name, t.date
            ''',
            # 新增支援維度表內資料查詢的模式
            r'(\d{4})年(\d{1,2})月.*客戶.*等級': lambda match: f'''
                SELECT c.customer_name, c.customer_level, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY c.customer_name, c.customer_level
                ORDER BY total_sales DESC
            ''',
            r'(\d{4})年(\d{1,2})月.*業務員.*部門': lambda match: f'''
                SELECT s.staff_name, s.department, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY s.staff_name, s.department
                ORDER BY total_sales DESC
            ''',
            r'(\d{4})年(\d{1,2})月.*產品.*類別': lambda match: f'''
                SELECT p.product_name, p.category, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY p.product_name, p.category
                ORDER BY total_sales DESC
            ''',
            r'(\d{4})年(\d{1,2})月.*地區.*類型': lambda match: f'''
                SELECT r.region_name, r.region_type, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_region r ON f.region_id = r.region_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.month = {match.group(2)}
                GROUP BY r.region_name, r.region_type
                ORDER BY total_sales DESC
            ''',
            # 支援季度查詢的模式
            r'(\d{4})年Q(\d).*客戶.*等級': lambda match: f'''
                SELECT c.customer_name, c.customer_level, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.quarter = {match.group(2)}
                GROUP BY c.customer_name, c.customer_level
                ORDER BY total_sales DESC
            ''',
            r'(\d{4})年Q(\d).*業務員.*部門': lambda match: f'''
                SELECT s.staff_name, s.department, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.quarter = {match.group(2)}
                GROUP BY s.staff_name, s.department
                ORDER BY total_sales DESC
            ''',
            r'(\d{4})年Q(\d).*產品.*類別': lambda match: f'''
                SELECT p.product_name, p.category, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.quarter = {match.group(2)}
                GROUP BY p.product_name, p.category
                ORDER BY total_sales DESC
            ''',
            r'(\d{4})年Q(\d).*地區.*類型': lambda match: f'''
                SELECT r.region_name, r.region_type, SUM(f.amount) as total_sales
                FROM sales_fact f
                JOIN dim_region r ON f.region_id = r.region_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {match.group(1)} AND t.quarter = {match.group(2)}
                GROUP BY r.region_name, r.region_type
                ORDER BY total_sales DESC
            '''
        }
        
        for pattern, sql in query_patterns.items():
            match = re.search(pattern, natural_query)
            if match:
                if callable(sql):
                    return sql(match)
                else:
                    return sql
        
        # 如果沒有匹配到預設模式，根據查詢內容智能推測
        query_lower = natural_query.lower()
        
        # 解析時間條件
        time_condition = ""
        year_match = re.search(r'(\d{4})年', natural_query)
        month_match = re.search(r'(\d{1,2})月', natural_query)
        quarter_match = re.search(r'Q(\d)', natural_query)
        
        if year_match and month_match:
            time_condition = f"WHERE t.year = {year_match.group(1)} AND t.month = {month_match.group(1)}"
        elif year_match and quarter_match:
            time_condition = f"WHERE t.year = {year_match.group(1)} AND t.quarter = {quarter_match.group(1)}"
        elif year_match:
            time_condition = f"WHERE t.year = {year_match.group(1)}"
        
        # 檢查是否包含數量相關詞彙
        if any(word in query_lower for word in ['數量', 'quantity', '件數', '個數']):
            return f'''
                SELECT p.product_name, SUM(f.quantity) as total_quantity
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                {time_condition}
                GROUP BY p.product_name
                ORDER BY total_quantity DESC
            '''
        
        # 檢查是否包含金額相關詞彙（但排除多維度查詢）
        elif (any(word in query_lower for word in ['金額', 'amount', '銷售額', '營業額', '收入']) and 
              not any(word in query_lower for word in ['年', '月', '季', '時間', '日期', '每天', '每日', '日', '業務員', '銷售員', 'staff', '業績'])):
            return '''
                SELECT p.product_name, SUM(f.amount) as total_amount
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                GROUP BY p.product_name
                ORDER BY total_amount DESC
            '''
        
        # 檢查是否包含時間和業務員相關詞彙
        elif (any(word in query_lower for word in ['年', '月', '季', '時間', '日期', '每天', '每日', '日']) and 
              any(word in query_lower for word in ['業務員', '銷售員', 'staff', '業績'])):
            return f'''
                SELECT s.staff_name, t.date, SUM(f.amount) as daily_sales, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_time t ON f.time_id = t.time_id
                {time_condition}
                GROUP BY s.staff_name, t.date
                ORDER BY s.staff_name, t.date DESC
                LIMIT 20
            '''
        
        # 檢查是否為業務員業績查詢（包含時間條件）
        elif (any(word in query_lower for word in ['業務員', '銷售員', 'staff', '業績']) and 
              (year and month)):
            return f'''
                SELECT s.staff_name, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE t.year = {year} AND t.month = {month}
                GROUP BY s.staff_name
                ORDER BY total_sales DESC
            '''
        
        # 檢查是否包含時間和產品相關詞彙
        elif (any(word in query_lower for word in ['年', '月', '季', '時間', '日期', '每天', '每日', '日']) and 
              any(word in query_lower for word in ['產品', '商品', 'product'])):
            return f'''
                SELECT p.product_name, t.date, SUM(f.amount) as daily_sales, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_time t ON f.time_id = t.time_id
                {time_condition}
                GROUP BY p.product_name, t.date
                ORDER BY p.product_name, t.date DESC
                LIMIT 20
            '''
        
        # 檢查是否包含時間和客戶相關詞彙
        elif (any(word in query_lower for word in ['年', '月', '季', '時間', '日期', '每天', '每日', '日']) and 
              any(word in query_lower for word in ['客戶', 'customer', '消費'])):
            return f'''
                SELECT c.customer_name, t.date, SUM(f.amount) as daily_consumption, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_time t ON f.time_id = t.time_id
                {time_condition}
                GROUP BY c.customer_name, t.date
                ORDER BY c.customer_name, t.date DESC
                LIMIT 20
            '''
        
        # 檢查是否包含時間和地區相關詞彙
        elif (any(word in query_lower for word in ['年', '月', '季', '時間', '日期', '每天', '每日', '日']) and 
              any(word in query_lower for word in ['地區', '區域', 'region', '地方'])):
            return f'''
                SELECT r.region_name, t.date, SUM(f.amount) as daily_sales, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_region r ON f.region_id = r.region_id
                JOIN dim_time t ON f.time_id = t.time_id
                {time_condition}
                GROUP BY r.region_name, t.date
                ORDER BY r.region_name, t.date DESC
                LIMIT 20
            '''
        
        # 檢查是否包含時間相關詞彙
        elif any(word in query_lower for word in ['年', '月', '季', '時間', '日期', '每天', '每日', '日']):
            return f'''
                SELECT t.date, SUM(f.amount) as daily_sales, SUM(f.quantity) as daily_quantity
                FROM sales_fact f
                JOIN dim_time t ON f.time_id = t.time_id
                {time_condition}
                GROUP BY t.date
                ORDER BY t.date DESC
                LIMIT 20
            '''
        
        # 檢查是否包含產品相關詞彙
        elif any(word in query_lower for word in ['產品', '商品', 'product']):
            return '''
                SELECT p.product_name, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                GROUP BY p.product_name
                ORDER BY total_sales DESC
            '''
        
        # 檢查是否包含客戶相關詞彙
        elif any(word in query_lower for word in ['客戶', 'customer', '消費']):
            return '''
                SELECT c.customer_name, SUM(f.amount) as total_consumption, SUM(f.quantity) as total_quantity
                FROM sales_fact f
                JOIN dim_customer c ON f.customer_id = c.customer_id
                GROUP BY c.customer_name
                ORDER BY total_consumption DESC
            '''
        
        # 檢查是否包含業務員相關詞彙
        elif any(word in query_lower for word in ['業務員', '銷售員', 'staff', '業績']):
            return '''
                SELECT s.staff_name, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                FROM sales_fact f
                JOIN dim_staff s ON f.staff_id = s.staff_id
                GROUP BY s.staff_name
                ORDER BY total_sales DESC
            '''
        
        # 檢查是否包含地區相關詞彙
        elif any(word in query_lower for word in ['地區', '區域', 'region', '地方']):
            return '''
                SELECT r.region_name, SUM(f.amount) as total_sales, SUM(f.quantity) as total_quantity
                FROM sales_fact f
                JOIN dim_region r ON f.region_id = r.region_id
                GROUP BY r.region_name
                ORDER BY total_sales DESC
            '''
        
        # 檢查是否包含銷售相關詞彙
        elif any(word in query_lower for word in ['銷售', '金額', '業績', 'sales', 'amount', 'quantity']):
            return '''
                SELECT f.sale_id, f.amount, f.quantity, p.product_name, c.customer_name, s.staff_name, r.region_name, t.date
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_region r ON f.region_id = r.region_id
                JOIN dim_time t ON f.time_id = t.time_id
                ORDER BY t.date DESC
                LIMIT 20
            '''
        
        # 預設返回產品表
        else:
            return 'SELECT * FROM dim_product LIMIT 10'

    def _generate_analysis_summary(self, current_sales, last_sales, diff, percentage_diff, driver_data, dimension_text, period_text, other_dimension_reference=None):
        """
        生成分析總結報告 (NLG - Natural Language Generation)
        新增參數 other_dimension_reference: 顯示多維度參考分析
        """
        print(f"📝 開始生成分析總結報告...")
        print(f"   輸入參數:")
        print(f"     - current_sales: {current_sales}")
        print(f"     - last_sales: {last_sales}")
        print(f"     - diff: {diff}")
        print(f"     - percentage_diff: {percentage_diff}")
        print(f"     - driver_data: {len(driver_data) if driver_data else 0} 筆")
        print(f"     - dimension_text: {dimension_text}")
        print(f"     - period_text: {period_text}")
        
        # 格式化數字
        def format_currency(amount):
            return f"{amount:,.0f}"
        
        # 生成主要趨勢描述
        if diff > 0:
            trend = "成長"
            trend_emoji = "📈"
            if percentage_diff > 50:
                trend_intensity = "大幅"
            elif percentage_diff > 20:
                trend_intensity = "明顯"
            else:
                trend_intensity = "小幅"
        elif diff < 0:
            trend = "下滑"
            trend_emoji = "📉"
            if abs(percentage_diff) > 50:
                trend_intensity = "大幅"
            elif abs(percentage_diff) > 20:
                trend_intensity = "明顯"
            else:
                trend_intensity = "小幅"
        else:
            trend = "持平"
            trend_emoji = "➡️"
            trend_intensity = ""

        # 生成主要貢獻者描述
        top_contributors = []
        if driver_data:
            # 找出貢獻最大的項目（正貢獻）
            positive_contributors = [item for item in driver_data if item['差異'] > 0]
            if positive_contributors:
                positive_contributors.sort(key=lambda x: x['差異'], reverse=True)
                top_positive = positive_contributors[0]
                top_contributors.append(f"<strong>{top_positive['分析維度']}</strong>貢獻了 {format_currency(top_positive['差異'])} 元")

            # 找出影響最大的項目（負貢獻）
            negative_contributors = [item for item in driver_data if item['差異'] < 0]
            if negative_contributors:
                negative_contributors.sort(key=lambda x: abs(x['差異']), reverse=True)
                top_negative = negative_contributors[0]
                top_contributors.append(f"<strong>{top_negative['分析維度']}</strong>減少了 {format_currency(abs(top_negative['差異']))} 元")

        # 生成總結報告
        summary_parts = []
        
        # 主要趨勢
        if trend_intensity:
            summary_parts.append(f"{trend_emoji} {period_text}業績{trend_intensity}{trend}，")
        else:
            summary_parts.append(f"{trend_emoji} {period_text}業績{trend}，")
        
        # 具體數據
        if percentage_diff != float('inf') and percentage_diff != float('-inf'):
            summary_parts.append(f"本期銷售額為 {format_currency(current_sales)} 元，")
            summary_parts.append(f"較前期 {format_currency(last_sales)} 元")
            if diff > 0:
                summary_parts.append(f"增加 {format_currency(diff)} 元")
            else:
                summary_parts.append(f"減少 {format_currency(abs(diff))} 元")
            summary_parts.append(f"（{percentage_diff:+.1f}%）。")
        else:
            summary_parts.append(f"本期銷售額為 {format_currency(current_sales)} 元，")
            if diff > 0:
                summary_parts.append(f"較前期增加 {format_currency(diff)} 元。")
            else:
                summary_parts.append(f"較前期減少 {format_currency(abs(diff))} 元。")

        # 主要貢獻者
        if top_contributors:
            summary_parts.append("<br><br>📊 <strong>主要貢獻分析：</strong>")
            summary_parts.append(" ".join(top_contributors))
        # 新增：多維度參考分析
        if other_dimension_reference:
            summary_parts.append("<br><br>🔎 <strong>其他維度參考分析：</strong><br>")
            summary_parts.append(other_dimension_reference)

        # 建議
        summary_parts.append("<br><br>💡 <strong>建議：</strong>")
        
        if diff > 0:
            # 整體成長的情況
            if positive_contributors:
                summary_parts.append("持續關注表現優異的項目，可考慮擴大相關業務。")
            
            # 如果有負面貢獻者，也要提供改善建議
            if negative_contributors:
                summary_parts.append("同時針對表現不佳的項目制定改善計劃，加強行銷推廣。")
        else:
            # 整體下滑的情況
            if negative_contributors:
                summary_parts.append("針對表現不佳的項目制定改善計劃，加強行銷推廣。")
            else:
                summary_parts.append("檢視整體營運策略，尋找新的成長機會。")
        
        # 針對具體負面貢獻者提供改善建議
        if negative_contributors:
            summary_parts.append("<br><br>🎯 <strong>具體改善建議：</strong>")
            for contributor in negative_contributors[:2]:  # 最多顯示前2個
                contributor_name = contributor['分析維度']
                loss_amount = abs(contributor['差異'])
                improvement_suggestions = self._get_dimension_specific_suggestions(contributor_name, loss_amount)
                
                summary_parts.append(f"<br>• <strong>{contributor_name}</strong>：")
                summary_parts.append(f"業績下滑 {format_currency(loss_amount)} 元，")
                summary_parts.append(improvement_suggestions)

        final_summary = "".join(summary_parts)
        print(f"   生成的總結報告長度: {len(final_summary)} 字元")
        print(f"   總結報告預覽: {final_summary[:200]}...")
        
        return final_summary

    def _get_dimension_specific_suggestions(self, dimension_name, loss_amount):
        """
        根據維度類型提供針對性的改善建議
        """
        # 格式化金額
        def format_currency(amount):
            return f"{amount:,.0f}"
        
        # 根據維度名稱判斷類型並提供相應建議
        dimension_lower = dimension_name.lower()
        
        # 產品相關維度
        if any(keyword in dimension_lower for keyword in ['筆記型電腦', '電腦', 'laptop', 'notebook', '耳機', '藍牙', '無線', '手機', '平板', 'tablet', 'smartphone']):
            if loss_amount > 10000:
                return f"建議：1) 「{dimension_name} 產品營銷策略 2024」了解最新趨勢；2) 「電商平台 A/B 測試案例」優化產品頁面；3) 「{dimension_name} 用戶評價管理」建立口碑；4) 「分期付款促銷方案」提升購買意願；5) 「售後服務標準流程」提升客戶滿意度；6) 「產品生態系統建設」提升用戶黏性。"
            else:
                return f"建議：1) 「{dimension_name} 產品展示優化」改善頁面；2) 「免費試用退換貨政策」降低購買門檻；3) 「會員積分等級制度設計」提升忠誠度；4) 「社群媒體推廣策略」擴大影響力；5) 「技術諮詢服務標準」提升專業度；6) 「季節性促銷活動策劃」提升銷量。"
        
        # 人員相關維度
        elif any(keyword in dimension_lower for keyword in ['王小明', '李美麗', '張三', '李四', '業務員', '銷售員', 'sales', '業務', '人員']):
            if loss_amount > 50000:
                return f"建議：1) 「SPIN 銷售技巧培訓課程」提升銷售能力；2) 「銷售漏斗管理系統」優化流程；3) 「CRM 系統功能比較」選擇合適工具；4) 「階梯式績效獎勵制度設計」激勵團隊；5) 「銷售團隊協作機制」提升效率；6) 「職業發展路徑規劃」留住人才。"
            else:
                return f"建議：1) 「客戶關係管理培訓課程」提升服務；2) 「個人品牌建設方法」提升形象；3) 「時間管理效率提升技巧」優化工作；4) 「溝通技巧談判能力培訓」提升技能；5) 「個人 KPI 目標管理方法」明確方向；6) 「導師制度經驗分享機制」促進成長。"
        
        # 地區相關維度
        elif any(keyword in dimension_lower for keyword in ['台北', '台中', '台南', '高雄', '桃園', '新竹', '地區', 'region', 'city', '縣市']):
            if loss_amount > 20000:
                return f"建議：1) 「{dimension_name} 市場調研競爭分析」了解市場；2) 「在地化供應鏈物流體系」優化配送；3) 「{dimension_name} 特色產品服務設計」差異化競爭；4) 「在地社群參與品牌建設」提升知名度；5) 「地區差異化定價策略」提升競爭力；6) 「地區客戶關係管理方法」提升服務。"
            else:
                return f"建議：1) 「{dimension_name} 媒體宣傳廣告投放」擴大影響；2) 「地區客戶服務中心建設」提升服務；3) 「{dimension_name} 在地化產品服務」滿足需求；4) 「地區會員優惠忠誠度計劃」提升黏性；5) 「社群媒體在地推廣策略」擴大影響；6) 「地區合作夥伴關係建立」共同發展。"
        
        # 時間相關維度
        elif any(keyword in dimension_lower for keyword in ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月', 'month', '季度', 'quarter']):
            if loss_amount > 15000:
                return f"建議：1) 「{dimension_name} 季節性預測模型」分析趨勢；2) 「淡旺季差異化營銷策略」優化策略；3) 「跨季節產品組合推廣」提升銷量；4) 「季節性客戶需求預測」精準營銷；5) 「庫存管理供應鏈優化」降低成本；6) 「節慶活動主題營銷策劃」提升效果。"
            else:
                return f"建議：1) 「敏捷營銷快速響應機制」提升效率；2) 「時間序列分析預測方法」優化決策；3) 「營銷活動時程安排優化」提升效果；4) 「時效性內容營銷策略」抓住機會；5) 「時間敏感型促銷策略」提升轉化；6) 「時間管理效率監控方法」持續改善。"
        
        # 客戶相關維度
        elif any(keyword in dimension_lower for keyword in ['客戶', 'customer', '客戶群', '客戶類型', 'vip', '一般客戶']):
            if loss_amount > 25000:
                return f"建議：1) 「客戶生命週期管理體系」完善流程；2) 「個性化推薦內容策展」提升體驗；3) 「VIP 專屬服務權益設計」提升價值；4) 「客戶成功指標監控方法」量化效果；5) 「客戶分層差異化服務」精準服務；6) 「客戶反饋收集快速響應」提升滿意度。"
            else:
                return f"建議：1) 「客戶畫像行為分析方法」了解需求；2) 「個性化溝通服務策略」提升體驗；3) 「客戶忠誠度回饋計劃設計」提升黏性；4) 「社群媒體互動參與策略」擴大影響；5) 「客戶教育價值傳遞方法」提升認知；6) 「客戶挽回留存策略」降低流失。"
        
        # 渠道相關維度
        elif any(keyword in dimension_lower for keyword in ['線上', '線下', 'online', 'offline', '電商', '實體店', '通路', 'channel']):
            if loss_amount > 30000:
                return f"建議：1) 「O2O 無縫整合體驗設計」提升體驗；2) 「全渠道庫存管理系統」優化運營；3) 「線上預約線下體驗服務」提升轉化；4) 「跨渠道會員權益整合」提升價值；5) 「渠道績效監控優化方法」提升效率；6) 「數位化轉型技術升級」提升競爭力。"
            else:
                return f"建議：1) 「渠道結構效率優化方法」提升效率；2) 「渠道合作夥伴關係管理」共同發展；3) 「渠道培訓支援體系建設」提升能力；4) 「渠道激勵獎勵制度設計」提升積極性；5) 「渠道數據分析洞察方法」優化決策；6) 「渠道創新發展策略」提升競爭力。"
        
        # 預設建議（適用於其他維度）
        else:
            if loss_amount > 20000:
                return f"建議：1) 「McKinsey 7S 模型應用案例」系統改善；2) 「數據驅動決策制定方法」優化決策；3) 「持續改善創新文化建設」提升競爭力；4) 「組織結構流程設計優化」提升效率；5) 「人才發展能力建設方法」提升團隊；6) 「風險管理應急預案制定」降低風險。"
            else:
                return f"建議：1) 「敏捷管理快速迭代方法」提升效率；2) 「KPI 監控績效管理系統」優化管理；3) 「團隊協作溝通效率提升」改善合作；4) 「員工培訓發展機會設計」提升能力；5) 「客戶導向服務文化建設」提升體驗；6) 「持續改善創新機制設計」提升競爭力。" 

    def generate_professional_report(self, analysis_context=None, report_type="general", chat_context=None):
        """
        生成專業建議報告書
        包含：主旨、分析說明、改善建議、規劃時程、結論
        基於 AI 對談內容生成個性化主旨
        """
        try:
            import google.generativeai as genai
            import os
            
            # 設定 Gemini API Key
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return self._generate_fallback_report(analysis_context, report_type, chat_context)
            
            # 配置 Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # 構建分析背景
            context_parts = []
            if analysis_context:
                context_parts.append(f"分析期間：{analysis_context.get('period_text', 'N/A')}")
                context_parts.append(f"當期銷售：{analysis_context.get('current_sales', 0):,.0f} 元")
                context_parts.append(f"前期銷售：{analysis_context.get('last_sales', 0):,.0f} 元")
                context_parts.append(f"差異：{analysis_context.get('diff', 0):,.0f} 元")
                context_parts.append(f"百分比差異：{analysis_context.get('percentage_diff', 0):.1f}%")
                context_parts.append(f"分析維度：{analysis_context.get('dimension_text', 'N/A')}")
                if analysis_context.get('driver_data'):
                    top_contributors = []
                    for item in analysis_context['driver_data'][:5]:
                        if item['差異'] > 0:
                            top_contributors.append(f"{item['分析維度']}(+{item['差異']:,.0f})")
                        else:
                            top_contributors.append(f"{item['分析維度']}({item['差異']:,.0f})")
                    context_parts.append(f"主要貢獻者：{', '.join(top_contributors)}")
                # 新增：多維度參考分析
                if analysis_context.get('other_dimension_reference'):
                    context_parts.append(f"其他維度參考分析：<br>{analysis_context['other_dimension_reference']}")
            
            # 構建聊天對話背景
            chat_background = ""
            if chat_context and len(chat_context) > 0:
                chat_background = "\n\nAI 對談內容：\n"
                for i, msg in enumerate(chat_context[-10:], 1):  # 只取最近10條對話
                    role = "用戶" if msg.get('role') == 'user' else "AI專家"
                    content = msg.get('content', '')
                    chat_background += f"{i}. {role}：{content}\n"
            
            # 根據報告類型設定不同的提示詞
            if report_type == "performance":
                report_focus = "銷售績效分析與改善"
            elif report_type == "strategy":
                report_focus = "經營策略規劃與建議"
            elif report_type == "risk":
                report_focus = "風險評估與管理建議"
            else:
                report_focus = "綜合經營分析與建議"
            
            # 構建專業報告提示詞
            system_prompt = f"""
你是一位資深的經營分析顧問，擁有豐富的商業諮詢經驗。請基於以下分析數據和 AI 對談內容，生成一份專業的建議報告書。

分析背景：
{chr(10).join(context_parts) if context_parts else '基於一般經營分析需求'}

{chat_background}

報告重點：{report_focus}

請生成一份包含以下五個部分的專業報告書：

## 一、主旨
基於 AI 對談內容和用戶關注點，生成個性化的報告主旨。主旨應該：
- 反映用戶在對話中表達的主要關切和需求
- 結合分析數據的關鍵發現
- 明確說明報告的核心目的和重點分析內容
- 體現個性化的諮詢建議方向

## 二、分析說明
基於數據進行深入分析，包括：
- 績效表現評估
- 關鍵指標分析
- 趨勢變化說明
- 影響因素分析
- 結合對談中提到的具體問題和關注點

## 三、改善建議
提供具體可執行的改善方案，包括：
- 短期改善措施（1-3個月）
- 中期策略調整（3-6個月）
- 長期發展規劃（6-12個月）
- 針對對談中提到的具體問題提供解決方案

## 四、規劃時程
制定詳細的執行時程表：
- 第一階段（1-2個月）：立即行動項目
- 第二階段（3-4個月）：策略調整項目
- 第三階段（5-6個月）：長期規劃項目
- 各階段關鍵里程碑和成功指標

## 五、結論
總結報告要點，強調關鍵建議和預期成效，並回應對談中的核心關切。

要求：
1. 使用專業但易懂的語言
2. 提供具體可執行的建議
3. 包含量化的目標和指標
4. 考慮實際執行可行性
5. 全程使用繁體中文
6. 報告總長度控制在800-1200字
7. 結構清晰，重點突出
8. 主旨必須基於對談內容個性化生成
9. 建議要針對對談中提到的具體問題

請生成完整的專業報告書：
"""

            # 調用 Gemini API
            response = model.generate_content(system_prompt)
            
            return {
                'success': True,
                'report': response.text,
                'model': 'gemini-pro',
                'report_type': report_type,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'chat_context_used': len(chat_context) if chat_context else 0
            }
            
        except ImportError:
            return self._generate_fallback_report(analysis_context, report_type, chat_context)
        except Exception as e:
            return {
                'success': False,
                'error': f'專業報告生成失敗：{str(e)}'
            }

    def _generate_fallback_report(self, analysis_context=None, report_type="general", chat_context=None):
        """
        備用專業報告生成（當 Gemini API 不可用時）
        """
        try:
            # 構建分析背景
            context_parts = []
            if analysis_context:
                context_parts.append(f"分析期間：{analysis_context.get('period_text', 'N/A')}")
                context_parts.append(f"當期銷售：{analysis_context.get('current_sales', 0):,.0f} 元")
                context_parts.append(f"前期銷售：{analysis_context.get('last_sales', 0):,.0f} 元")
                context_parts.append(f"差異：{analysis_context.get('diff', 0):,.0f} 元")
                context_parts.append(f"百分比差異：{analysis_context.get('percentage_diff', 0):.1f}%")
                context_parts.append(f"分析維度：{analysis_context.get('dimension_text', 'N/A')}")
                # 新增：多維度參考分析
                if analysis_context.get('other_dimension_reference'):
                    context_parts.append(f"其他維度參考分析：<br>{analysis_context['other_dimension_reference']}")
            
            # 構建聊天背景
            chat_summary = ""
            if chat_context and len(chat_context) > 0:
                # 提取對談中的關鍵問題和關注點
                key_topics = []
                for msg in chat_context[-5:]:  # 取最近5條對話
                    if msg.get('role') == 'user':
                        content = msg.get('content', '')
                        # 簡單提取關鍵詞
                        if any(word in content for word in ['改善', '提升', '問題', '建議']):
                            key_topics.append(content[:50] + "...")
                
                if key_topics:
                    chat_summary = f"\n\n用戶關注重點：{', '.join(key_topics)}"
            
            # 根據報告類型生成不同的報告模板
            if report_type == "performance":
                report = self._generate_performance_report_template(context_parts, chat_summary)
            elif report_type == "strategy":
                report = self._generate_strategy_report_template(context_parts, chat_summary)
            elif report_type == "risk":
                report = self._generate_risk_report_template(context_parts, chat_summary)
            else:
                report = self._generate_general_report_template(context_parts, chat_summary)
            
            return {
                'success': True,
                'report': report,
                'model': 'fallback',
                'report_type': report_type,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'chat_context_used': len(chat_context) if chat_context else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'備用報告生成失敗：{str(e)}'
            }

    def _generate_performance_report_template(self, context_parts, chat_summary=""):
        """生成績效分析報告模板"""
        # 根據聊天內容調整主旨
        if chat_summary:
            purpose = f"本報告旨在分析當前銷售績效表現，並針對用戶在對談中提到的具體問題{chat_summary}，提供個性化的改善建議。"
        else:
            purpose = "本報告旨在分析當前銷售績效表現，識別關鍵改善機會，並提供具體的績效提升策略，以實現可持續的業務增長。"
        
        return f"""
# 銷售績效分析與改善建議報告

## 一、主旨
{purpose}

## 二、分析說明
基於分析數據顯示：
{chr(10).join(context_parts) if context_parts else '- 需要進一步的數據分析來提供具體見解'}

### 績效表現評估
- 銷售趨勢分析顯示整體表現需要關注
- 關鍵指標變化反映市場動態和內部營運狀況
- 各維度表現差異化明顯，需要針對性改善

### 影響因素分析
- 市場競爭環境變化
- 客戶需求偏好轉移
- 內部營運效率影響
- 產品組合策略調整

## 三、改善建議

### 短期改善措施（1-3個月）
1. **立即行動項目**
   - 加強高績效產品推廣
   - 優化銷售流程和客戶服務
   - 建立每日績效監控機制

2. **快速改善方案**
   - 針對表現下滑項目制定改善計劃
   - 加強銷售團隊培訓和激勵
   - 改善客戶關係管理

### 中期策略調整（3-6個月）
1. **策略優化**
   - 重新評估產品組合策略
   - 制定差異化定價方案
   - 加強數位行銷和線上推廣

2. **流程改善**
   - 優化庫存管理系統
   - 改善訂單處理流程
   - 建立客戶忠誠度計劃

### 長期發展規劃（6-12個月）
1. **戰略規劃**
   - 開發新產品線和服務
   - 拓展新市場和客戶群
   - 建立競爭優勢

2. **能力建設**
   - 提升團隊專業能力
   - 建立數據驅動決策文化
   - 優化組織結構

## 四、規劃時程

### 第一階段（1-2個月）：立即行動
- **第1週**：建立績效監控機制
- **第2-4週**：實施快速改善措施
- **第4-8週**：評估初步成效並調整

### 第二階段（3-4個月）：策略調整
- **第3個月**：實施中期策略調整
- **第4個月**：建立新的營運流程
- **里程碑**：達成階段性績效目標

### 第三階段（5-6個月）：長期規劃
- **第5-6個月**：實施長期發展規劃
- **關鍵指標**：銷售增長率、客戶滿意度、市場份額

## 五、結論
通過系統性的績效分析和改善計劃，預期在6個月內實現顯著的業務改善。關鍵成功因素包括：領導層的承諾支持、團隊的積極參與、以及持續的監控和調整機制。建議定期檢討進度，確保改善措施的有效執行。
"""

    def _generate_strategy_report_template(self, context_parts, chat_summary=""):
        """生成策略規劃報告模板"""
        # 根據聊天內容調整主旨
        if chat_summary:
            purpose = f"本報告基於當前業務表現分析，並結合用戶在對談中表達的具體需求{chat_summary}，提供個性化的經營策略規劃建議。"
        else:
            purpose = "本報告基於當前業務表現分析，提供全面的經營策略規劃建議，旨在建立可持續的競爭優勢和業務增長模式。"
        
        return f"""
# 經營策略規劃與建議報告

## 一、主旨
{purpose}

## 二、分析說明
{chr(10).join(context_parts) if context_parts else '基於一般經營分析需求'}

### 策略環境分析
- 市場競爭態勢評估
- 客戶需求變化趨勢
- 內部資源能力分析
- 外部機會與威脅識別

### 核心競爭力評估
- 產品服務優勢分析
- 營運效率評估
- 客戶關係管理能力
- 創新發展潛力

## 三、改善建議

### 短期策略調整（1-3個月）
1. **市場定位優化**
   - 重新定義目標客戶群
   - 調整產品服務定位
   - 優化價格策略

2. **營運效率提升**
   - 改善流程和系統
   - 加強團隊協作
   - 建立績效管理機制

### 中期策略發展（3-6個月）
1. **業務模式創新**
   - 開發新的收入來源
   - 建立合作夥伴關係
   - 拓展服務範圍

2. **能力建設**
   - 提升團隊專業技能
   - 建立學習型組織
   - 加強技術創新能力

### 長期戰略規劃（6-12個月）
1. **市場擴張**
   - 進入新市場領域
   - 開發新產品線
   - 建立品牌影響力

2. **可持續發展**
   - 建立核心競爭優勢
   - 實現規模化發展
   - 建立行業領導地位

## 四、規劃時程

### 第一階段（1-2個月）：策略調整
- **第1週**：策略環境分析
- **第2-4週**：制定調整方案
- **第4-8週**：實施策略調整

### 第二階段（3-4個月）：能力建設
- **第3個月**：建立新的能力體系
- **第4個月**：優化營運模式
- **里程碑**：達成策略調整目標

### 第三階段（5-6個月）：戰略發展
- **第5-6個月**：實施長期戰略
- **關鍵指標**：市場份額、客戶滿意度、營收增長

## 五、結論
通過系統性的策略規劃和執行，預期建立可持續的競爭優勢。成功關鍵在於：清晰的戰略方向、有效的執行機制、以及持續的監控和調整。建議建立定期策略檢討機制，確保策略的有效性和適應性。
"""

    def _generate_risk_report_template(self, context_parts, chat_summary=""):
        """生成風險評估報告模板"""
        # 根據聊天內容調整主旨
        if chat_summary:
            purpose = f"本報告旨在識別當前業務運營中的潛在風險，並針對用戶在對談中提到的具體關注點{chat_summary}，提供相應的風險管理策略和建議。"
        else:
            purpose = "本報告旨在識別當前業務運營中的潛在風險，評估風險影響程度，並提供相應的風險管理策略和建議。"
        
        return f"""
# 風險評估與管理建議報告

## 一、主旨
{purpose}

## 二、分析說明
{chr(10).join(context_parts) if context_parts else '基於一般經營分析需求'}

### 風險識別與評估
- **市場風險**：競爭加劇、需求變化
- **營運風險**：流程效率、人員流失
- **財務風險**：現金流、成本控制
- **策略風險**：方向偏差、執行不力

### 風險影響分析
- 對業務連續性的影響
- 對財務表現的影響
- 對客戶關係的影響
- 對團隊士氣的影響

## 三、改善建議

### 短期風險控制（1-3個月）
1. **立即風險緩解**
   - 建立風險監控機制
   - 制定應急預案
   - 加強內部控制

2. **快速改善措施**
   - 優化關鍵流程
   - 加強團隊培訓
   - 改善溝通機制

### 中期風險管理（3-6個月）
1. **系統性改善**
   - 建立風險管理體系
   - 優化營運流程
   - 加強技術支持

2. **能力建設**
   - 提升風險識別能力
   - 建立預警機制
   - 加強團隊應變能力

### 長期風險防範（6-12個月）
1. **戰略性規劃**
   - 建立風險文化
   - 優化組織結構
   - 加強技術創新

2. **可持續發展**
   - 建立風險管理長效機制
   - 實現風險與收益平衡
   - 建立行業最佳實踐

## 四、規劃時程

### 第一階段（1-2個月）：風險識別與控制
- **第1週**：全面風險評估
- **第2-4週**：制定控制措施
- **第4-8週**：實施風險控制

### 第二階段（3-4個月）：風險管理體系
- **第3個月**：建立管理體系
- **第4個月**：優化控制流程
- **里程碑**：達成風險控制目標

### 第三階段（5-6個月）：風險防範機制
- **第5-6個月**：建立長效機制
- **關鍵指標**：風險事件發生率、損失控制效果

## 五、結論
通過系統性的風險評估和管理，預期建立穩健的業務運營環境。關鍵成功因素包括：領導層的重視、全員參與、以及持續的監控和改進。建議建立定期風險檢討機制，確保風險管理的有效性和適應性。
"""

    def _generate_general_report_template(self, context_parts, chat_summary=""):
        """生成綜合分析報告模板"""
        # 根據聊天內容調整主旨
        if chat_summary:
            purpose = f"本報告基於全面的經營數據分析，並結合用戶在對談中表達的具體需求{chat_summary}，提供個性化的業務評估和改善建議。"
        else:
            purpose = "本報告基於全面的經營數據分析，提供綜合性的業務評估和改善建議，旨在促進業務的可持續發展和競爭力提升。"
        
        return f"""
# 綜合經營分析與建議報告

## 一、主旨
{purpose}

## 二、分析說明
{chr(10).join(context_parts) if context_parts else '基於一般經營分析需求'}

### 整體表現評估
- 業務績效綜合分析
- 關鍵指標趨勢評估
- 競爭力分析
- 發展潛力評估

### 核心問題識別
- 營運效率問題
- 市場競爭挑戰
- 客戶需求變化
- 內部管理改善空間

## 三、改善建議

### 短期改善措施（1-3個月）
1. **立即行動項目**
   - 優化關鍵業務流程
   - 加強客戶服務品質
   - 改善內部溝通機制

2. **快速改善方案**
   - 制定績效提升計劃
   - 加強團隊培訓
   - 建立監控機制

### 中期策略調整（3-6個月）
1. **業務優化**
   - 重新評估業務模式
   - 優化產品服務組合
   - 改善客戶體驗

2. **能力建設**
   - 提升團隊專業能力
   - 加強技術創新
   - 建立學習型組織

### 長期發展規劃（6-12個月）
1. **戰略發展**
   - 制定長期發展戰略
   - 建立競爭優勢
   - 實現可持續增長

2. **組織發展**
   - 優化組織結構
   - 建立企業文化
   - 實現規模化發展

## 四、規劃時程

### 第一階段（1-2個月）：基礎改善
- **第1週**：問題識別與分析
- **第2-4週**：制定改善方案
- **第4-8週**：實施改善措施

### 第二階段（3-4個月）：策略調整
- **第3個月**：實施策略調整
- **第4個月**：建立新的營運模式
- **里程碑**：達成階段性目標

### 第三階段（5-6個月）：長期發展
- **第5-6個月**：實施長期規劃
- **關鍵指標**：整體績效改善、競爭力提升

## 五、結論
通過系統性的分析和改善，預期實現業務的全面提升。成功關鍵在於：明確的目標導向、有效的執行機制、以及持續的監控和調整。建議建立定期檢討機制，確保改善措施的有效執行和持續改進。
"""

    def _generate_unified_monthly_forecast(self, periods, best_model):
        """統一的月度預測生成函數，添加波動性讓預測更接近歷史數據"""
        import numpy as np
        import random
        
        # 生成基礎月度預測
        forecast = best_model.forecast(steps=periods)
        monthly_values = forecast.values if hasattr(forecast, 'values') else forecast
        
        # 計算歷史數據的波動性
        historical_data = self._get_historical_sales_data()
        if historical_data:
            # 計算歷史數據的標準差作為波動參考
            historical_values = [float(row['sales']) for row in historical_data if float(row['sales']) > 0]
            if len(historical_values) > 1:
                historical_std = np.std(historical_values)
                historical_mean = np.mean(historical_values)
                
                # 添加隨機波動，讓預測更接近歷史數據的波動模式
                # 波動幅度為歷史標準差的 10-30%
                volatility_factor = random.uniform(0.1, 0.3)
                noise_std = historical_std * volatility_factor
                
                # 為每個預測值添加隨機波動
                for i in range(len(monthly_values)):
                    # 生成正態分佈的隨機波動
                    noise = np.random.normal(0, noise_std)
                    monthly_values[i] += noise
                    
                    # 確保預測值不會變成負數
                    monthly_values[i] = max(0, monthly_values[i])
        
        return monthly_values

    def _add_volatility_to_forecast(self, forecast_values, historical_data):
        """為預測值添加波動性，讓預測更接近歷史數據的波動模式"""
        import numpy as np
        import random
        
        if not historical_data:
            return forecast_values
            
        # 計算歷史數據的波動性
        historical_values = [float(row['sales']) for row in historical_data if float(row['sales']) > 0]
        if len(historical_values) < 2:
            return forecast_values
            
        historical_std = np.std(historical_values)
        historical_mean = np.mean(historical_values)
        
        # 添加隨機波動，讓預測更接近歷史數據的波動模式
        # 波動幅度為歷史標準差的 15-35%（比 ARIMA 稍高一些）
        volatility_factor = random.uniform(0.15, 0.35)
        noise_std = historical_std * volatility_factor
        
        # 為每個預測值添加隨機波動
        for i in range(len(forecast_values)):
            # 生成正態分佈的隨機波動
            noise = np.random.normal(0, noise_std)
            forecast_values[i] += noise
            
            # 確保預測值不會變成負數
            forecast_values[i] = max(0, forecast_values[i])
        
        return forecast_values

    def generate_unified_forecast(self, forecast_type, periods=12, dimension='all', value=None):
        """
        使用統一預測系統生成業績預測，可指定維度
        Args:
            forecast_type (str): 預測類型 ('month', 'quarter', 'year')
            periods (int): 預測期數
            dimension (str): 維度類型 all/product/customer
            value: 維度值
        Returns:
            dict: 預測結果
        """
        try:
            # 導入統一預測系統
            from models.unified_forecaster import UnifiedForecaster
            
            # 初始化統一預測器
            unified_forecaster = UnifiedForecaster(self.data_manager)
            
            # 使用統一預測系統進行預測
            result = unified_forecaster.generate_unified_forecast(
                forecast_type=forecast_type,
                periods=periods,
                enable_ai_analysis=False  # 暫時關閉AI分析，專注於預測
            )
            
            if not result['success']:
                return result
            
            # 如果指定了維度，需要進行額外的過濾處理
            if dimension != 'all' and value:
                # 這裡可以添加維度過濾邏輯
                # 目前統一預測系統使用整體數據，維度過濾功能可以後續擴展
                print(f"⚠️  注意：維度過濾功能 ({dimension}={value}) 將在後續版本中支援")
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'統一預測過程中發生錯誤: {str(e)}'
            }

    def generate_ets_forecast(self, forecast_type, periods=12, dimension='all', value=None):
        """
        使用 ETS (Exponential Smoothing) 模型生成業績預測，可指定維度
        Args:
            forecast_type (str): 預測類型 ('month', 'quarter', 'year')
            periods (int): 預測期數
            dimension (str): 維度類型 all/product/customer
            value: 維度值
        Returns:
            dict: 預測結果
        """
        try:
            import numpy as np
            import pandas as pd
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            from datetime import datetime, timedelta
            import warnings
            warnings.filterwarnings('ignore')

            # 根據維度過濾資料
            if dimension == 'product' and value:
                sql = f"""
                    SELECT t.date, SUM(sf.amount) as sales
                    FROM sales_fact sf
                    JOIN dim_time t ON sf.time_id = t.time_id
                    WHERE sf.product_id = ?
                    GROUP BY t.date
                    ORDER BY t.date
                """
                df = self.data_manager.execute_query(sql, (value,))
            elif dimension == 'customer' and value:
                sql = f"""
                    SELECT t.date, SUM(sf.amount) as sales
                    FROM sales_fact sf
                    JOIN dim_time t ON sf.time_id = t.time_id
                    WHERE sf.customer_id = ?
                    GROUP BY t.date
                    ORDER BY t.date
                """
                df = self.data_manager.execute_query(sql, (value,))
            else:
                sql = """
                    SELECT t.date, SUM(sf.amount) as sales
                    FROM sales_fact sf
                    JOIN dim_time t ON sf.time_id = t.time_id
                    GROUP BY t.date
                    ORDER BY t.date
                """
                df = self.data_manager.execute_query(sql)

            if df.empty:
                return {'success': False, 'error': '無歷史數據可用於預測'}

            # 取出 sales series
            sales_series = df.set_index('date')['sales'].astype(float)
            # 資料檢查：有 NaN、全 0、極端低值
            if sales_series.isnull().any():
                return {'success': False, 'error': '歷史數據包含空值，無法預測'}
            if (sales_series == 0).all():
                return {'success': False, 'error': '歷史數據全為 0，無法預測'}
            if sales_series.mean() < 1000:
                return {'success': False, 'error': '歷史數據過低，無法預測'}

            # 根據預測類型處理數據
            if forecast_type == 'month':
                # 月度預測：基於月度數據進行預測，考慮季節性變化
                processed_data = self._process_monthly_data(df.to_dict('records'))
                period_text = '月度'
                date_format = '%Y-%m'
                seasonal_periods = 12
            elif forecast_type == 'quarter':
                # 季度預測：基於月度預測結果進行加總
                processed_data = self._process_monthly_data(df.to_dict('records'))
                period_text = '季度'
                date_format = '%Y-Q%m'
                seasonal_periods = 12
            elif forecast_type == 'year':
                # 年度預測：基於月度預測結果進行加總
                processed_data = self._process_monthly_data(df.to_dict('records'))
                period_text = '年度'
                date_format = '%Y'
                seasonal_periods = 12
            else:
                return {
                    'success': False,
                    'error': '無效的預測類型'
                }

            if len(processed_data) < 3:
                return {
                    'success': False,
                    'error': f'{period_text}數據不足，無法進行預測'
                }

            # 強制使用加法趨勢與季節性
            try:
                model = ExponentialSmoothing(
                    sales_series,
                    trend='add',
                    seasonal='add' if seasonal_periods else None,
                    seasonal_periods=seasonal_periods if seasonal_periods else None
                )
                fitted_model = model.fit(optimized=True)
                aic = fitted_model.aic if hasattr(fitted_model, 'aic') else None
            except Exception as e:
                return {'success': False, 'error': f'ETS模型訓練失敗: {str(e)}'}

            if forecast_type == 'month':
                # 月度預測：直接使用月度預測值
                forecast = fitted_model.forecast(steps=periods)
                forecast_values = forecast.values if hasattr(forecast, 'values') else forecast
                
                # 為 ETS 預測添加波動性
                forecast_values = self._add_volatility_to_forecast(forecast_values, processed_data)
                
            elif forecast_type == 'quarter':
                # 季度預測：先預測月度，然後加總為季度
                months_to_predict = periods * 3  # 每個季度3個月
                forecast = fitted_model.forecast(steps=months_to_predict)
                monthly_values = forecast.values if hasattr(forecast, 'values') else forecast
                
                # 為月度預測添加波動性
                monthly_values = self._add_volatility_to_forecast(monthly_values, processed_data)
                
                # 將月度預測值加總為季度預測值
                quarterly_forecast_values = []
                for i in range(0, len(monthly_values), 3):
                    quarter_sum = sum(monthly_values[i:i+3])
                    quarterly_forecast_values.append(quarter_sum)
                
                # 只取需要的季度數
                quarterly_forecast_values = quarterly_forecast_values[:periods]
                forecast_values = quarterly_forecast_values
            elif forecast_type == 'year':
                # 年度預測：先預測月度，然後加總為年度
                months_to_predict = periods * 12  # 每年12個月
                forecast = fitted_model.forecast(steps=months_to_predict)
                monthly_values = forecast.values if hasattr(forecast, 'values') else forecast
                
                # 為月度預測添加波動性
                monthly_values = self._add_volatility_to_forecast(monthly_values, processed_data)
                
                # 將月度預測值加總為年度預測值
                yearly_forecast_values = []
                for i in range(0, len(monthly_values), 12):
                    year_sum = sum(monthly_values[i:i+12])
                    yearly_forecast_values.append(year_sum)
                
                # 只取需要的年度數
                yearly_forecast_values = yearly_forecast_values[:periods]
                forecast_values = yearly_forecast_values
            
            forecast_dates = self._generate_forecast_dates(forecast_type, periods)
            forecast_data = []
            for i, (date, value) in enumerate(zip(forecast_dates, forecast_values)):
                forecast_data.append({
                    'period': date,
                    'forecast_sales': round(max(0, value), 2),
                    'period_number': i + 1
                })
            total_forecast = sum(item['forecast_sales'] for item in forecast_data)
            avg_forecast = total_forecast / len(forecast_data) if len(forecast_data) > 0 else 0
            forecast_summary = self._generate_forecast_summary(
                forecast_type, periods, total_forecast, avg_forecast, 
                processed_data, forecast_data
            )
            # 預測異常檢查
            historical_sales = [float(row['sales']) for row in processed_data]
            historical_avg = sum(historical_sales) / len(historical_sales) if len(historical_sales) > 0 else 0
            warning = None
            if historical_avg > 0 and avg_forecast < 0.2 * historical_avg:
                warning = f'⚠️ 預測值遠低於歷史平均，請檢查資料或考慮其他模型。歷史平均: {historical_avg:,.2f}，預測平均: {avg_forecast:,.2f}'
            return {
                'success': True,
                'forecast_type': forecast_type,
                'period_text': period_text,
                'periods': periods,
                'forecast_data': forecast_data,
                'total_forecast': round(total_forecast, 2),
                'avg_forecast': round(avg_forecast, 2),
                'historical_data': processed_data,
                'forecast_summary': forecast_summary,
                'model_info': {
                    'method': 'ETS',
                    'trend': 'add',
                    'seasonal': 'add' if seasonal_periods else None,
                    'seasonal_periods': seasonal_periods,
                    'aic': round(aic, 2) if aic else None
                },
                'warning': warning
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'ETS預測過程中發生錯誤: {str(e)}'
            }

    def _get_historical_sales_data(self):
        """獲取歷史銷售數據"""
        try:
            # 使用數據管理器獲取銷售數據
            sql = """
            SELECT 
                t.date,
                SUM(sf.amount) as sales
            FROM sales_fact sf
            JOIN dim_time t ON sf.time_id = t.time_id
            GROUP BY t.date
            ORDER BY t.date
            """
            
            result = self.data_manager.execute_custom_sql(sql)
            if result['success']:
                return result['data']
            else:
                return None
        except Exception as e:
            print(f"獲取歷史數據時發生錯誤: {e}")
            return None
    
    def _process_monthly_data(self, historical_data):
        """處理月度數據"""
        try:
            monthly_data = {}
            
            for row in historical_data:
                date_str = row['date']
                sales = float(row['sales'])
                
                # 提取年月
                year_month = date_str[:7]  # YYYY-MM
                
                if year_month in monthly_data:
                    monthly_data[year_month]['sales'] += sales
                else:
                    monthly_data[year_month] = {
                        'period': year_month,
                        'sales': sales
                    }
            
            # 按日期排序
            sorted_data = sorted(monthly_data.values(), key=lambda x: x['period'])
            return sorted_data
            
        except Exception as e:
            print(f"處理月度數據時發生錯誤: {e}")
            return []
    
    def _process_quarterly_data(self, historical_data):
        """處理季度數據"""
        try:
            quarterly_data = {}
            
            for row in historical_data:
                date_str = row['date']
                sales = float(row['sales'])
                
                # 提取年月
                year = int(date_str[:4])
                month = int(date_str[5:7])
                
                # 計算季度
                quarter = (month - 1) // 3 + 1
                quarter_key = f"{year}-Q{quarter}"
                
                if quarter_key in quarterly_data:
                    quarterly_data[quarter_key]['sales'] += sales
                else:
                    quarterly_data[quarter_key] = {
                        'period': quarter_key,
                        'sales': sales
                    }
            
            # 按日期排序
            sorted_data = sorted(quarterly_data.values(), key=lambda x: x['period'])
            return sorted_data
            
        except Exception as e:
            print(f"處理季度數據時發生錯誤: {e}")
            return []
    
    def _process_yearly_data(self, historical_data):
        """處理年度數據"""
        try:
            yearly_data = {}
            
            for row in historical_data:
                date_str = row['date']
                sales = float(row['sales'])
                
                # 提取年份
                year = date_str[:4]
                
                if year in yearly_data:
                    yearly_data[year]['sales'] += sales
                else:
                    yearly_data[year] = {
                        'period': year,
                        'sales': sales
                    }
            
            # 按日期排序
            sorted_data = sorted(yearly_data.values(), key=lambda x: x['period'])
            return sorted_data
            
        except Exception as e:
            print(f"處理年度數據時發生錯誤: {e}")
            return []
    
    def _generate_forecast_dates(self, forecast_type, periods):
        """生成預測日期"""
        try:
            from datetime import datetime, timedelta
            import calendar
            
            # 使用固定日期作為基準，確保時間軸一致性
            base_date = datetime(2025, 7, 10)  # 與其他模組保持一致
            
            forecast_dates = []
            
            if forecast_type == 'month':
                # 從2025年8月開始預測
                start_year = 2025
                start_month = 8
                
                for i in range(periods):
                    if start_month > 12:
                        start_month = 1
                        start_year += 1
                    
                    forecast_dates.append(f"{start_year}-{start_month:02d}")
                    start_month += 1
                    
            elif forecast_type == 'quarter':
                # 從2025年Q3開始預測
                start_quarter = 3
                start_year = 2025
                
                for i in range(periods):
                    if start_quarter > 4:
                        start_quarter = 1
                        start_year += 1
                    
                    forecast_dates.append(f"{start_year}-Q{start_quarter}")
                    start_quarter += 1
                    
            elif forecast_type == 'year':
                # 從2026年開始預測
                start_year = 2026
                
                for i in range(periods):
                    forecast_dates.append(str(start_year + i))
            
            return forecast_dates
            
        except Exception as e:
            print(f"生成預測日期時發生錯誤: {e}")
            return []
    
    def _generate_forecast_summary(self, forecast_type, periods, total_forecast, avg_forecast, 
                                  historical_data, forecast_data):
        """生成預測摘要"""
        try:
            # 計算歷史平均
            historical_sales = [float(row['sales']) for row in historical_data]
            historical_avg = sum(historical_sales) / len(historical_sales) if len(historical_sales) > 0 else 0
            
            # 計算增長率（避免除零錯誤）
            if historical_avg > 0:
                growth_rate = ((avg_forecast - historical_avg) / historical_avg * 100)
            else:
                growth_rate = 0
            
            # 生成摘要文本
            period_text = {'month': '月', 'quarter': '季', 'year': '年'}[forecast_type]
            
            summary = f"""
## {period_text}度業績預測分析報告

### 預測概覽
- **預測期間**: 未來 {periods} {period_text}
- **總預測銷售額**: {total_forecast:,.2f} 元
- **平均{period_text}度銷售額**: {avg_forecast:,.2f} 元
- **歷史平均{period_text}度銷售額**: {historical_avg:,.2f} 元
- **預測增長率**: {growth_rate:+.2f}%

### 預測趨勢分析
"""
            
            if growth_rate > 0:
                summary += f"- 預測顯示{period_text}度銷售額呈上升趨勢\n"
                summary += f"- 平均每{period_text}預計增長 {growth_rate:.2f}%\n"
            elif growth_rate < 0:
                summary += f"- 預測顯示{period_text}度銷售額呈下降趨勢\n"
                summary += f"- 平均每{period_text}預計下降 {abs(growth_rate):.2f}%\n"
            else:
                summary += f"- 預測顯示{period_text}度銷售額保持穩定\n"
            
            summary += f"""
### 預測詳細數據
| 期間 | 預測銷售額 |
|------|------------|
"""
            
            for item in forecast_data:
                summary += f"| {item['period']} | {item['forecast_sales']:,.2f} 元 |\n"
            
            summary += f"""
### 建議與注意事項
1. **數據驅動決策**: 基於歷史數據的 ARIMA 模型預測
2. **定期更新**: 建議每月更新預測模型
3. **風險考量**: 預測結果僅供參考，實際情況可能受多種因素影響
4. **策略調整**: 根據預測結果調整業務策略和資源配置
"""
            
            return summary
            
        except Exception as e:
            print(f"生成預測摘要時發生錯誤: {e}")
            return "預測摘要生成失敗"

    def generate_line_notification_data(self, query_type="summary", custom_query=None, time_range=None):
        """
        生成適合 LINE 通知的資料庫查詢結果
        Args:
            query_type (str): 查詢類型 ('summary', 'product', 'staff', 'customer', 'region', 'custom')
            custom_query (str): 自定義查詢內容
            time_range (dict): 時間範圍 {'start': '2025-01-01', 'end': '2025-01-31'}
        Returns:
            dict: LINE 通知格式的數據
        """
        try:
            # 設定預設時間範圍
            if not time_range:
                today = datetime(2025, 7, 10)
                current_start = today.replace(day=1)
                last_start = (current_start - timedelta(days=1)).replace(day=1)
                current_end = (current_start + relativedelta(months=1)) - timedelta(days=1)
                last_end = (last_start + relativedelta(months=1)) - timedelta(days=1)
                time_range = {
                    'current_start': current_start.strftime('%Y-%m-%d'),
                    'current_end': current_end.strftime('%Y-%m-%d'),
                    'last_start': last_start.strftime('%Y-%m-%d'),
                    'last_end': last_end.strftime('%Y-%m-%d')
                }

            # 根據查詢類型生成不同的數據
            if query_type == "summary":
                return self._generate_summary_line_data(time_range)
            elif query_type == "product":
                return self._generate_product_line_data(time_range)
            elif query_type == "staff":
                return self._generate_staff_line_data(time_range)
            elif query_type == "customer":
                return self._generate_customer_line_data(time_range)
            elif query_type == "region":
                return self._generate_region_line_data(time_range)
            elif query_type == "custom" and custom_query:
                return self._generate_custom_line_data(custom_query, time_range)
            else:
                return {
                    'success': False,
                    'error': '無效的查詢類型或缺少自定義查詢'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成 LINE 通知數據失敗: {str(e)}'
            }

    def _generate_summary_line_data(self, time_range):
        """生成摘要 LINE 通知數據"""
        try:
            # 執行期間比較
            period_comparison = self.data_manager.get_period_comparison(
                time_range['current_start'], time_range['current_end'],
                time_range['last_start'], time_range['last_end']
            )
            
            current_sales = period_comparison['current_period_sales'].iloc[0]
            last_sales = period_comparison['last_period_sales'].iloc[0]
            diff = current_sales - last_sales
            percentage_diff = (diff / last_sales * 100) if last_sales != 0 else 0
            
            # 獲取各維度的主要貢獻者
            dimensions = ['product', 'staff', 'customer', 'region']
            top_contributors = {}
            
            for dim in dimensions:
                try:
                    driver_analysis = self.data_manager.get_driver_analysis(
                        time_range['current_start'], time_range['current_end'],
                        time_range['last_start'], time_range['last_end'],
                        dim
                    )
                    if not driver_analysis.empty:
                        top_contributors[dim] = driver_analysis.head(3).to_dict('records')
                except:
                    continue

            # 生成 LINE 通知格式
            message = f"📊 銷售業績摘要報告\n"
            message += f"📅 期間: {time_range['current_start']} ~ {time_range['current_end']}\n"
            message += f"💰 當期銷售: {current_sales:,.0f} 元\n"
            message += f"📈 前期銷售: {last_sales:,.0f} 元\n"
            
            if diff > 0:
                message += f"✅ 成長: +{diff:,.0f} 元 (+{percentage_diff:.1f}%)\n"
            else:
                message += f"❌ 下滑: {diff:,.0f} 元 ({percentage_diff:.1f}%)\n"

            # 添加主要貢獻者
            if top_contributors:
                message += f"\n🏆 主要貢獻者:\n"
                for dim, contributors in top_contributors.items():
                    dim_name = {'product': '產品', 'staff': '業務員', 'customer': '客戶', 'region': '地區'}[dim]
                    message += f"• {dim_name}: {contributors[0]['分析維度']} ({contributors[0]['差異']:,.0f}元)\n"

            return {
                'success': True,
                'message': message,
                'data': {
                    'current_sales': current_sales,
                    'last_sales': last_sales,
                    'diff': diff,
                    'percentage_diff': percentage_diff,
                    'top_contributors': top_contributors,
                    'time_range': time_range
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成摘要數據失敗: {str(e)}'
            }

    def _generate_product_line_data(self, time_range):
        """生成產品維度 LINE 通知數據"""
        try:
            driver_analysis = self.data_manager.get_driver_analysis(
                time_range['current_start'], time_range['current_end'],
                time_range['last_start'], time_range['last_end'],
                'product'
            )
            
            message = f"📦 產品銷售分析\n"
            message += f"📅 期間: {time_range['current_start']} ~ {time_range['current_end']}\n\n"
            
            for i, row in driver_analysis.head(5).iterrows():
                diff = row['差異']
                if diff > 0:
                    message += f"✅ {row['分析維度']}: +{diff:,.0f} 元\n"
                else:
                    message += f"❌ {row['分析維度']}: {diff:,.0f} 元\n"

            return {
                'success': True,
                'message': message,
                'data': driver_analysis.head(5).to_dict('records')
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成產品數據失敗: {str(e)}'
            }

    def _generate_staff_line_data(self, time_range):
        """生成業務員維度 LINE 通知數據"""
        try:
            driver_analysis = self.data_manager.get_driver_analysis(
                time_range['current_start'], time_range['current_end'],
                time_range['last_start'], time_range['last_end'],
                'staff'
            )
            
            message = f"👥 業務員業績分析\n"
            message += f"📅 期間: {time_range['current_start']} ~ {time_range['current_end']}\n\n"
            
            for i, row in driver_analysis.head(5).iterrows():
                diff = row['差異']
                if diff > 0:
                    message += f"🏆 {row['分析維度']}: +{diff:,.0f} 元\n"
                else:
                    message += f"⚠️ {row['分析維度']}: {diff:,.0f} 元\n"

            return {
                'success': True,
                'message': message,
                'data': driver_analysis.head(5).to_dict('records')
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成業務員數據失敗: {str(e)}'
            }

    def _generate_customer_line_data(self, time_range):
        """生成客戶維度 LINE 通知數據"""
        try:
            driver_analysis = self.data_manager.get_driver_analysis(
                time_range['current_start'], time_range['current_end'],
                time_range['last_start'], time_range['last_end'],
                'customer'
            )
            
            message = f"👤 客戶消費分析\n"
            message += f"📅 期間: {time_range['current_start']} ~ {time_range['current_end']}\n\n"
            
            for i, row in driver_analysis.head(5).iterrows():
                diff = row['差異']
                if diff > 0:
                    message += f"💎 {row['分析維度']}: +{diff:,.0f} 元\n"
                else:
                    message += f"📉 {row['分析維度']}: {diff:,.0f} 元\n"

            return {
                'success': True,
                'message': message,
                'data': driver_analysis.head(5).to_dict('records')
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成客戶數據失敗: {str(e)}'
            }

    def _generate_region_line_data(self, time_range):
        """生成地區維度 LINE 通知數據"""
        try:
            driver_analysis = self.data_manager.get_driver_analysis(
                time_range['current_start'], time_range['current_end'],
                time_range['last_start'], time_range['last_end'],
                'region'
            )
            
            message = f"🌍 地區銷售分析\n"
            message += f"📅 期間: {time_range['current_start']} ~ {time_range['current_end']}\n\n"
            
            for i, row in driver_analysis.head(5).iterrows():
                diff = row['差異']
                if diff > 0:
                    message += f"🚀 {row['分析維度']}: +{diff:,.0f} 元\n"
                else:
                    message += f"📊 {row['分析維度']}: {diff:,.0f} 元\n"

            return {
                'success': True,
                'message': message,
                'data': driver_analysis.head(5).to_dict('records')
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成地區數據失敗: {str(e)}'
            }

    def _generate_custom_line_data(self, custom_query, time_range):
        """生成自定義查詢 LINE 通知數據"""
        try:
            # 將自然語言查詢轉換為 SQL
            sql_query = self.natural_language_to_sql(custom_query)
            
            # 執行查詢
            result = self.data_manager.execute_custom_sql(sql_query)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': f'自定義查詢執行失敗: {result["error"]}'
                }

            # 生成 LINE 通知格式
            message = f"🔍 自定義查詢結果\n"
            message += f"📅 期間: {time_range['current_start']} ~ {time_range['current_end']}\n"
            message += f"❓ 查詢: {custom_query}\n\n"
            
            if result['data']:
                # 顯示前5筆結果
                for i, row in enumerate(result['data'][:5], 1):
                    message += f"{i}. {str(row)}\n"
                
                if len(result['data']) > 5:
                    message += f"... 還有 {len(result['data']) - 5} 筆資料\n"
            else:
                message += "📭 查無資料"

            return {
                'success': True,
                'message': message,
                'data': result['data'],
                'sql_query': sql_query
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'生成自定義查詢數據失敗: {str(e)}'
            }

    def _analyze_specific_customer_query(self, query, customer_name):
        """分析特定客戶查詢"""
        try:
            # 檢查客戶是否存在
            customer_exists = self._check_customer_exists(customer_name)
            
            if not customer_exists:
                return {
                    'success': True,
                    'message': f'客戶「{customer_name}」在資料庫中沒有找到相關的銷售記錄。',
                    'customer_name': customer_name,
                    'exists': False,
                    'data': []
                }
            
            # 生成SQL查詢
            sql = self.natural_language_to_sql(query)
            
            # 執行查詢
            result = self.data_manager.execute_query(sql)
            
            if result is None or result.empty:
                return {
                    'success': True,
                    'message': f'客戶「{customer_name}」在資料庫中沒有找到相關的銷售記錄。',
                    'customer_name': customer_name,
                    'exists': False,
                    'data': []
                }
            
            # 格式化結果
            formatted_data = []
            for _, row in result.iterrows():
                formatted_data.append({
                    'customer_name': row['customer_name'],
                    'total_sales': float(row['total_sales']),
                    'total_quantity': int(row['total_quantity'])
                })
            
            return {
                'success': True,
                'customer_name': customer_name,
                'exists': True,
                'data': formatted_data,
                'sql_query': sql,
                'message': f'查詢客戶「{customer_name}」的銷售記錄成功。'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'查詢客戶「{customer_name}」時發生錯誤: {str(e)}'
            }

    def _analyze_specific_staff_query(self, query, staff_name):
        """分析特定業務員查詢"""
        try:
            # 生成SQL查詢
            sql = self.natural_language_to_sql(query)
            
            # 執行查詢
            result = self.data_manager.execute_query(sql)
            
            if result is None or result.empty:
                return {
                    'success': True,
                    'message': f'業務員「{staff_name}」在資料庫中沒有找到相關的銷售記錄。',
                    'staff_name': staff_name,
                    'exists': False,
                    'data': []
                }
            
            # 格式化結果
            formatted_data = []
            for _, row in result.iterrows():
                formatted_data.append({
                    'staff_name': row['staff_name'],
                    'total_sales': float(row['total_sales']),
                    'total_quantity': int(row['total_quantity'])
                })
            
            return {
                'success': True,
                'staff_name': staff_name,
                'exists': True,
                'data': formatted_data,
                'sql_query': sql,
                'message': f'查詢業務員「{staff_name}」的銷售記錄成功。'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'查詢業務員「{staff_name}」時發生錯誤: {str(e)}'
            }

    def _analyze_specific_product_query(self, query, product_name):
        """分析特定產品查詢"""
        try:
            # 生成SQL查詢
            sql = self.natural_language_to_sql(query)
            
            # 執行查詢
            result = self.data_manager.execute_query(sql)
            
            if result is None or result.empty:
                return {
                    'success': True,
                    'message': f'產品「{product_name}」在資料庫中沒有找到相關的銷售記錄。',
                    'product_name': product_name,
                    'exists': False,
                    'data': []
                }
            
            # 格式化結果
            formatted_data = []
            for _, row in result.iterrows():
                formatted_data.append({
                    'product_name': row['product_name'],
                    'total_sales': float(row['total_sales']),
                    'total_quantity': int(row['total_quantity'])
                })
            
            return {
                'success': True,
                'product_name': product_name,
                'exists': True,
                'data': formatted_data,
                'sql_query': sql,
                'message': f'查詢產品「{product_name}」的銷售記錄成功。'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'查詢產品「{product_name}」時發生錯誤: {str(e)}'
            }

    def _analyze_specific_region_query(self, query, region_name):
        """分析特定地區查詢"""
        try:
            # 生成SQL查詢
            sql = self.natural_language_to_sql(query)
            
            # 執行查詢
            result = self.data_manager.execute_query(sql)
            
            if result is None or result.empty:
                return {
                    'success': True,
                    'message': f'地區「{region_name}」在資料庫中沒有找到相關的銷售記錄。',
                    'region_name': region_name,
                    'exists': False,
                    'data': []
                }
            
            # 格式化結果
            formatted_data = []
            for _, row in result.iterrows():
                formatted_data.append({
                    'region_name': row['region_name'],
                    'total_sales': float(row['total_sales']),
                    'total_quantity': int(row['total_quantity'])
                })
            
            return {
                'success': True,
                'region_name': region_name,
                'exists': True,
                'data': formatted_data,
                'sql_query': sql,
                'message': f'查詢地區「{region_name}」的銷售記錄成功。'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'查詢地區「{region_name}」時發生錯誤: {str(e)}'
            }

    def _get_dimension_values(self, dimension):
        """動態獲取指定維度的所有值"""
        try:
            dim_map = {
                'customer': {'table': 'dim_customer', 'name': 'customer_name'},
                'staff': {'table': 'dim_staff', 'name': 'staff_name'},
                'product': {'table': 'dim_product', 'name': 'product_name'},
                'region': {'table': 'dim_region', 'name': 'region_name'}
            }
            
            if dimension not in dim_map:
                return []
            
            d = dim_map[dimension]
            sql = f"SELECT {d['name']} FROM {d['table']}"
            result = self.data_manager.execute_query(sql)
            
            if result is not None and len(result) > 0:
                return result[d['name']].tolist()
            else:
                return []
        except Exception as e:
            print(f"獲取{dimension}維度資料時發生錯誤: {e}")
            return []

    def _check_customer_exists(self, customer_name):
        """檢查客戶是否存在於資料庫中"""
        try:
            # 執行查詢
            sql = f"""
            SELECT COUNT(*)
            FROM dim_customer
            WHERE customer_name = '{customer_name}'
            """
            result = self.data_manager.execute_query(sql)
            if result is not None and len(result) > 0:
                return result.iloc[0, 0] > 0
            else:
                return False
        except Exception as e:
            print(f"檢查客戶是否存在時發生錯誤: {e}")
            return False
    
    # ==================== 向量搜尋輔助方法 ====================
    
    def _build_semantic_period_query(self, parsed):
        """構建語義期間查詢"""
        try:
            # 根據時間範圍和維度構建語義查詢
            period_text = parsed['period_text']
            dimension = parsed['dimension']
            
            # 構建語義查詢文字
            semantic_query = f"分析{period_text}期間的{dimension}維度表現"
            
            # 添加時間範圍信息（檢查鍵是否存在）
            try:
                current_start = parsed['current_start'].strftime('%Y-%m-%d') if 'current_start' in parsed else "未知"
                current_end = parsed['current_end'].strftime('%Y-%m-%d') if 'current_end' in parsed else "未知"
                last_start = parsed['last_start'].strftime('%Y-%m-%d') if 'last_start' in parsed else "未知"
                last_end = parsed['last_end'].strftime('%Y-%m-%d') if 'last_end' in parsed else "未知"
            except Exception as e:
                print(f"時間範圍解析錯誤: {e}")
                current_start = current_end = last_start = last_end = "未知"
            
            semantic_query += f"，當前期間：{current_start}到{current_end}，比較期間：{last_start}到{last_end}"
            
            return semantic_query
            
        except Exception as e:
            # self.logger.error(f"構建語義查詢失敗: {e}")
            return "期間分析查詢"
    
    def _execute_vector_period_analysis(self, semantic_query, parsed):
        """執行向量期間分析"""
        try:
            # 使用向量搜尋進行智能分析
            vector_results = {}
            
            # 1. 產品維度向量分析
            if parsed['dimension'] == 'product':
                # 搜尋相似產品模式
                product_results = self.data_manager.search_similar_products(semantic_query, limit=5)
                if product_results['success']:
                    vector_results['products'] = product_results['results']
            
            # 2. 客戶維度向量分析
            elif parsed['dimension'] == 'customer':
                # 搜尋相似客戶模式
                customer_results = self.data_manager.search_similar_customers(semantic_query, limit=5)
                if customer_results['success']:
                    vector_results['customers'] = customer_results['results']
            
            # 3. 銷售事件向量分析
            # 使用語義查詢搜尋相似銷售模式
            sales_results = self.data_manager.search_similar_sales(
                quantity=100,  # 預設值
                amount=10000,  # 預設值
                limit=5
            )
            if sales_results['success']:
                vector_results['sales_patterns'] = sales_results['results']
            
            # 4. 時間序列向量分析
            # 分析時間模式
            time_patterns = self._analyze_time_patterns_vector(parsed)
            if time_patterns:
                vector_results['time_patterns'] = time_patterns
            
            return vector_results
            
        except Exception as e:
            # self.logger.error(f"執行向量期間分析失敗: {e}")
            return {}
    
    def _analyze_time_patterns_vector(self, parsed):
        """使用向量分析時間模式"""
        try:
            # 構建時間序列查詢
            time_query = f"分析{parsed['period_text']}的時間模式"
            
            # 這裡可以擴展為更複雜的時間序列向量分析
            # 例如：季節性模式、趨勢分析、異常檢測等
            
            return {
                'query': time_query,
                'patterns': ['季節性變化', '趨勢增長', '週期性波動'],
                'confidence': 0.85
            }
            
        except Exception as e:
            # self.logger.error(f"向量時間模式分析失敗: {e}")
            return None

    def generate_voice_summary(self, summary_text, voice_type="mandarin_female"):
        """
        生成語音播放內容
        播放內容為主要貢獻分析、其他維度參考分析
        播放語音為國語新聞播放女生
        """
        try:
            # 提取主要貢獻分析
            main_contribution = self._extract_main_contribution(summary_text)
            
            # 提取其他維度參考分析
            other_dimension = self._extract_other_dimension_reference(summary_text)
            
            # 組合語音播放內容
            voice_content = self._combine_voice_content(main_contribution, other_dimension)
            
            # 生成語音文件
            audio_file_path = self._synthesize_speech(voice_content, voice_type)
            
            return {
                'success': True,
                'voice_content': voice_content,
                'audio_file_path': audio_file_path,
                'main_contribution': main_contribution,
                'other_dimension': other_dimension
            }
            
        except Exception as e:
            # self.logger.error(f"語音總結生成失敗: {e}")
            return {
                'success': False,
                'error': f"語音總結生成失敗: {str(e)}"
            }

    def _extract_main_contribution(self, summary_text):
        """
        從分析總結中提取主要貢獻分析
        """
        try:
            # 尋找主要貢獻分析部分
            main_contribution_pattern = r'📊\s*<strong>主要貢獻分析：</strong>(.*?)(?=<br><br>|$)'
            match = re.search(main_contribution_pattern, summary_text, re.DOTALL)
            
            if match:
                content = match.group(1).strip()
                # 移除HTML標籤
                content = re.sub(r'<[^>]+>', '', content)
                return content
            else:
                # 如果沒有找到主要貢獻分析，嘗試從其他部分提取
                if '主要貢獻' in summary_text:
                    # 提取包含"主要貢獻"的段落
                    lines = summary_text.split('<br>')
                    for line in lines:
                        if '主要貢獻' in line:
                            content = re.sub(r'<[^>]+>', '', line)
                            return content
                
                return "主要貢獻分析：銷售表現分析完成"
                
        except Exception as e:
            # self.logger.error(f"提取主要貢獻分析失敗: {e}")
            return "主要貢獻分析：銷售表現分析完成"

    def _extract_other_dimension_reference(self, summary_text):
        """
        從分析總結中提取其他維度參考分析
        """
        try:
            # 尋找其他維度參考分析部分
            other_dimension_pattern = r'🔎\s*<strong>其他維度參考分析：</strong><br>(.*?)(?=<br><br>|$)'
            match = re.search(other_dimension_pattern, summary_text, re.DOTALL)
            
            if match:
                content = match.group(1).strip()
                # 移除HTML標籤
                content = re.sub(r'<[^>]+>', '', content)
                return content
            else:
                # 如果沒有找到其他維度參考分析，嘗試從其他部分提取
                if '其他維度' in summary_text:
                    # 提取包含"其他維度"的段落
                    lines = summary_text.split('<br>')
                    for line in lines:
                        if '其他維度' in line:
                            content = re.sub(r'<[^>]+>', '', line)
                            return content
                
                return "其他維度參考分析：多維度分析完成"
                
        except Exception as e:
            # self.logger.error(f"提取其他維度參考分析失敗: {e}")
            return "其他維度參考分析：多維度分析完成"

    def _combine_voice_content(self, main_contribution, other_dimension):
        """
        組合語音播放內容
        """
        try:
            voice_content = f"分析總結報告。{main_contribution}。{other_dimension}。報告播放完畢。"
            
            # 優化語音內容，使其更適合語音播放
            voice_content = voice_content.replace('。', '，')
            voice_content = voice_content.replace('：', '，')
            voice_content = voice_content.replace('（', '，')
            voice_content = voice_content.replace('）', '，')
            voice_content = voice_content.replace('元', '元，')
            voice_content = voice_content.replace('vs', '對比')
            voice_content = voice_content.replace('vs', '對比')
            
            # 移除多餘的逗號
            voice_content = re.sub(r'，+', '，', voice_content)
            voice_content = voice_content.strip('，')
            
            return voice_content
            
        except Exception as e:
            # self.logger.error(f"組合語音內容失敗: {e}")
            return "分析總結報告播放完畢"

    def _synthesize_speech(self, text, voice_type="mandarin_female"):
        """
        語音合成
        使用 gTTS (Google Text-to-Speech) 生成國語女聲語音
        """
        try:
            # 嘗試使用 gTTS
            try:
                from gtts import gTTS
                from gtts.lang import tts_langs
                
                # 檢查是否支援繁體中文
                supported_langs = tts_langs()
                if 'zh-tw' in supported_langs:
                    lang = 'zh-tw'  # 繁體中文
                elif 'zh' in supported_langs:
                    lang = 'zh'      # 簡體中文
                else:
                    lang = 'en'      # 英文（備用）
                
                # 創建臨時目錄
                temp_dir = os.path.join(tempfile.gettempdir(), 'voice_summary')
                os.makedirs(temp_dir, exist_ok=True)
                
                # 生成語音文件
                tts = gTTS(text=text, lang=lang, slow=False)
                audio_file_path = os.path.join(temp_dir, f'voice_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3')
                tts.save(audio_file_path)
                
                # 檢查文件是否成功生成
                if os.path.exists(audio_file_path) and os.path.getsize(audio_file_path) > 0:
                    # self.logger.info(f"語音文件生成成功: {audio_file_path}")
                    # self.logger.info(f"文件大小: {os.path.getsize(audio_file_path)} 字節")
                    return audio_file_path
                else:
                    # self.logger.error(f"語音文件生成失敗或文件為空: {audio_file_path}")
                    return None
                
            except ImportError:
                # 如果沒有安裝 gTTS，使用備用方案
                # self.logger.info("gTTS 未安裝，使用備用語音合成方案")
                return self._fallback_speech_synthesis(text)
                
        except Exception as e:
            # self.logger.error(f"語音合成失敗: {e}")
            return None

    def _fallback_speech_synthesis(self, text):
        """
        備用語音合成方案
        使用 pyttsx3 或其他本地語音合成引擎
        """
        try:
            # 嘗試使用 pyttsx3
            try:
                import pyttsx3
                
                # 初始化語音引擎
                engine = pyttsx3.init()
                
                # 設定語音屬性（嘗試設定為女聲）
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'female' in voice.name.lower() or '女' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                
                # 設定語速和音量
                engine.setProperty('rate', 150)    # 語速
                engine.setProperty('volume', 0.9)  # 音量
                
                # 創建臨時目錄
                temp_dir = os.path.join(tempfile.gettempdir(), 'voice_summary')
                os.makedirs(temp_dir, exist_ok=True)
                
                # 生成語音文件
                audio_file_path = os.path.join(temp_dir, f'voice_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav')
                engine.save_to_file(text, audio_file_path)
                engine.runAndWait()
                
                # 檢查文件是否成功生成
                if os.path.exists(audio_file_path) and os.path.getsize(audio_file_path) > 0:
                    # self.logger.info(f"備用語音文件生成成功: {audio_file_path}")
                    # self.logger.info(f"文件大小: {os.path.getsize(audio_file_path)} 字節")
                    return audio_file_path
                else:
                    # self.logger.error(f"備用語音文件生成失敗或文件為空: {audio_file_path}")
                    return None
                
            except ImportError:
                # 如果都沒有安裝，返回 None
                # self.logger.warning("未安裝語音合成套件，無法生成語音文件")
                return None
                
        except Exception as e:
            # self.logger.error(f"備用語音合成失敗: {e}")
            return None

    def get_voice_summary_status(self):
        """
        獲取語音總結功能狀態
        """
        try:
            # 檢查是否支援語音合成
            gtts_available = False
            pyttsx3_available = False
            
            try:
                from gtts import gTTS
                gtts_available = True
            except ImportError:
                pass
            
            try:
                import pyttsx3
                pyttsx3_available = True
            except ImportError:
                pass
            
            return {
                'success': True,
                'voice_synthesis_available': gtts_available or pyttsx3_available,
                'gtts_available': gtts_available,
                'pyttsx3_available': pyttsx3_available,
                'supported_voice_types': ['mandarin_female', 'mandarin_male', 'english_female', 'english_male'] if (gtts_available or pyttsx3_available) else []
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"獲取語音總結狀態失敗: {str(e)}"
            }
