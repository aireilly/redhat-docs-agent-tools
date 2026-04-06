"""Flask application with env vars and API endpoints for testing."""
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = os.environ.get("API_PORT", "8080")
DATABASE_URL = os.environ["DATABASE_URL"]


@app.route("/api/v1/resources", methods=["GET"])
def list_resources():
    return jsonify({"resources": []})


@app.route("/api/v1/resources", methods=["POST"])
def create_resource():
    data = request.get_json()
    return jsonify(data), 201


if __name__ == "__main__":
    app.run(host=API_HOST, port=int(API_PORT))
