from flask import jsonify


def error(status, message, errors=None):
    body = {"error": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status
