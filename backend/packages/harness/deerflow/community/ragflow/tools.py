import json
import logging
import os
from typing import Any
import httpx
from langchain.tools import tool

logger = logging.getLogger(__name__)
def _query_ragflow(
    question: str,
    dataset_ids: list[str], 
    api_url: str,
    api_key: str,
    topk: int = 5,
) -> dict[str, Any]:
    url = f"{api_url.rstrip('/')}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
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
            try:
                return response.json()
            except Exception:
                return {"error": "API 响应格式错误（非 JSON）"}
    except Exception as e:
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
    api_url = os.getenv("RAGFLOW_API_URL", "").strip("'\"")
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip("'\"")
    
    # 1. 获取环境变量中的所有默认 ID，避免仅显式地传递第一个id
    env_dataset_id = os.getenv("RAGFLOW_DATASET_ID")
    env_ids = [id.strip().strip("'\"").strip() for id in env_dataset_id.split(",") if id.strip()]
       
    if dataset_id:
        dataset_ids = [id.strip().strip("'\"").strip() for id in dataset_id.split(",") if id.strip()]
        all_ids = list(set(env_ids + dataset_ids))
    else:
        all_ids = env_ids

    logger.info(f"Final Dataset IDs for search: {all_ids}")

    result = _query_ragflow(
        question=question,
        dataset_ids=all_ids,
        api_url=api_url,
        api_key=api_key,
        topk=topk,
    )

    # RAGFlow 官方 API 返回结构: { "code": 0, "data": { "chunks": [...] } }
    chunks = result.get("data", {}).get("chunks", [])

    logger.info(f"RAGFlow returned {len(chunks)} chunks for query: {question[:50]}...")

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
