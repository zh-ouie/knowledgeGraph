import os
import json
import fitz
import re
from typing import List, Optional, Dict, Any
from tqdm import tqdm
import difflib
import glob
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from util.prompts import prompt_electrolyte_extraction_cot
from util.API_KEY import GPTAPI
import base64
from io import BytesIO
from PIL import Image


class PDFProcessor:
    def __init__(self, pdf_folder_name=None,
                 result_folder_name=os.getcwd(),
                 result_json_name='gpt_results',
                 material=None,
                 api_keys=None,
                 base_url=None,
                 max_workers=3,
                 max_retries=3):
        self.pdf_folder_name = pdf_folder_name
        self.result_folder_name = result_folder_name
        self.result_json_name = result_json_name
        self.result_dict = {}
        self.processed_pdf_list = []
        self.material = material
        
        # 并行处理相关
        self.api_keys = api_keys or []  # API Key 列表
        self.base_url = base_url  # 基础 URL
        self.max_workers = max_workers  # 最大线程数
        self.max_retries = max_retries  # 最大重试次数
        self.lock = threading.Lock()  # 用于线程安全地访问 result_dict

    def load_existing_results(self):
        """加载已有的处理结果"""
        result_path = os.path.join(self.result_folder_name, f"{self.result_json_name}.json")
        if os.path.exists(result_path):
            try:
                with open(result_path, 'r', encoding='utf-8') as file:
                    self.result_dict = json.load(file)
                self.processed_pdf_list = list(self.result_dict.keys())
                print(f'Successfully Loaded existing results: {len(self.processed_pdf_list)} files processed')
            except Exception as e:
                print(f'Error loading existing results: {e}')
        else:
            print(f"Result JSON does not exist at {result_path}")

    def get_pdf_files(self, directory: str = None):
        """返回目录下的所有 pdf 文件名（不含路径）"""
        directory = directory or self.pdf_folder_name
        if directory is None:
            raise ValueError("pdf folder not specified (self.pdf_folder_name is None)")
        pdf_files = glob.glob(os.path.join(directory, '*.pdf'))
        return [os.path.basename(file) for file in pdf_files]

    def check_pdf_existence(self, target_pdf_name: str, pdf_name_list: List[str], 
                           similarity_threshold: float = 0.9) -> bool:
        """判断 target_pdf_name 是否在 pdf_name_list 中"""
        for pdf_name in pdf_name_list:
            similarity = difflib.SequenceMatcher(None, target_pdf_name, pdf_name).ratio()
            if similarity > similarity_threshold:
                return True
        return False

    def read_data_from_json(self, filename: str):
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_data_as_json(self, filename: str, data):
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

    def pdf_to_long_string(self, pdf_path, remove_references=True):
        document = fitz.open(pdf_path)
        text = ''
        for page_num in range(len(document)):
            page = document.load_page(page_num)
            text += page.get_text()
        document.close()
        if remove_references:
            text = self.remove_references_section(text)
        return text

    def remove_references_section(self, text, keyword="REFERENCES"):
        keyword_pos = text.upper().rfind(keyword)
        if keyword_pos != -1:
            text_filtered_reference = text[:keyword_pos].strip()
        else:
            text_filtered_reference = text
        return text_filtered_reference

    def replace_zeros_in_reactants_and_products(self, text):
        def replacer(match):
            return match.group(0).replace("0", "'")
        pattern = r"(Reactants: .*|Products: .*)"
        return re.sub(pattern, replacer, text)

    def process_single_pdf(self, pdf_path, api_key_index):
        """处理单个 PDF 文件，包含重试机制"""
        pdf_name = pdf_path.replace('.pdf', '')
        
        # 检查是否已处理
        if pdf_name in self.processed_pdf_list:
            print(f'Skipping {pdf_name} (already processed)')
            return
        
        # 获取当前线程的 API Key
        if self.api_keys:
            api_key = self.api_keys[api_key_index % len(self.api_keys)]
        else:
            api_key = None
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 读取 PDF 文本
                cleaned_text = self.pdf_to_long_string(
                    os.path.join(self.pdf_folder_name, pdf_path)
                )
                total_length = len(cleaned_text)
                print(f'Processing: {pdf_name}, TXT Length: {total_length} (Attempt {attempt + 1}/{self.max_retries})')
                
                # 检查长度限制
                if total_length > 200000:
                    print(f'{pdf_name} Exceed maximum length, skip ...')
                    return
                
                # 初始化 LLM（使用指定的 API Key）
                llm = GPTAPI(
                    api_key=api_key,
                    base_url=self.base_url,
                    temperature=0.0
                )
                
                # 调用 LLM 进行抽取
                prompt_reaction_extract = prompt_electrolyte_extraction_cot
                ans_reaction = llm.answer_wo_vision(prompt_reaction_extract, cleaned_text)
                
                # 保存结果（线程安全）
                with self.lock:
                    self.result_dict[pdf_name] = {
                        "llm_raw": ans_reaction
                    }
                    # 立即保存到 JSON 文件
                    self.save_data_as_json(
                        os.path.join(self.result_folder_name, f"{self.result_json_name}.json"),
                        self.result_dict
                    )
                    # 更新已处理列表
                    self.processed_pdf_list.append(pdf_name)
                
                print(f"Saved result for '{pdf_name}'")
                return  # 成功则退出重试循环
                
            except Exception as e:
                print(f"Error processing {pdf_name} (Attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    # 等待后重试
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"Failed to process {pdf_name} after {self.max_retries} attempts")

    def process_pdfs_txt(self):
        """并行处理所有 PDF 文件"""
        pdf_file_list = self.get_pdf_files(self.pdf_folder_name)
        pdf_name_list = [pdf.split('.pdf')[0] for pdf in pdf_file_list]

        # 获取待处理的文件列表（排除已处理的）
        pdf_name_to_process = [
            title for title in pdf_name_list
            if title not in self.processed_pdf_list
        ]
        pdf_file_to_process = [pdf_name + '.pdf' for pdf_name in pdf_name_to_process]

        print(f'Total number of titles: {len(pdf_name_list)}, '
              f'{len(self.processed_pdf_list)} have been processed, '
              f'{len(pdf_name_to_process)} are planned to be processed')

        if len(pdf_file_to_process) == 0:
            print("All PDF files have been processed!")
            reactions_txt = ''
            for key, value in self.result_dict.items():
                reactions = value.get("llm_raw", "")
                reactions_txt += ('\n\n' + (reactions or ""))
            return reactions_txt

        os.makedirs(self.result_folder_name, exist_ok=True)
        
        # 如果有 API Key，使用并行处理；否则使用串行处理
        if self.api_keys:
            self._process_pdfs_parallel(pdf_file_to_process)
        else:
            self._process_pdfs_sequential(pdf_file_to_process)

        reactions_txt = ''
        for key, value in self.result_dict.items():
            reactions = value.get("llm_raw", "")
            reactions_txt += ('\n\n' + (reactions or ""))
        
        return reactions_txt

    def _process_pdfs_parallel(self, pdf_file_list):
        """并行处理 PDF 文件"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for idx, pdf_file in enumerate(pdf_file_list):
                future = executor.submit(self.process_single_pdf, pdf_file, idx)
                futures.append(future)
            
            # 等待所有任务完成
            for future in tqdm(futures, total=len(futures)):
                future.result()

    def _process_pdfs_sequential(self, pdf_file_list):
        """串行处理 PDF 文件（当没有 API Key 时）"""
        for idx, pdf_file in enumerate(tqdm(pdf_file_list)):
            self.process_single_pdf(pdf_file, idx)
