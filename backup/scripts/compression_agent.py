#!/usr/bin/env python3
"""
Hermes Memory Compression Agent
分层记忆系统的压缩模块

职责:
- 读取原始记忆内容
- 调用 LLM 进行压缩（保留 40-50%）
- 按语义拆分超限文件
- 写入压缩结果到目标域
- 处理失败重试逻辑

压缩规则 (严格遵守):
  ✅ 一定保留:
     - 完整指令 (文件名、路径、参数、命令)
     - 关键决策点
     - 时间/日期等事实
     - 数字/配置等精确值
     - 代码/命令的完整内容
  ❌ 可以删除:
     - 语气词 ("那个","然后呢","我觉得")
     - 重复表达
     - 废话铺垫 ("我们先来讨论一下")
     - 人类情绪表达
  📐 压缩目标:
     - 保留 40-50%，压缩 40-50%
     - 宁可多留，不要少留
     - 大任务优先按语义拆分，不依赖过度压缩
"""

import json
import os
import sys
import time
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# ============ 配置 ============
HERMES_MEMORIES = Path.home() / ".hermes" / "memories"
SCRIPTS_DIR = Path.home() / ".hermes" / "scripts"
L2_MAX_KB = 20  # KB

# LLM 配置 (通过环境变量或默认值)
LLM_API_URL = os.environ.get("MINIMAX_API_URL", "https://api.minimax.chat/v1/text/chatcompletion_v2")
LLM_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
LLM_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-Text-01")

# 重试配置
MAX_RETRIES = 2
RETRY_DELAY_SEC = 300  # 5 分钟

# ============ LLM 调用 ============

def call_llm(prompt: str, system: str = "") -> Optional[str]:
    """调用 LLM 进行压缩"""
    import httpx
    
    if not LLM_API_KEY:
        print("⚠️ 未配置 LLM_API_KEY，跳过 LLM 调用")
        return None
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3  # 低温度保证一致性
    }
    
    try:
        response = httpx.post(LLM_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        return None

# ============ 压缩逻辑 ============

COMPRESSION_SYSTEM = """你是一个记忆压缩助手。你的任务是将原始记忆压缩到 40-50%，同时严格遵守以下规则：

【一定保留】
- 完整指令：文件名、路径、参数、命令必须逐字保留
- 关键决策点及其理由
- 时间、日期等事实
- 数字、配置等精确值
- 代码、命令的完整内容
- 用户明确表达的需求和目标

【可以删除】
- 语气词：那个、然后呢、我觉得、可能、大概
- 重复表达（相同内容说多次）
- 废话铺垫：我们先来、其实呢、说起来
- 人类情绪表达：开心、不爽、惊讶
- 连接词导致的冗余

【输出格式】
直接输出压缩后的内容，不要加任何解释或标记。

【重要原则】
- 宁可多留，不要少留
- 保留语义完整性
- 大任务按阶段/话题拆分"""

COMPRESSION_USER_TEMPLATE = """请将以下记忆内容压缩到 40-50%，保留精华和所有关键信息：

---

{content}

---

压缩后的内容："""


def compress_content(content: str) -> Optional[str]:
    """调用 LLM 压缩单段内容"""
    if len(content) < 100:
        # 太短的内容不需要压缩
        return content
    
    # 估算压缩后长度
    target_len = int(len(content) * 0.45)
    
    prompt = COMPRESSION_USER_TEMPLATE.format(content=content)
    result = call_llm(prompt, COMPRESSION_SYSTEM)
    
    if result:
        # 简单验证：压缩后不应超过原始的 60%
        if len(result) <= len(content) * 0.6:
            return result
        else:
            print(f"⚠️ 压缩结果超出预期长度限制，进行简单截断")
            return result[:int(len(content) * 0.5)]
    
    return None


def split_by_semantic(content: str, max_size_kb: float = L2_MAX_KB) -> list:
    """
    按语义将内容拆分成多个块
    优先按段落/话题拆分，其次按字数硬切
    """
    # 粗略估算：1KB ≈ 500 中文字符
    max_chars = int(max_size_kb * 500)
    
    if len(content) <= max_chars:
        return [content]
    
    # 尝试按段落拆分
    paragraphs = content.split("\n\n")
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # 如果单个段落就超过限制，按句子拆分
            if len(para) > max_chars:
                sentences = para.split("。")
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_chars:
                        current_chunk += sent + "。"
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent + "。"
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def compress_and_write(raw_file: Path, domain: str) -> Tuple[bool, str]:
    """
    压缩单个 raw 文件并写入目标域
    
    Args:
        raw_file: .dirty/ 目录下的原始文件
        domain: 目标 L1 域 (skills/user/projects 等)
    
    Returns:
        (成功标志, 消息)
    """
    print(f"\n📝 处理: {raw_file.name} → {domain}/")
    
    # 读取原始内容
    with open(raw_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_size = len(content)
    print(f"   原始大小: {original_size} 字符 ({round(original_size/1024, 2)} KB)")
    
    # 检查是否需要拆分
    raw_size_kb = original_size / 1024
    
    if raw_size_kb > L2_MAX_KB:
        print(f"   📦 文件超限 ({raw_size_kb:.2f} KB > {L2_MAX_KB} KB)，先拆分")
        chunks = split_by_semantic(content, L2_MAX_KB)
        print(f"   拆分后: {len(chunks)} 个块")
    else:
        chunks = [content]
    
    # 压缩每个块
    compressed_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"   压缩块 {i+1}/{len(chunks)}...")
        
        # 检查是否太短不需要压缩
        if len(chunk) < 200:
            compressed_chunks.append(chunk)
            continue
        
        compressed = compress_content(chunk)
        if compressed:
            compressed_chunks.append(compressed)
        else:
            # 压缩失败，使用原始内容
            print(f"   ⚠️ 块 {i+1} 压缩失败，使用原始内容")
            compressed_chunks.append(chunk)
        
        # LLM 调用间隔
        time.sleep(1)
    
    # 生成目标文件名
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = raw_file.stem  # 去掉 .md
    
    # 写入目标域
    domain_path = HERMES_MEMORIES / domain
    domain_path.mkdir(exist_ok=True)
    
    if len(compressed_chunks) == 1:
        # 单块，直接写入
        output_file = domain_path / f"{base_name}-{timestamp}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(compressed_chunks[0])
        print(f"   ✅ 已写入: {output_file.name}")
    else:
        # 多块，写入多个文件
        for i, chunk in enumerate(compressed_chunks):
            output_file = domain_path / f"{base_name}-{timestamp}-p{i+1}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(chunk)
            print(f"   ✅ 已写入: {output_file.name}")
    
    # 移动原始文件到 .archive/
    archive_dir = HERMES_MEMORIES / ".archive"
    archive_dir.mkdir(exist_ok=True)
    
    archive_path = archive_dir / raw_file.name
    # 如果已存在，加时间戳
    if archive_path.exists():
        archive_path = archive_dir / f"{base_name}-{timestamp}-raw.md"
    
    shutil.move(str(raw_file), str(archive_path))
    print(f"   📦 已归档: {archive_path.name}")
    
    # 更新 index (通过调用 supervisor)
    try:
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "memory_supervisor.py"), "rebuild"],
            capture_output=True,
            text=True,
            timeout=30
        )
    except Exception as e:
        print(f"   ⚠️ index 更新失败: {e}")
    
    final_size = sum(len(c) for c in compressed_chunks)
    ratio = (1 - final_size / original_size) * 100 if original_size > 0 else 0
    print(f"   📊 压缩率: {ratio:.1f}% (原始 {original_size} → 最终 {final_size})")
    
    return True, f"成功处理 {raw_file.name}"


def process_dirty_with_retry(raw_file: Path, domain: str) -> Tuple[bool, str]:
    """处理单个 dirty 文件，带重试"""
    for attempt in range(MAX_RETRIES + 1):
        success, msg = compress_and_write(raw_file, domain)
        if success:
            return True, msg
        
        if attempt < MAX_RETRIES:
            print(f"   🔄 重试 ({attempt + 1}/{MAX_RETRIES})，等待 {RETRY_DELAY_SEC} 秒...")
            time.sleep(RETRY_DELAY_SEC)
    
    # 标记为压缩失败
    failed_marker = raw_file.with_suffix(".md.failed")
    shutil.move(str(raw_file), str(failed_marker))
    print(f"   ❌ 压缩失败，标记为 .failed")
    return False, f"压缩失败: {raw_file.name}"


# ============ 主入口 ============

def main():
    """主入口"""
    if len(sys.argv) < 3:
        print("用法: python compression_agent.py <file_path> <domain>")
        print("  例: python compression_agent.py .dirty/session-123.md skills")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    domain = sys.argv[2]
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    success, msg = process_dirty_with_retry(file_path, domain)
    
    if success:
        print(f"\n✅ {msg}")
        sys.exit(0)
    else:
        print(f"\n❌ {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
