import logging
import os
import sys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))
from config import SECRET_KEY, DEBUG, MAX_CONTENT_LENGTH, CORS_ORIGINS
from routes.academic import academic_bp
from routes.affairs import affairs_bp
from routes.growth import growth_bp
from routes.upload_route import upload_bp

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"),
    static_url_path="",
)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})

# 注册蓝图
from routes.academic import academic_bp
from routes.affairs import affairs_bp
from routes.growth import growth_bp
from routes.upload_route import upload_bp

# 统一 Agent 路由接口
from flask import Blueprint, request, jsonify
from services.ai_service import chat_completion

agent_bp = Blueprint("agent", __name__)

@agent_bp.route("/api/agent/chat", methods=["POST"])
def agent_chat():
    """统一 Agent 对话接口（自动路由）"""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    intent = data.get("intent", "affairs")
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    # 知识库检索补充上下文
    try:
        from services.kb_service import search_knowledge
        kb_results = search_knowledge(message, top_k=3)
        kb_context = "\n".join(r.get("content", "") for r in kb_results)
    except Exception:
        kb_context = ""

    system_prompt = "你是智链校园的AI助手。请根据知识库内容回答问题。\n"
    if kb_context:
        system_prompt += f"\n【参考资料】\n{kb_context}"

    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-10:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
            messages.append(item)
    messages.append({"role": "user", "content": message})

    result = chat_completion(messages, temperature=0.5)
    return jsonify({
        "result": result,
        "agent_type": intent,
        "status": "completed",
        "latency_ms": 0,
    })

app.register_blueprint(academic_bp)
app.register_blueprint(affairs_bp)
app.register_blueprint(growth_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(agent_bp)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "name": "智校通 API", "version": "1.0.0"})


@app.errorhandler(404)
def not_found(e):
    from flask import request as req
    if req.path.startswith("/api/"):
        return jsonify({"error": "接口不存在"}), 404
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(413)
def request_too_large(e):
    return jsonify({"error": "上传文件过大，请控制在 16MB 以内"}), 413


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "服务器内部错误，请稍后重试"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
