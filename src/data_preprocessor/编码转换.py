import os
from pathlib import Path

base_path = Path(__file__).resolve().parent.parent.parent / 'raw'
data_path = Path(__file__).resolve().parent.parent.parent / 'data'
file = 'products.csv' # 需要转换的文件
print(file)
with open(os.path.join(base_path, file), 'r', encoding='gbk') as f_in, open(os.path.join(data_path, file), 'w', encoding='utf-8-sig') as f_out:
    for line in f_in:
        f_out.write(line)
print(f"已转换为 UTF-8-SIG 格式：{os.path.join(data_path, file)}")

