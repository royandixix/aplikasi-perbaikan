from flask import Blueprint, current_app, render_template, send_from_directory

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def dashboard():
    return render_template("dashboard.html")


@main_bp.get("/processing")
def processing():
    return render_template("processing.html")


@main_bp.get("/comparison")
@main_bp.get("/pengujian")
def comparison():
    return render_template("comparison.html")


@main_bp.get("/uji-citra")
def image_test():
    return render_template("image_test.html")


@main_bp.get("/history")
def history():
    return render_template("history.html")


@main_bp.get("/symptoms")
def symptoms_page():
    return render_template("symptoms.html")


@main_bp.get("/data/<path:filename>")
def data_files(filename: str):
    """Serve artefak runtime yang disimpan di folder data project."""
    return send_from_directory(current_app.config["DATA_ROOT"], filename)
