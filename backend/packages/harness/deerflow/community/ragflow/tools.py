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
    query: str,
    dataset_id: str,
    api_url: str,
    api_key: str,
    topk: int = 5,
) -> dict[str, Any]:
    """
    Execute query against RAGFlow retrieval API.
    """
    url = f"{api_url.rstrip('/')}/retrieval/{dataset_id}/query"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "topk": topk,
        "rerank": True,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to query RAGFlow: {e}")
        return {"error": str(e)}


@tool("knowledge_search", parse_docstring=True)
def ragflow_search_tool(
    query: str,
    dataset_id: str | None = None,
    topk: int = 5,
) -> str:
    """搜索知识库以获取相关文档和信息。当你需要回答关于公司政策、流程、技术文档或任何存储在知识库中的内容时，请使用此工具。

    Args:
        query: 搜索关键词或用户的问题。
        dataset_id: 可选。要查询的具体数据集 ID。如果未提供，将使用默认配置。
        topk: 返回的相关结果数量。默认为 5。
    """
    # 优先从 .env 读取配置，兼容用户之前的设置
    api_url = os.getenv("RAGFLOW_API_URL")
    api_key = os.getenv("RAGFLOW_API_KEY")
    
    # 如果 dataset_id 为空，尝试从环境变量读取（假设用户在 .env 中也配置了）
    if not dataset_id:
        dataset_id = os.getenv("RAGFLOW_DATASET_ID") or "d1ff449c4dad11f18e8135a5d5418d1d"

    if not api_url or not api_key:
        return "错误: 未配置 RAGFLOW_API_URL 或 RAGFLOW_API_KEY 环境变量。"

    if not dataset_id:
        return "错误: 未提供 dataset_id 且未配置默认数据集。"

    result = _query_ragflow(
        query=query,
        dataset_id=dataset_id,
        api_url=api_url,
        api_key=api_key,
        topk=topk,
    )

    if "error" in result:
        return f"查询知识库失败: {result['error']}"

    # 格式化输出
    data = result.get("data", {})
    chunks = data.get("chunks", [])
    
    if not chunks:
        return "在知识库中未找到相关匹配信息。"

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
        "query": query,
        "dataset_id": dataset_id,
        "count": len(chunks),
        "results": "\n---\n".join(formatted_results)
    }

    return json.dumps(output, indent=2, ensure_ascii=False)
