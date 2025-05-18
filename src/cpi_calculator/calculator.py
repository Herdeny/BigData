import os
from datetime import date
from pathlib import Path

import clickhouse_driver
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings


class CPICalculator:
    def __init__(self, db_config):
        self.db_config = db_config
        self.clickhouse_client = self._connect_clickhouse()
        self.sqlalchemy_engine = self._connect_sqlalchemy()
        self.Session = sessionmaker(bind=self.sqlalchemy_engine)

        # 初始化产品和类别信息
        self.categories = self._load_categories()
        self.products = self._load_products()

    def _connect_clickhouse(self):
        """连接到 ClickHouse 数据库"""
        return clickhouse_driver.Client(
            host=self.db_config['HOST'],
            port=self.db_config['PORT'],
            user=self.db_config['USER'],
            password=self.db_config['PASSWORD']
        )

    def _connect_sqlalchemy(self):
        """连接 SQLAlchemy 引擎"""
        return create_engine(self.db_config['SQLALCHEMY_DATABASE_URI'])

    def _execute_clickhouse_query(self, query):
        """执行 ClickHouse 查询"""
        return self.clickhouse_client.execute(query)

    def _load_categories(self):
        """从 ClickHouse 加载所有类别信息"""
        query = "SELECT category_id, parent, weight FROM categories"
        result = self._execute_clickhouse_query(query)
        return pd.DataFrame(result, columns=["category_id", "parent", "weight"])

    def _load_products(self):
        """从 ClickHouse 加载产品信息"""
        query = "SELECT product_id, category_id FROM products"
        result = self._execute_clickhouse_query(query)
        return pd.DataFrame(result, columns=["product_id", "category_id"])

    def _load_prices_for_dates(self, date_tuple):
        """加载指定日期范围的产品价格"""
        date_list = "', '".join(str(d) for d in date_tuple)
        query = f"""
            SELECT product_id, price, toDate(date) AS date
            FROM prices
            WHERE date IN ('{date_list}')
        """
        result = self._execute_clickhouse_query(query)
        return pd.DataFrame(result, columns=["product_id", "price", "date"])

    def compute_cpi(self, start_date, end_date):
        """使用 ClickHouse SQL 计算指定时间区间 CPI"""
        sql_query = f"""
        WITH
        leaf_categories AS (
            SELECT category_id, weight
            FROM categories
            WHERE category_id NOT IN (SELECT parent FROM categories WHERE parent != -1)
        ),
        price_data AS (
            SELECT
                product_id,
                MAXIf(price, toDate(date) = toDate('{start_date}')) AS base_price,
                MAXIf(price, toDate(date) = toDate('{end_date}')) AS report_price
            FROM prices
            WHERE date IN ('{start_date}', '{end_date}')
            GROUP BY product_id
        ),
        category_cpi AS (
            SELECT
                p.category_id,
                EXP(avg(log(pd.report_price / pd.base_price))) AS price_index
            FROM products p
            JOIN price_data pd ON p.product_id = pd.product_id
            JOIN leaf_categories lc ON p.category_id = lc.category_id
            WHERE pd.base_price > 0 AND pd.report_price IS NOT NULL
            GROUP BY p.category_id
        )
        SELECT
            SUM(cc.price_index * lc.weight) AS CPI
        FROM category_cpi cc
        JOIN leaf_categories lc ON cc.category_id = lc.category_id;
        """
        try:
            result = self._execute_clickhouse_query(sql_query)
            return result[0][0] if result else None
        except Exception as e:
            print(f"ClickHouse CPI SQL 执行失败: {e}")
            return None

    def compute_daily_cpi(self, start_date: date, end_date: date) -> pd.Series:
        """计算每日 CPI 指数"""
        leaf_categories = self.categories[
            ~self.categories['category_id'].isin(self.categories['parent'].dropna())
        ][['category_id', 'weight']]

        all_dates = pd.date_range(start_date, end_date, freq='D').date
        price_data = self._load_prices_for_dates(all_dates)

        price_pivot = price_data.pivot_table(
            index='product_id',
            columns='date',
            values='price',
            aggfunc='first'
        ).ffill(axis=1)

        base_prices = price_pivot[start_date].rename('base_price')

        merged_data = self.products.merge(
            base_prices,
            left_on='product_id',
            right_index=True
        ).merge(
            leaf_categories,
            on='category_id'
        )

        cpi_series = pd.Series(index=all_dates, dtype='float64')

        for current_date in all_dates:
            current_prices = price_pivot[current_date].rename('current_price')
            daily_data = merged_data.merge(
                current_prices,
                left_on='product_id',
                right_index=True
            )

            valid_data = daily_data[
                (daily_data['base_price'] > 0) & (daily_data['current_price'].notnull())
                ].copy()

            valid_data['price_ratio'] = valid_data['current_price'] / valid_data['base_price']
            valid_data['log_ratio'] = np.log(valid_data['price_ratio'])

            category_index = valid_data.groupby('category_id')['log_ratio'].mean().apply(np.exp)

            final_data = category_index.reset_index(name='price_index').merge(
                leaf_categories,
                on='category_id'
            )

            cpi_series[current_date] = (final_data['price_index'] * final_data['weight']).sum()

        return cpi_series.astype('float64').round(4)


def plot_cpi_trend(cpi_series: pd.Series, output_path: str = None):
    """
    绘制 CPI 趋势图，并可选地导出为图片报告。

    :param cpi_series: 时间序列形式的 CPI 指数（pd.Series, index 为日期）
    :param output_path: 可选，保存路径，支持 .png 格式（例如 'output/cpi_trend.png'）
    """
    plt.figure(figsize=(15, 6))
    cpi_series.plot(
        kind='line',
        title='Daily Consumer Price Index Trend',
        xlabel='Date',
        ylabel='CPI',
        grid=True,
        color='steelblue',
        marker='o',
        markersize=4
    )
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300)
        print(f"图表已保存至: {output_path}")

    plt.show()


def run(start_date: date, end_date: date):
    try:
        data_path = Path(__file__).resolve().parent.parent.parent / 'data'
        # 1. 初始化配置
        print("CPI 计算器启动.", flush=True)

        # 2. 数据加载
        settings.from_env('prod')

        # 3. 核心计算
        calculator = CPICalculator(db_config=settings.CLICKHOUSE)
        daily_cpi = calculator.compute_daily_cpi(start_date, end_date)

        # 4. 结果输出
        print("生成可视化报告...",flush=True)
        print(daily_cpi,flush=True)
        plot_cpi_trend(daily_cpi, os.path.join(data_path, 'cpi_trend.png'))
        print("处理成功 | 可视化引擎: matplotlib",flush=True)
    except Exception as e:
        print("流程异常终止",flush=True)
        raise
