# models/data_manager.py
# 數據管理器模型 - 負責所有數據庫操作

import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta
import os

class DataManager:
    """
    模型(Model)層: 處理所有數據庫的建立、數據生成和查詢。
    """
    def __init__(self, db_file):
        """
        初始化DataManager。如果資料庫檔案不存在，則建立並生成初始數據。
        """
        self.db_file = db_file
        if not os.path.exists(self.db_file):
            print("偵測到資料庫檔案不存在，正在進行首次初始化...")
            self.conn = self._get_connection()
            self._create_schema()
            self._generate_initial_data()
            print(f"資料庫 '{self.db_file}' 初始化完成。")
        else:
            self.conn = self._get_connection()
            print(f"已成功連接至現有資料庫 '{self.db_file}'。")

    def _get_connection(self):
        """建立並返回資料庫連接。"""
        return sqlite3.connect(self.db_file, check_same_thread=False)

    def _create_schema(self):
        """根據規格書建立資料庫綱要 (Schema)。"""
        cursor = self.conn.cursor()
        
        print("正在建立維度表 (Dimension Tables)...")
        # 維度表 (來自規格書 Page 1 & 2)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_product (
            product_id INTEGER PRIMARY KEY, product_name TEXT, category TEXT, brand TEXT
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id INTEGER PRIMARY KEY, customer_name TEXT, gender TEXT, age INTEGER, loyalty_level TEXT
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_staff (
            staff_id INTEGER PRIMARY KEY, staff_name TEXT, title TEXT, hire_date TEXT
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_region (
            region_id INTEGER PRIMARY KEY, region_name TEXT, country TEXT, city TEXT
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_time (
            time_id INTEGER PRIMARY KEY, date TEXT, month INTEGER, quarter INTEGER, year INTEGER
        )''')
        
        print("正在建立事實表 (Fact Table)...")
        # 事實表 (來自規格書 Page 1)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_fact (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER, customer_id INTEGER, staff_id INTEGER, region_id INTEGER, time_id INTEGER,
            quantity INTEGER, amount REAL,
            FOREIGN KEY (product_id) REFERENCES dim_product(product_id),
            FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
            FOREIGN KEY (staff_id) REFERENCES dim_staff(staff_id),
            FOREIGN KEY (region_id) REFERENCES dim_region(region_id),
            FOREIGN KEY (time_id) REFERENCES dim_time(time_id)
        )''')
        
        self.conn.commit()
        print("資料庫綱要建立完成。")

    def _generate_initial_data(self):
        """生成初始維度數據和3000筆事實數據。"""
        cursor = self.conn.cursor()

        print("正在生成維度表基礎數據...")
        # 1. 填入維度表數據
        products = [ (1, '高效能筆記型電腦', '電子產品', 'A品牌'), (2, '無線藍牙耳機', '電子產品', 'B品牌'), (3, '人體工學辦公椅', '家具', 'C品牌'), (4, '智能運動手錶', '穿戴裝置', 'A品牌'), (5, '有機咖啡豆', '食品', 'D品牌') ]
        cursor.executemany('INSERT OR IGNORE INTO dim_product VALUES (?, ?, ?, ?)', products)

        customers = [ (1, '台塑', '股', 35, '金級'), (2, '台泥', '股', 28, '銀級'), (3, '世紀民生', '股', 5, '白金級'), (4, '信立化學', '股', 32, '普通') ]
        cursor.executemany('INSERT OR IGNORE INTO dim_customer VALUES (?, ?, ?, ?, ?)', customers)

        staff = [ (1, '王小明', '銷售經理', '2022-01-15'), (2, '李美麗', '銷售專員', '2023-03-20'), (3, '趙大為', '銷售專員', '2023-08-01') ]
        cursor.executemany('INSERT OR IGNORE INTO dim_staff VALUES (?, ?, ?, ?)', staff)

        regions = [(1, '北區', '台灣', '台北'), (2, '中區', '台灣', '台中'), (3, '南區', '台灣', '高雄')]
        cursor.executemany('INSERT OR IGNORE INTO dim_region VALUES (?, ?, ?, ?)', regions)
        
        # 2. 填入時間維度表 (2024/01/01 - 2025/12/31)
        print("正在生成時間維度數據 (2024-2025)...")
        time_entries = []
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2025, 12, 31)
        current_date = start_date
        time_id = 1
        while current_date <= end_date:
            quarter = (current_date.month - 1) // 3 + 1
            time_entries.append((time_id, current_date.strftime('%Y-%m-%d'), current_date.month, quarter, current_date.year))
            current_date += timedelta(days=1)
            time_id += 1
        cursor.executemany('INSERT OR IGNORE INTO dim_time (time_id, date, month, quarter, year) VALUES (?, ?, ?, ?, ?)', time_entries)
        
        # 3. 生成100筆銷售事實數據
        print("正在生成3000筆銷售事實數據...")
        time_ids = [row[0] for row in cursor.execute('SELECT time_id FROM dim_time').fetchall()]
        sales_facts = []
        for _ in range(3000):
            product_id = random.randint(1, 5)
            customer_id = random.randint(1, 4)
            staff_id = random.randint(1, 3)
            region_id = random.randint(1, 3)
            time_id = random.choice(time_ids)
            quantity = random.randint(1, 10)
            base_price = {1: 30000, 2: 3000, 3: 8000, 4: 5000, 5: 500}[product_id]
            amount = quantity * base_price * random.uniform(0.9, 1.1)
            sales_facts.append((product_id, customer_id, staff_id, region_id, time_id, quantity, round(amount, 2)))
        
        cursor.executemany('INSERT INTO sales_fact (product_id, customer_id, staff_id, region_id, time_id, quantity, amount) VALUES (?, ?, ?, ?, ?, ?, ?)', sales_facts)

        self.conn.commit()
        print("數據生成完畢。")
    
    def _normalize_date_format(self, date_str):
        """
        將各種日期格式標準化為 YYYY-MM-DD 格式
        支援: YYYY/MM/DD, YYYY-MM-DD, YYYY/MM, YYYY-MM
        """
        if not date_str:
            return date_str
            
        import re
        
        # 如果已經是 YYYY-MM-DD 格式，直接返回
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
        # 處理 YYYY/MM/DD 格式
        match = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
            
        # 處理 YYYY-MM-DD 格式（但分隔符可能不同）
        match = re.match(r'^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})$', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
            
        # 處理 YYYY/MM 或 YYYY-MM 格式（只有年月）
        match = re.match(r'^(\d{4})[-\/](\d{1,2})$', date_str)
        if match:
            year, month = match.groups()
            return f"{year}-{int(month):02d}-01"  # 預設為該月第一天
            
        return date_str  # 如果無法解析，返回原字串

    def _convert_numpy_types(self, obj):
        """轉換 NumPy 數據類型為 Python 原生類型，確保 JSON 序列化"""
        if hasattr(obj, 'item'):  # NumPy 類型
            return obj.item()
        elif isinstance(obj, (list, tuple)):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        else:
            return obj

    def execute_query(self, query, params=()):
        """通用查詢執行器，返回Pandas DataFrame。"""
        try:
            result = pd.read_sql_query(query, self.conn, params=params)
            return result
        except Exception as e:
            # 如果查詢失敗，返回空的 DataFrame
            print(f"查詢執行錯誤: {e}")
            return pd.DataFrame()

    def get_period_comparison(self, current_start, current_end, last_start, last_end):
        """執行期間比較的SQL查詢 (類似規格書 Page 3 範例)。"""
        # 標準化日期格式
        current_start = self._normalize_date_format(current_start)
        current_end = self._normalize_date_format(current_end)
        last_start = self._normalize_date_format(last_start)
        last_end = self._normalize_date_format(last_end)
        
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END), 0) AS current_period_sales,
                COALESCE(SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END), 0) AS last_period_sales
            FROM sales_fact f 
            JOIN dim_time t ON f.time_id = t.time_id
        """
        result = self.execute_query(query, (current_start, current_end, last_start, last_end))
        
        # 檢查是否有數據
        if result.empty or (result['current_period_sales'].iloc[0] == 0 and result['last_period_sales'].iloc[0] == 0):
            # 檢查時間範圍是否有數據
            check_query = """
                SELECT COUNT(*) as data_count 
                FROM sales_fact f 
                JOIN dim_time t ON f.time_id = t.time_id 
                WHERE (t.date BETWEEN ? AND ?) OR (t.date BETWEEN ? AND ?)
            """
            check_result = self.execute_query(check_query, (current_start, current_end, last_start, last_end))
            if check_result['data_count'].iloc[0] == 0:
                raise ValueError(f"指定時間範圍內無銷售數據: {current_start} ~ {current_end} 或 {last_start} ~ {last_end}")
        
        return result

    def get_driver_analysis(self, current_start, current_end, last_start, last_end, dimension='product'):
        """執行貢獻度分析的SQL查詢 (類似規格書 Page 3 範例)。"""
        # 標準化日期格式
        current_start = self._normalize_date_format(current_start)
        current_end = self._normalize_date_format(current_end)
        last_start = self._normalize_date_format(last_start)
        last_end = self._normalize_date_format(last_end)
        
        dim_map = {
            'product': {'table': 'dim_product', 'id': 'product_id', 'name': 'product_name'},
            'staff': {'table': 'dim_staff', 'id': 'staff_id', 'name': 'staff_name'},
            'customer': {'table': 'dim_customer', 'id': 'customer_id', 'name': 'customer_name'},
            'region': {'table': 'dim_region', 'id': 'region_id', 'name': 'region_name'}
        }
        if dimension not in dim_map: 
            raise ValueError("無效的分析維度")
        
        d = dim_map[dimension]
        query = f"""
            SELECT d.{d['name']} AS "分析維度",
                   COALESCE(SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END), 0) AS "本期銷售額",
                   COALESCE(SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END), 0) AS "前期銷售額",
                   COALESCE(SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END), 0) - 
                   COALESCE(SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END), 0) AS "差異"
            FROM sales_fact f
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN {d['table']} d ON f.{d['id']} = d.{d['id']}
            GROUP BY d.{d['name']}
            HAVING ABS("差異") > 0
            ORDER BY ABS("差異") DESC
        """
        params = (current_start, current_end, last_start, last_end, current_start, current_end, last_start, last_end)
        result = self.execute_query(query, params)
        
        # 檢查是否有數據
        if result.empty:
            raise ValueError(f"指定時間範圍內無{dim_map[dimension]['name']}維度的銷售數據")
        
        return result

    def get_drill_down_analysis(self, current_start, current_end, last_start, last_end, 
                               primary_dimension, primary_value, drill_dimension):
        """執行 drill down 分析，基於主要維度的特定值進行下鑽分析"""
        # 標準化日期格式
        current_start = self._normalize_date_format(current_start)
        current_end = self._normalize_date_format(current_end)
        last_start = self._normalize_date_format(last_start)
        last_end = self._normalize_date_format(last_end)
        
        dim_map = {
            'product': {'table': 'dim_product', 'id': 'product_id', 'name': 'product_name'},
            'staff': {'table': 'dim_staff', 'id': 'staff_id', 'name': 'staff_name'},
            'customer': {'table': 'dim_customer', 'id': 'customer_id', 'name': 'customer_name'},
            'region': {'table': 'dim_region', 'id': 'region_id', 'name': 'region_name'}
        }
        
        if primary_dimension not in dim_map or drill_dimension not in dim_map:
            raise ValueError("無效的分析維度")
        
        primary_d = dim_map[primary_dimension]
        drill_d = dim_map[drill_dimension]
        
        # 構建 drill down 查詢，限制在主要維度的特定值範圍內
        query = f"""
            SELECT drill.{drill_d['name']} AS "下鑽維度",
                   SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END) AS "本期銷售額",
                   SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END) AS "前期銷售額",
                   SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END) - 
                   SUM(CASE WHEN t.date BETWEEN ? AND ? THEN f.amount ELSE 0 END) AS "差異"
            FROM sales_fact f
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN {primary_d['table']} primary_dim ON f.{primary_d['id']} = primary_dim.{primary_d['id']}
            JOIN {drill_d['table']} drill ON f.{drill_d['id']} = drill.{drill_d['id']}
            WHERE primary_dim.{primary_d['name']} = ?
            GROUP BY drill.{drill_d['name']}
            ORDER BY ABS("差異") DESC
        """
        params = (current_start, current_end, last_start, last_end, current_start, current_end, last_start, last_end, primary_value)
        return self.execute_query(query, params)

    def get_available_dimensions(self, current_dimension):
        """獲取可用的 drill down 維度列表"""
        all_dimensions = {
            'product': '產品',
            'staff': '業務員', 
            'customer': '客戶',
            'region': '地區'
        }
        
        # 移除當前使用的維度，返回可用的 drill down 維度
        available = {k: v for k, v in all_dimensions.items() if k != current_dimension}
        return available

    def get_all_tables(self):
        """獲取所有資料表名稱"""
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = self.execute_query(query)
        # 確保返回的是 Python 原生類型
        return [str(name) for name in result['name'].tolist()]

    def get_table_schema(self, table_name):
        """獲取指定資料表的結構"""
        query = f"PRAGMA table_info({table_name})"
        result = self.execute_query(query)
        
        # 轉換數據為可序列化的格式
        records = result.to_dict('records')
        serializable_records = self._convert_numpy_types(records)
        
        # 創建新的 DataFrame 以避免修改原始數據
        import pandas as pd
        return pd.DataFrame(serializable_records)

    def get_table_data(self, table_name, page=1, limit=10):
        """獲取指定資料表的數據，支援分頁"""
        offset = (page - 1) * limit
        
        # 獲取總記錄數
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        total_result = self.execute_query(count_query)
        total_count = int(total_result['total'].iloc[0])
        
        # 獲取分頁數據
        data_query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        data_result = self.execute_query(data_query)
        
        # 轉換數據為可序列化的格式
        records = data_result.to_dict('records')
        serializable_records = self._convert_numpy_types(records)
        
        return {
            'data': serializable_records,
            'columns': data_result.columns.tolist(),
            'total_count': total_count,
            'current_page': page,
            'total_pages': (total_count + limit - 1) // limit
        }

    def execute_custom_sql(self, sql_query):
        """執行自定義SQL查詢"""
        try:
            if not sql_query or sql_query.strip() == '':
                return {
                    'success': False,
                    'error': 'SQL 查詢不能為空'
                }
            
            result = self.execute_query(sql_query)
            
            # 檢查結果是否為空
            if result is None or result.empty:
                return {
                    'success': True,
                    'data': [],
                    'columns': [],
                    'row_count': 0
                }
            
            # 轉換數據為可序列化的格式
            records = result.to_dict('records')
            serializable_records = self._convert_numpy_types(records)
            
            return {
                'success': True,
                'data': serializable_records,
                'columns': result.columns.tolist(),
                'row_count': len(result)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_quarter_data(self, year, quarter):
        """根據年份和季度獲取銷售數據"""
        query = """
            SELECT 
                COALESCE(SUM(f.amount), 0) AS total_sales,
                COUNT(*) AS transaction_count,
                COALESCE(AVG(f.amount), 0) AS avg_transaction
            FROM sales_fact f
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year = ? AND t.quarter = ?
        """
        result = self.execute_query(query, (year, quarter))
        
        if result.empty or result['total_sales'].iloc[0] == 0:
            raise ValueError(f"{year}年第{quarter}季度無銷售數據")
        
        return result

    def get_quarter_comparison(self, current_year, current_quarter, compare_year, compare_quarter):
        """比較兩個季度的銷售數據"""
        query = """
            SELECT 
                t.year,
                t.quarter,
                COALESCE(SUM(f.amount), 0) AS total_sales,
                COUNT(*) AS transaction_count
            FROM sales_fact f
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE (t.year = ? AND t.quarter = ?) OR (t.year = ? AND t.quarter = ?)
            GROUP BY t.year, t.quarter
            ORDER BY t.year, t.quarter
        """
        result = self.execute_query(query, (current_year, current_quarter, compare_year, compare_quarter))
        
        if result.empty:
            raise ValueError(f"指定季度範圍內無銷售數據")
        
        return result

    def get_quarter_driver_analysis(self, year, quarter, dimension='product'):
        """獲取指定季度的貢獻度分析"""
        dim_map = {
            'product': {'table': 'dim_product', 'id': 'product_id', 'name': 'product_name'},
            'staff': {'table': 'dim_staff', 'id': 'staff_id', 'name': 'staff_name'},
            'customer': {'table': 'dim_customer', 'id': 'customer_id', 'name': 'customer_name'},
            'region': {'table': 'dim_region', 'id': 'region_id', 'name': 'region_name'}
        }
        
        if dimension not in dim_map:
            raise ValueError("無效的分析維度")
        
        d = dim_map[dimension]
        query = f"""
            SELECT 
                d.{d['name']} AS "分析維度",
                COALESCE(SUM(f.amount), 0) AS "季度銷售額",
                COUNT(*) AS "交易次數",
                COALESCE(AVG(f.amount), 0) AS "平均交易金額"
            FROM sales_fact f
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN {d['table']} d ON f.{d['id']} = d.{d['id']}
            WHERE t.year = ? AND t.quarter = ?
            GROUP BY d.{d['name']}
            HAVING "季度銷售額" > 0
            ORDER BY "季度銷售額" DESC
        """
        
        result = self.execute_query(query, (year, quarter))
        
        if result.empty:
            raise ValueError(f"{year}年第{quarter}季度無{dim_map[dimension]['name']}維度的銷售數據")
        
        return result 