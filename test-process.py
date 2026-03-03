import os
import sys
from dotenv import load_dotenv, dotenv_values

# 加载 .env
load_dotenv()

# 确保项目目录在 sys.path
project_dir = os.path.dirname(__file__)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# 导入 PDFProcessor
try:
    from pdfProcessor import PDFProcessor
except Exception as e:
    parent = os.path.dirname(project_dir)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    from pdfProcessor import PDFProcessor

# 直接读取 .env 文件内容（作为备选方案）
def read_env_file(filepath):
    """直接读取 .env 文件，返回字典"""
    env_dict = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_dict[key] = value
    except Exception as e:
        print(f"Error reading .env file: {e}")
    return env_dict

# 从 .env 中读取 API Keys（5个独立的 API Key）
api_keys = []

# 先尝试使用 dotenv_values（更可靠）
env_path = os.path.join(project_dir, '.env')
env_config = dotenv_values(env_path)

# 如果 dotenv_values 失败，使用直接读取方式
if not env_config:
    env_config = read_env_file(env_path)

print(f"Found env config keys: {list(env_config.keys())}\n")

# API_KEY 是必须的
api_key = env_config.get("API_KEY", "").strip().strip('"').strip("'")
if api_key:
    api_keys.append(api_key)
    print(f"✓ Loaded API_KEY: {api_key[:20]}...")

# API_KEY_2 到 API_KEY_5
for i in range(2, 6):
    key_name = f"API_KEY_{i}"
    api_key = env_config.get(key_name, "").strip().strip('"').strip("'")
    if api_key:
        api_keys.append(api_key)
        print(f"✓ Loaded {key_name}: {api_key[:20]}...")
    else:
        print(f"✗ {key_name} not found")

# 检验 API Key
if not api_keys:
    print("\nERROR: 未检测到任何 API_KEY，请先在 .env 中配置。")
    sys.exit(1)

print(f"\n已成功加载 {len(api_keys)} 个 API Key\n")

# 指定要处理的本地 PDF 文件夹
pdf_dir = r"E:/Py_Projects/MAterial/download_papers-main/download_papers-main/pdf_hydrogel"
results_dir = pdf_dir
os.makedirs(results_dir, exist_ok=True)

# 获取 BASE_URL
base_url = env_config.get("BASE_URL", "").strip().strip('"').strip("'")

# 创建处理器，传入 API Key 列表
processor = PDFProcessor(
    pdf_folder_name=pdf_dir,
    result_folder_name=results_dir,
    result_json_name="hydrogel_electrolytes",
    material=None,
    api_keys=api_keys,
    base_url=base_url,
    max_workers=len(api_keys)  # 线程数等于 API Key 数量（最多5个）
)

# 加载已有结果
processor.load_existing_results()

# 运行处理
print("开始处理 PDF（目录）：", pdf_dir)
print("处理中间结果将保存到:", results_dir)
print(f"使用 {len(api_keys)} 个 API Key 并行处理\n")
reactions_text = processor.process_pdfs_txt()

print("\n处理完成。抽取到的反应总文本（部分）：")
print(reactions_text[:2000] if reactions_text else "No content")

print("\n完整结果已保存为：", os.path.join(results_dir, "hydrogel_electrolytes.json"))