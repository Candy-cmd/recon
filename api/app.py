from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os, tempfile, zipfile
import pandas as pd
from datetime import datetime
from recon import run_reconciliation

app = Flask(__name__)
app.secret_key = "secure_secret_key"
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    try:
        zip_file = request.files.get("zip_file")
        selected_date = request.form.get("selected_date")

        if not zip_file or not selected_date:
            return "Missing files or date", 400

        # Create temp directory
        output_dir = os.path.join(UPLOAD_FOLDER, "recon_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(output_dir, exist_ok=True)

        zip_path = os.path.join(output_dir, "uploaded.zip")
        zip_file.save(zip_path)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)

        # Find extracted files
        extracted_files = os.listdir(output_dir)
        excel_files = [f for f in extracted_files if f.endswith((".xls", ".xlsx", ".csv"))]

        if len(excel_files) < 3:
            return "Error: Missing one or more input files inside zip", 400

        admin_path, echeque_path, yono_path = [os.path.join(output_dir, f) for f in excel_files[:3]]

        results = run_reconciliation(admin_path, echeque_path, yono_path, selected_date, output_dir)

        preview_data = {
            name: df.head(20).to_html(classes="table table-striped table-bordered", index=False)
            for name, df in results.items()
            if isinstance(df, pd.DataFrame) and not df.empty
        }

        return render_template("result.html",
                               date=selected_date,
                               previews=preview_data,
                               excel=os.path.basename(results["Excel_File"]),
                               pdf=os.path.basename(results["PDF_File"]),
                               folder=output_dir)
    except Exception as e:
        return f"Error: {e}"

@app.route("/download/<path:folder>/<path:filename>")
def download(folder, filename):
    return send_file(os.path.join(folder, filename), as_attachment=True)

# ✅ Vercel entrypoint
def handler(event, context):
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    return DispatcherMiddleware(app, {"/": app})
