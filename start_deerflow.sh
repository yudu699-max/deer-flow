#!/bin/bash

echo "🧹 正在清理可能残留的僵尸进程..."
taskkill //f //im node.exe 2>/dev/null
taskkill //f //im nginx.exe 2>/dev/null
# 清理可能残留的 langgraph 相关进程
taskkill //f //im python.exe 2>/dev/null 
echo "✨ 环境已清理完毕！"
echo "---------------------------------"

echo "🚀 正在启动 DeerFlow 本地服务..."

# 1. 启动 LangGraph 开发服务器 (大脑)
echo "🧠 [1/4] 启动 LangGraph 引擎 (Port 2024)..."
cd backend
# 设置环境变量确保能找到 deerflow 模块
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/packages/harness
langgraph dev --port 2024 --allow-blocking &
LANGGRAPH_PID=$!
cd ..

# 等待几秒确保大脑服务启动完毕
sleep 3

# 2. 启动后端 (Gateway)
echo "📦 [2/4] 启动后端 Gateway API (Port 8001)..."
cd backend
AUTH_TYPE=none uv run uvicorn app.gateway.app:app --host 127.0.0.1 --port 8001 --reload > gateway.log 2>&1 &
BACKEND_PID=$!
cd ..

# 3. 启动前端
echo "🎨 [3/4] 启动前端 Next.js..."
cd frontend
pnpm dev &
FRONTEND_PID=$!
cd ..

# 4. 启动 Nginx
echo "🌐 [4/4] 启动 Nginx 反向代理..."
nginx -c $(pwd)/nginx_local.conf

echo ""
echo "🎉 所有服务启动指令已发送！"
echo "👉 请访问: http://127.0.0.1:3000"
echo "==================================================="
echo "🛑 想要停止服务，请直接在键盘上按【回车键 (Enter)】"
echo "==================================================="
echo ""

# 用 read 替代容易假死的 wait
read -r 

echo -e "\n🛑 收到停止指令，正在安全关闭服务..."
# 关闭记录了 PID 的进程
kill $LANGGRAPH_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
# 强制清理 Windows 下可能残留的进程
taskkill //f //im node.exe 2>/dev/null
taskkill //f //im nginx.exe 2>/dev/null
taskkill //f //im python.exe 2>/dev/null 
echo "✅ 服务已彻底关闭。"
exit 0