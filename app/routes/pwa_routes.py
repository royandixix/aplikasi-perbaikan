from pathlib import Path

from flask import Blueprint, current_app, make_response, send_from_directory

pwa_bp = Blueprint("pwa", __name__)


@pwa_bp.get("/service-worker.js")
def service_worker():
    response = make_response(send_from_directory(
        Path(current_app.static_folder),
        "service-worker.js",
        mimetype="application/javascript",
    ))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
