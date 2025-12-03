import os
import csv
import io
import json # New import
from werkzeug.utils import secure_filename # New import
from cs50 import SQL
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file
from PIL import Image # New import for PDF conversion

# Import helper functions
from helpers import generate_certificate # New import

# Configure application
app = Flask(__name__)
app.config["SECRET_KEY"] = "a_super_secret_key_that_is_long_and_random" # Change for production
app.config['UPLOAD_FOLDER_TEMPLATES'] = 'static/templates'
app.config['UPLOAD_FOLDER_CERTS'] = 'static/certs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Ensure the database file exists before connecting
if not os.path.exists("certs.db"):
    open("certs.db", "w").close()

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///certs.db")

@app.route("/")
def index():
    """Show homepage"""
    return render_template("index.html")

@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Upload CSV or add participants"""
    if request.method == "POST":
        # Check which form was submitted
        if request.form.get("submit_button") == "upload_csv":
            # --- CSV Upload Logic ---
            if 'csvfile' not in request.files:
                flash("No file part in the request.", "danger")
                return redirect(request.url)
            
            file = request.files['csvfile']
            
            if file.filename == '':
                flash("No selected file.", "warning")
                return redirect(request.url)

            if file and file.filename.endswith('.csv'):
                try:
                    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                    csv_reader = csv.reader(stream)
                    
                    header = [h.strip().lower() for h in next(csv_reader)] # Get and clean header
                    
                    # Define standard fields and their indices
                    standard_fields = {
                        "name": None, "email": None, "event": None, "position": None, "date": None
                    }
                    custom_field_headers = []

                    for i, h in enumerate(header):
                        if h in standard_fields:
                            standard_fields[h] = i
                        else:
                            custom_field_headers.append((h, i)) # Store custom header name and its index

                    if standard_fields["name"] is None:
                        flash("CSV must contain 'name' column.", "danger")
                        return redirect(request.url)

                    count = 0
                    for row in csv_reader:
                        if not row: continue # Skip empty rows

                        name = row[standard_fields["name"]] if standard_fields["name"] is not None else ""
                        email = row[standard_fields["email"]] if standard_fields["email"] is not None else ""
                        event = row[standard_fields["event"]] if standard_fields["event"] is not None else ""
                        position = row[standard_fields["position"]] if standard_fields["position"] is not None else ""
                        date = row[standard_fields["date"]] if standard_fields["date"] is not None else ""

                        # Collect custom fields for this row
                        custom_fields_data = {}
                        for custom_header, index in custom_field_headers:
                            if index < len(row): # Ensure row has this column
                                custom_fields_data[custom_header] = row[index]
                        
                        db.execute(
                            "INSERT INTO participants (name, email, event, position, date, custom_fields) VALUES (?, ?, ?, ?, ?, ?)",
                            name, email, event, position, date, json.dumps(custom_fields_data)
                        )
                        count += 1
                    
                    flash(f"Successfully uploaded and inserted {count} participants from CSV (including custom fields).", "success")
                except json.JSONDecodeError:
                    flash("Error parsing custom fields from CSV. Ensure data is valid JSON if applicable.", "danger")
                except Exception as e:
                    flash(f"An error occurred while processing the CSV file: {e}", "danger")
                
                return redirect(url_for('upload'))

            else:
                flash("Invalid file type. Please upload a .csv file.", "danger")
                return redirect(request.url)

        elif request.form.get("submit_button") == "add_manual":
            # --- Manual Entry Logic ---
            name = request.form.get("name")
            email = request.form.get("email")
            event = request.form.get("event")
            position = request.form.get("position")
            date = request.form.get("date")

            if not name:
                flash("Name is required.", "danger")
                return redirect(request.url)

            # Collect custom fields from dynamic inputs
            custom_field_keys = request.form.getlist("custom_field_keys[]")
            custom_field_values = request.form.getlist("custom_field_values[]")
            
            custom_fields_data = {}
            for i in range(len(custom_field_keys)):
                key = custom_field_keys[i].strip()
                value = custom_field_values[i].strip()
                if key and value: # Only add if both key and value are non-empty
                    custom_fields_data[key] = value

            try:
                db.execute(
                    "INSERT INTO participants (name, email, event, position, date, custom_fields) VALUES (?, ?, ?, ?, ?, ?)",
                    name, email, event, position, date, json.dumps(custom_fields_data)
                )
                flash(f"Successfully added participant: {name} (with custom fields).", "success")
            except Exception as e:
                flash(f"An error occurred while adding the participant: {e}", "danger")
            
            return redirect(url_for('upload'))

    # GET request
    return render_template("upload.html")

@app.route("/templates", methods=["GET", "POST"])
def templates():
    """Manage certificate templates"""
    if request.method == "POST":
        # Check if the post request has the file part
        if 'template_image' not in request.files:
            flash("No template image file part", "danger")
            return redirect(request.url)
        
        file = request.files['template_image']
        template_name = request.form.get("template_name")
        fields_config_str = request.form.get("fields_config")

        if file.filename == '':
            flash("No selected file for template image", "danger")
            return redirect(request.url)
        
        if not template_name:
            flash("Template name is required", "danger")
            return redirect(request.url)

        # Validate file type and save
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename = secure_filename(template_name + os.path.splitext(file.filename)[1])
            filepath = os.path.join(app.config['UPLOAD_FOLDER_TEMPLATES'], filename)
            file.save(filepath)

            try:
                # Validate JSON for fields_config
                fields_config_json = json.loads(fields_config_str)
            except json.JSONDecodeError:
                flash("Invalid JSON for Fields Configuration. Please check the syntax.", "danger")
                return redirect(request.url)
            
            # Store template details in DB
            try:
                db.execute(
                    "INSERT INTO templates (name, file_path, fields_config) VALUES (?, ?, ?)",
                    template_name, filepath, json.dumps(fields_config_json)
                )
                flash(f"Template '{template_name}' added successfully!", "success")
            except Exception as e:
                flash(f"Error saving template to database: {e}", "danger")
            
            return redirect(url_for('templates'))
        else:
            flash("Invalid template image file type. Only PNG, JPG, JPEG are allowed.", "danger")
            return redirect(request.url)

    # GET request: Display existing templates and a form to add new ones
    existing_templates = db.execute("SELECT * FROM templates")
    return render_template("templates.html", templates=existing_templates)

@app.route("/delete_templates", methods=["POST"])
def delete_templates():
    """Delete selected templates"""
    template_ids = request.form.getlist("template_ids")
    if not template_ids:
        flash("No templates selected for deletion.", "warning")
        return redirect(url_for('templates'))
    
    deleted_count = 0
    errors = []

    for t_id in template_ids:
        try:
            # Check if any certificates use this template
            usage_count = db.execute("SELECT COUNT(*) as count FROM certificates WHERE template_id = ?", t_id)[0]["count"]
            if usage_count > 0:
                template_name = db.execute("SELECT name FROM templates WHERE id = ?", t_id)[0]["name"]
                errors.append(f"Cannot delete template '{template_name}' because {usage_count} certificates are using it. Please delete those certificates first.")
                continue

            # Get file path to delete the image
            template_info = db.execute("SELECT file_path FROM templates WHERE id = ?", t_id)
            if template_info:
                file_path = template_info[0]["file_path"]
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete from database
                db.execute("DELETE FROM templates WHERE id = ?", t_id)
                deleted_count += 1

        except Exception as e:
            errors.append(f"Error deleting template ID {t_id}: {e}")
            
    if deleted_count > 0:
        flash(f"Successfully deleted {deleted_count} templates.", "success")
    for error in errors:
        flash(error, "danger")
    
    return redirect(url_for('templates'))

@app.route("/edit_template/<int:template_id>", methods=["GET", "POST"])
def edit_template(template_id):
    """Edit an existing template's configuration"""
    template = db.execute("SELECT * FROM templates WHERE id = ?", template_id)
    if not template:
        flash("Template not found.", "danger")
        return redirect(url_for('templates'))
    
    template = template[0] # Get the first (and only) row

    if request.method == "POST":
        template_name = request.form.get("template_name")
        fields_config_str = request.form.get("fields_config")
        file = request.files.get('template_image') # Use .get to avoid KeyError if no file uploaded

        if not template_name:
            flash("Template name is required.", "danger")
            return redirect(url_for('edit_template', template_id=template_id))

        try:
            # Validate JSON for fields_config
            fields_config_json = json.loads(fields_config_str)
        except json.JSONDecodeError:
            flash("Invalid JSON for Fields Configuration. Please check the syntax.", "danger")
            return redirect(url_for('edit_template', template_id=template_id))

        new_filepath = template["file_path"] # Default to existing path

        # Handle new image upload if provided
        if file and file.filename != '':
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Delete old image if it's different and exists
                if os.path.exists(template["file_path"]):
                    os.remove(template["file_path"])
                
                filename = secure_filename(template_name + os.path.splitext(file.filename)[1])
                new_filepath = os.path.join(app.config['UPLOAD_FOLDER_TEMPLATES'], filename)
                file.save(new_filepath)
            else:
                flash("Invalid new template image file type. Only PNG, JPG, JPEG are allowed.", "danger")
                return redirect(url_for('edit_template', template_id=template_id))
        
        try:
            db.execute(
                "UPDATE templates SET name = ?, file_path = ?, fields_config = ? WHERE id = ?",
                template_name, new_filepath, json.dumps(fields_config_json), template_id
            )
            flash(f"Template '{template_name}' updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating template: {e}", "danger")
        
        return redirect(url_for('templates'))
        
    else: # GET request
        # Pass the template data, including formatted JSON string, to the template
        template["fields_config_pretty"] = json.dumps(json.loads(template["fields_config"]), indent=4)
        return render_template("edit_template.html", template=template)

@app.route("/generate", methods=["GET", "POST"])
def generate():
    """Generate certificates for selected participants and template."""
    if request.method == "POST":
        selected_participant_ids = request.form.getlist("participant_ids")
        template_id = request.form.get("template_id")

        if not selected_participant_ids or not template_id:
            flash("Please select at least one participant and a template.", "danger")
            return redirect(url_for('generate'))

        template = db.execute("SELECT * FROM templates WHERE id = ?", template_id)[0]
        participants = db.execute("SELECT * FROM participants WHERE id IN (" + ",".join("?" for _ in selected_participant_ids) + ")", *selected_participant_ids)

        generated_count = 0
        for participant in participants:
            # Convert participant data to dict as generate_certificate expects dict
            participant_dict = dict(participant)
            
            # Call the helper function
            generated_path = generate_certificate(participant_dict, template)

            if generated_path:
                try:
                    db.execute(
                        "INSERT INTO certificates (participant_id, template_id, generated_file_path) VALUES (?, ?, ?)",
                        participant_dict["id"], template["id"], generated_path
                    )
                    generated_count += 1
                except Exception as e:
                    flash(f"Error saving generated certificate for {participant_dict['name']}: {e}", "warning")
            else:
                flash(f"Failed to generate certificate for {participant_dict['name']}.", "warning")
        
        flash(f"Successfully generated {generated_count} certificates.", "success")
        return redirect(url_for('certificates'))

    else: # GET request for /generate
        all_participants = db.execute("SELECT * FROM participants")
        all_templates = db.execute("SELECT * FROM templates")
        return render_template("generate.html", participants=all_participants, templates=all_templates)


@app.route("/certificates")
def certificates():
    """Show generated certificates"""
    # Fetch all generated certificates with participant and template info
    certs = db.execute("""
        SELECT 
            c.id, p.name AS participant_name, t.name AS template_name, c.generated_file_path, c.created_at
        FROM certificates c
        JOIN participants p ON c.participant_id = p.id
        JOIN templates t ON c.template_id = t.id
        ORDER BY c.created_at DESC
    """)
    return render_template("certificates.html", certificates=certs)

@app.route("/participants")
def participants():
    """Show and manage participants"""
    all_participants_raw = db.execute("SELECT * FROM participants ORDER BY name")
    
    # Process custom_fields from JSON string (if any)
    all_participants = []
    for p in all_participants_raw:
        participant_dict = dict(p) # Convert Row to dict
        if not participant_dict.get("custom_fields"):
            participant_dict["custom_fields"] = "{}" # Ensure it's an empty JSON string if no custom fields
        all_participants.append(participant_dict)

    return render_template("participants.html", participants=all_participants)

@app.template_filter('from_json')
def from_json_filter(json_string):
    """Jinja2 filter to parse a JSON string"""
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return {} # Return empty dict on error


@app.route("/delete_participants", methods=["POST"])
def delete_participants():
    """Delete selected participants and their associated certificates"""
    participant_ids = request.form.getlist("participant_ids")
    if not participant_ids:
        flash("No participants selected for deletion.", "warning")
        return redirect(url_for('participants'))
    
    deleted_participants_count = 0
    deleted_certificates_count = 0
    errors = []

    for p_id in participant_ids:
        try:
            # Get all certificates associated with this participant
            associated_certs = db.execute("SELECT id, generated_file_path FROM certificates WHERE participant_id = ?", p_id)
            
            for cert in associated_certs:
                cert_id = cert["id"]
                file_path_db = cert["generated_file_path"]
                
                filename = os.path.basename(file_path_db)
                full_png_path = os.path.join(app.config['UPLOAD_FOLDER_CERTS'], filename)
                
                if os.path.exists(full_png_path):
                    os.remove(full_png_path)
                
                # Delete certificate record
                db.execute("DELETE FROM certificates WHERE id = ?", cert_id)
                deleted_certificates_count += 1
            
            # Finally, delete the participant record
            db.execute("DELETE FROM participants WHERE id = ?", p_id)
            deleted_participants_count += 1

        except Exception as e:
            errors.append(f"Error deleting participant ID {p_id} and/or associated certificates: {e}")
            
    if deleted_participants_count > 0:
        flash(f"Successfully deleted {deleted_participants_count} participants and {deleted_certificates_count} associated certificates.", "success")
    if errors:
        for error in errors:
            flash(error, "danger")
    
    return redirect(url_for('participants'))

@app.route("/download/<path:filename>")
def download_file(filename):
    """Serve generated certificate files for download"""
    return send_from_directory(app.config['UPLOAD_FOLDER_CERTS'], filename, as_attachment=True)

@app.route("/download_pdf/<path:filename>")
def download_pdf(filename):
    """Convert PNG to PDF and serve for download"""
    png_path = os.path.join(app.config['UPLOAD_FOLDER_CERTS'], filename)
    pdf_filename = os.path.splitext(filename)[0] + ".pdf"

    if not os.path.exists(png_path):
        flash("File not found.", "danger")
        return redirect(url_for('certificates'))

    try:
        image = Image.open(png_path)
        # Convert to RGB if it's RGBA (to avoid issues with PDF saving)
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # Save to a memory buffer
        pdf_buffer = io.BytesIO()
        image.save(pdf_buffer, "PDF", resolution=100.0)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        flash(f"An error occurred while converting to PDF: {e}", "danger")
        return redirect(url_for('certificates'))

@app.route("/delete_certificates", methods=["POST"])
def delete_certificates():
    """Delete selected certificates"""
    certificate_ids = request.form.getlist("certificate_ids")
    if not certificate_ids:
        flash("No certificates selected for deletion.", "warning")
        return redirect(url_for('certificates'))
    
    deleted_count = 0
    errors = []

    for cert_id in certificate_ids:
        try:
            cert = db.execute("SELECT generated_file_path FROM certificates WHERE id = ?", cert_id)
            if cert:
                file_path_db = cert[0]["generated_file_path"]
                # Extract filename from the stored path (e.g., static/certs/filename.png)
                # The stored path might be like 'static/certs/...' or just 'certs/...'
                # os.path.basename handles both cases correctly
                filename = os.path.basename(file_path_db)
                full_png_path = os.path.join(app.config['UPLOAD_FOLDER_CERTS'], filename)
                
                # Delete PNG file
                if os.path.exists(full_png_path):
                    os.remove(full_png_path)
                
                # Delete record from database
                db.execute("DELETE FROM certificates WHERE id = ?", cert_id)
                deleted_count += 1
            else:
                errors.append(f"Certificate with ID {cert_id} not found in database.")
        except Exception as e:
            errors.append(f"Error deleting certificate ID {cert_id}: {e}")
            
    if deleted_count > 0:
        flash(f"Successfully deleted {deleted_count} certificates.", "success")
    if errors:
        for error in errors:
            flash(error, "danger")
    
    return redirect(url_for('certificates'))

if __name__ == '__main__':
    # Create database tables if they don't exist
    # This is a simple way to initialize the DB. For more complex apps, you'd use migrations.
    with app.app_context():
        db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                fields_config TEXT
            );
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                event TEXT NOT NULL,
                position TEXT,
                date TEXT NOT NULL
            );
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                generated_file_path TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (participant_id) REFERENCES participants(id),
                FOREIGN KEY (template_id) REFERENCES templates(id)
            );
        """)
        
        # --- Database Migration: Add custom_fields to participants table ---
        try:
            # Attempt to select the column to see if it exists
            db.execute("SELECT custom_fields FROM participants LIMIT 1")
        except RuntimeError: # cs50.SQL raises RuntimeError for SQL errors like "no such column"
            db.execute("ALTER TABLE participants ADD COLUMN custom_fields TEXT DEFAULT '{}'")
            print("Added 'custom_fields' column to 'participants' table.")
        # --- End Database Migration ---

    app.run(debug=True, port=5001)
