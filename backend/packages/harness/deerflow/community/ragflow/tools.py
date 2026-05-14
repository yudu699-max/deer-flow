"""
RAGFlow Search Tool - Search RAGFlow knowledge base.
"""

import json
import logging
import os
from typing import Any

import httpx
from langchain.tools import tool

from deerflow.config import get_app_config

logger = logging.getLogger(__name__)


def _query_ragflow(
    question: str,
    dataset_id: str,
    api_url: str,
    api_key: str,
    topk: int = 5,
) -> dict[str, Any]:
    """
    使用 RAGFlow 标准 API v1 进行检索。
    """
    # 尝试标准的 v1 检索接口
    url = f"{api_url.rstrip('/')}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "question": question,
        "dataset_ids": [dataset_id],  # 修正：RAGFlow 最新 API 要求使用 dataset_ids
        "page": 1,
        "page_size": topk,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            # 如果 v1 接口报 404/405，尝试兼容旧路径
            if response.status_code in (404, 405):
                old_url = f"{api_url.rstrip('/')}/retrieval/{dataset_id}/search"
                response = client.post(old_url, headers=headers, json={"question": question, "topk": topk})
            
            res_json = response.json()
            # 如果返回 code 102 提示缺少 dataset_ids，尝试兼容旧的 kb_ids 字段
            if res_json.get("code") == 102:
                payload["kb_ids"] = [dataset_id]
                del payload["dataset_ids"]
                response = client.post(url, headers=headers, json=payload)
                res_json = response.json()

            response.raise_for_status()
            return res_json
    except Exception as e:
        logger.error(f"Failed to search RAGFlow at {url}: {e}")
        return {"error": str(e)}


@tool("knowledge_search", parse_docstring=True)
def ragflow_search_tool(
    question: str,
    dataset_id: str | None = None,
    topk: int = 5,
) -> str:
    """搜索知识库以获取相关文档和信息。当你需要回答关于公司政策、流程、技术文档或任何存储在知识库中的内容时，请使用此工具。

    Args:
        question: 搜索关键词或用户的问题。
        dataset_id: 可选。要查询的具体数据集 ID。如果未提供，将使用默认配置。
        topk: 返回的相关结果数量。默认为 5。
    """
    # 彻底清理环境变量中的引号和空格
    api_url = os.getenv("RAGFLOW_API_URL", "").strip().strip("'\"").strip()
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip().strip("'\"").strip()
    
    if not dataset_id:
        dataset_id = (os.getenv("RAGFLOW_DATASET_ID") or "d1ff449c4dad11f18e8135a5d5418d1d").strip().strip("'\"").strip()

    if not api_url or not api_key:
        return "错误: 未配置 RAGFLOW_API_URL 或 RAGFLOW_API_KEY 环境变量。"

    if not dataset_id:
        return "错误: 未提供 dataset_id 且未配置默认数据集。"

    result = _query_ragflow(
        question=question,
        dataset_id=dataset_id,
        api_url=api_url,
        api_key=api_key,
        topk=topk,
    )

    res_json = result
    code = res_json.get("code", 0)
    
    # RAGFlow code 0 表示成功，非 0 表示业务逻辑错误
    if code != 0:
        error_msg = res_json.get("message", "未知业务错误")
        logger.error(f"RAGFlow business error: {error_msg}")
        return f"知识库检索返回业务错误: {error_msg}。请检查 RAGFlow 侧的模型配置或网络连接。"

    # 格式化输出
    data = res_json.get("data", {})
    # 兼容两种可能的返回结构：result['data']['chunks'] 或 result['data'] 本身就是列表
    chunks = []
    if isinstance(data, dict):
        chunks = data.get("chunks", [])
    elif isinstance(data, list):
        chunks = data

    if not chunks:
        # 调试信息：如果返回了成功但没有 chunks，打印整个 raw response 以便排查
        logger.warning(f"RAGFlow returned success but no chunks. Raw data: {result}")
        return f"在知识库中未找到关于 '{question}' 的相关匹配信息。请确认知识库 ID 是否正确，且文档已完成解析（Parsed）。"

    formatted_results = []
    for i, chunk in enumerate(chunks, 1):
        doc_name = chunk.get("document_name", "未知文档")
        content = chunk.get("content", "").strip()
        score = chunk.get("score", 0)
        
        formatted_results.append(
            f"### 来源 {i}: {doc_name} (相关度: {score:.2%})\n"
            f"{content}\n"
        )

    output = {
        "question": question,
        "dataset_id": dataset_id,
        "count": len(chunks),
        "results": "\n---\n".join(formatted_results)
    }

    return json.dumps(output, indent=2, ensure_ascii=False)
