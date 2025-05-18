from pathlib import Path

import pandas as pd
import os
from datetime import datetime

# 设置路径
base_path = Path(__file__).resolve().parent.parent.parent / 'raw'
data_path = Path(__file__).resolve().parent.parent.parent / 'data'
daily_price_path = 'daily_price'
products_path = 'products.csv'
categories_path = 'categories.csv'

# 读取产品和类别数据
df_products = pd.read_csv(os.path.join(base_path, products_path), dtype={'product_id': str, 'category_id': str},
                          encoding='gbk')
df_categories = pd.read_csv(os.path.join(base_path, categories_path), dtype={'category_id': str}, encoding='gbk')

# 初始化清洗结果列表
all_price_data = []

# 遍历 daily_price 目录下所有 CSV 文件
for filename in os.listdir(os.path.join(base_path,daily_price_path)):
    if filename.endswith('.csv'):
        filepath = os.path.join(base_path, daily_price_path, filename)
        print("正在清洗文件:", filepath)
        df_daily = pd.read_csv(filepath, dtype={'product_id': str, 'category_id': str}, encoding='gbk')

        # 统一日期格式
        df_daily['change_date'] = pd.to_datetime(df_daily['change_date'], errors='coerce')
        df_daily = df_daily.dropna(subset=['change_date'])

        # 保留所需字段并重命名
        df_clean = df_daily[['product_id', 'category_id', 'name', 'price', 'change_date']].copy()
        df_clean.rename(columns={'change_date': 'date'}, inplace=True)

        # 删除价格为负或缺失的数据
        df_clean = df_clean[df_clean['price'] > 0]
        df_clean = df_clean.dropna(subset=['product_id', 'category_id', 'price'])

        # 加入列表
        all_price_data.append(df_clean)

# 合并所有天的价格数据
df_all = pd.concat(all_price_data, ignore_index=True)

# 日期统一为字符串格式 yyyy-MM-dd
df_all['date'] = df_all['date'].dt.strftime('%Y-%m-%d')

# 保存为统一格式 CSV
output_path = os.path.join(data_path, 'price.csv')
df_all.to_csv(output_path, index=False, encoding='utf-8-sig')

categories = pd.read_csv(os.path.join(base_path, categories_path), encoding='gbk')
categories.fillna(-1, inplace=True)
categories['parent'] = categories['parent'].astype(int)
categories.to_csv(os.path.join(data_path, categories_path), encoding='utf-8-sig', index=False)

print(f"清洗完成，已保存到 {data_path}，共 {len(df_all)} 条记录")
