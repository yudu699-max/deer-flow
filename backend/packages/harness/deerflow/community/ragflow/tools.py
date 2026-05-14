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
    dataset_ids: list[str],  # 修改为接收 ID 列表
    api_url: str,
    api_key: str,
    topk: int = 5,
) -> dict[str, Any]:
    """
    使用 RAGFlow 官方标准 API v1 进行检索。
    """
    url = f"{api_url.rstrip('/')}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # 使用传入的 ID 列表
    payload = {
        "question": question,
        "dataset_ids": dataset_ids,
        "page": 1,
        "page_size": topk,
    }

    cross_langs = os.getenv("RAGFLOW_CROSS_LANGUAGES")
    if cross_langs:
        payload["cross_languages"] = [lang.strip() for lang in cross_langs.split(",")]

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            
            # 安全检查：如果状态码错误，拦截并报错
            if response.status_code >= 400:
                logger.error(f"RAGFlow error {response.status_code}: {response.text[:500]}")
                return {"error": f"服务器返回错误 {response.status_code}"}

            try:
                return response.json()
            except Exception:
                logger.error(f"Failed to parse RAGFlow JSON response: {response.text[:500]}")
                return {"error": "API 响应格式错误（非 JSON）"}
    except Exception as e:
        logger.error(f"Failed to search RAGFlow at {url}: {e}")
        return {"error": str(e)}


@tool("knowledge_search", parse_docstring=True)
def ragflow_search_tool(
    question: str,
    dataset_id: str | None = None,
    topk: int = 10,
) -> str:
    """搜索一个或多个知识库以获取相关文档和信息。当你需要回答关于公司政策、流程、技术文档或任何存储在知识库中的内容时，请使用此工具。

    Args:
        question: 搜索关键词或用户的问题。
        dataset_id: 可选。要查询的一个或多个数据集 ID（多个 ID 用逗号分隔）。如果未提供，将使用环境变量 RAGFLOW_DATASET_ID。
        topk: 返回的相关结果数量。默认为 10。
    """
    # 清理环境变量中的引号和空格
    api_url = os.getenv("RAGFLOW_API_URL", "").strip().strip("'\"").strip()
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip().strip("'\"").strip()
    
    # 1. 获取环境变量中的所有默认 ID，避免仅显式地传递第一个id
    env_dataset_id = os.getenv("RAGFLOW_DATASET_ID") or "b4640b664dad11f18cc1c994647531c4"
    env_ids = [id.strip().strip("'\"").strip() for id in env_dataset_id.split(",") if id.strip()]

    # 2. 如果 Agent 传了额外的 ID，将其加入列表并去重
    if dataset_id:
        param_ids = [id.strip().strip("'\"").strip() for id in dataset_id.split(",") if id.strip()]
        all_ids = list(set(env_ids + param_ids))
    else:
        all_ids = env_ids

    logger.info(f"Final Dataset IDs for search: {all_ids}")

    if not api_url or not api_key:
        return "Error: RAGFLOW_API_URL or RAGFLOW_API_KEY is not configured."

    if not all_ids:
        return "Error: No valid Dataset IDs found."

    result = _query_ragflow(
        question=question,
        dataset_ids=all_ids,
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
# 组装最终返回给 Agent 的结果对象
    output = {
        "question": question,
        "dataset_ids": all_ids,
        "count": len(chunks),
        "results": "\n---\n".join(formatted_results)
    }

    return json.dumps(output, indent=2, ensure_ascii=False)
