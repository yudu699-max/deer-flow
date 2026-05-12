import requests
import json
 
def test_ragflow_connection():
    url = "http://192.168.0.127:8083/api/v1/datasets"
    headers = {
        "Authorization": "Bearer ragflow-Ee2hYlHhmctHABfFRJnvby5fzfLRQr6nfq84qCEtnsQ",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("✅ RAGFlow连接成功！")
            print("可用知识库:", json.dumps(response.json(), indent=2))
        else:
            print("❌ 连接失败，状态码:", response.status_code)
    except Exception as e:
        print("❌ 连接异常:", str(e))
 
if __name__ == "__main__":
    test_ragflow_connection()