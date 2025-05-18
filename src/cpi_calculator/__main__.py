# -*- coding: utf-8 -*-
"""
CPI 计算器主程序 - 实现数据加载、计算、可视化全流程
"""
import calculator
from datetime import date

if __name__ == '__main__':
    start_date = date(2025, 5, 17)
    end_date = date(2028, 5, 15)
    calculator.run(start_date, end_date)
