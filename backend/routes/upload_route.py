from flask import Blueprint, request, jsonify
import os

upload_bp = Blueprint("upload", __name__)

UPLOAD_SECRET = "zhilian2026"

@upload_bp.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    """临时上传端点 - 用完后请删除此文件"""
    secret = request.headers.get("X-Upload-Secret", "")
    if secret != UPLOAD_SECRET:
        return jsonify({"error": "未授权"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "无数据"}), 400

    filepath = data.get("filepath", "")
    content = data.get("content", "")

    if not filepath or content is None:
        return jsonify({"error": "缺少 filepath 或 content"}), 400

    if not filepath.startswith("/opt/zhilian-campus/"):
        return jsonify({"error": "不允许的路径"}), 403

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"status": "ok", "written": filepath})
