# 🦌 DeerFlow - 2.0

> **完整项目说明请参考：[README_zh.md](README_zh.md)**

---
## 🚀 快速启动

### 1. 大语言配置模型
编辑项目根目录下的 `config.yaml`，配置你的 LLM 供应商（如 DeepSeek, OpenAI 等）：
```yaml
models:
  - name: deepseek-reasoner
    display_name: DeepSeek R1
    use: langchain_deepseek:ChatDeepSeek
    model: deepseek-reasoner
    api_key: $DEEPSEEK_API_KEY
```
### 2. 启动 DeerFlow 服务

双击 `start_deerflow.sh` 脚本即可启动 DeerFlow 服务。
由于部署在windows系统，Nginx可能出现兼容问题，所以使用Next.js 前端开发服务器的原生端口3000。
在127.0.0.1:3000 上运行

## 📚 对接 RAGFlow 知识库

DeerFlow 已集成 RAGFlow 原生工具，支持秒级检索。

### 1. 环境变量配置
在根目录的 `.env` 文件中添加以下配置（若运行报错，同步backend的.env文件配置,保持一致）：
```env
# RAGFlow API 地址 (注意替换为你的实际 IP 和端口)
RAGFLOW_API_URL="http://192.168.0.200:8083" 

# RAGFlow API Key (在 RAGFlow 控制台生成)
RAGFLOW_API_KEY="your-ragflow-api-key"

# 默认查询的知识库 ID (Dataset ID)
RAGFLOW_DATASET_ID="your-dataset-id"
```

### 2. 启用知识库工具
确保 `config.yaml` 的 `tools` 部分已注册 `knowledge_search`：
```yaml
tools:
  - name: knowledge_search
    use: deerflow.community.ragflow.tools:ragflow_search_tool
    group: web
```

### 3. 使用方法
在对话中直接询问知识库相关内容，Agent 会自动调用该工具。
- **示例**：`“根据知识库，帮我查一下产品的定价政策”`
- **进阶**：你也可以在 `http://127.0.0.1:3000/workspace/agents/new` 创建专门的知识库 Agent。

---