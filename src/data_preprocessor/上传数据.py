import os
import sys
from pathlib import Path
import oss2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cpi_calculator.config import settings


auth = oss2.Auth(settings.ACCESS_KEY, settings.ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, settings.OSS['ENDPOINT'], settings.OSS['BUCKET'])

# 本地文件路径
base_path = Path(__file__).resolve().parent.parent.parent / 'data'
filelist = [ 'products.csv', 'categories.csv', 'price.csv']  # 需要上传的文件列表
for file in filelist:
    local_file = os.path.join(base_path, file)  # 本地文件路径
    oss_key = f'{file}'  # OSS 中的路径
    # 上传文件
    bucket.put_object_from_file(oss_key, local_file)
    print(f"已上传至 OSS：oss://{settings.OSS['BUCKET']}/{oss_key}")
