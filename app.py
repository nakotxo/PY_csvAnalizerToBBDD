import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from validators import validar_identificador, limpiar_y_elegir_telefono, validar_email_Regex
import uuid
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_dev")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

progress = {}

# Configuration
UPLOAD_FOLDER = 'static/uploads'
DOWNLOAD_FOLDER = 'static/downloads'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_database_connection():
    """Get database connection using environment variables"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            cursorclass=DictCursor,
            charset='utf8mb4'
        )
        return connection
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        return None

def test_database_connection():
    """Test database connection and return status"""
    try:
        connection = get_database_connection()
        if connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION() as version")
                result = cursor.fetchone()
                connection.close()
                return True, f"Connected to MariaDB {result['version']}"
        else:
            return False, "Unable to establish connection"
    except Exception as e:
        return False, f"Database error: {str(e)}"

def insert_user_meta(cursor, user_id, dni, telefono):
    """Insert or update user meta data in wp_usermeta table"""
    inserted_meta = 0
    updated_meta = 0
    try:
        logging.info(f"Inserting meta for user {user_id}, dni {dni}, telefono '{telefono}'")
        # Define default meta keys and values
        meta_keys = {
            'nickname': dni,
            'dni': dni,
            'phone': telefono,
            'old_user': '1',
            'wp_capabilities': 'a:1:{s:10:"subscriber";b:1;}',
            'wp_user_level': '0',
            'show_admin_bar_front': 'false'
        }

        # Check if user already has meta data by checking 'nickname' meta_key with DNI value
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM wp_usermeta
            WHERE user_id = %s AND meta_key = 'nickname' AND meta_value = %s
        """, (user_id, dni))
        exists = cursor.fetchone()['count'] > 0
        logging.info(f"User {user_id} exists meta: {exists}")

        if exists:
            # User has meta data, get existing meta data
            cursor.execute("SELECT meta_key, meta_value FROM wp_usermeta WHERE user_id = %s", (user_id,))
            existing_meta = {row['meta_key']: row['meta_value'] for row in cursor.fetchall()}
            logging.info(f"Existing meta for user {user_id}: {existing_meta}")

            # Update or insert meta keys
            for key, value in meta_keys.items():
                if key in existing_meta:
                    # Update phone if changed
                    if key == 'phone' and value:
                        logging.info(f"Sync phone for user {user_id}: '{existing_meta.get(key)}' → '{value}'")
                        cursor.execute("""
                            UPDATE wp_usermeta
                            SET meta_value = %s
                            WHERE user_id = %s AND meta_key = %s
                        """, (value, user_id, key))
                        updated_meta += 1
                else:
                    # Insert missing meta keys
                    logging.info(f"Inserting missing meta {key} = '{value}' for user {user_id}")
                    cursor.execute("""
                        INSERT INTO wp_usermeta (user_id, meta_key, meta_value)
                        VALUES (%s, %s, %s)
                    """, (user_id, key, value))
                    inserted_meta += 1
        else:
            # No meta data exists, insert all meta keys
            logging.info(f"Inserting all meta for new user {user_id}")
            for key, value in meta_keys.items():
                cursor.execute("""
                    INSERT INTO wp_usermeta (user_id, meta_key, meta_value)
                    VALUES (%s, %s, %s)
                """, (user_id, key, value))
                inserted_meta += len(meta_keys)
    except Exception as e:
        logging.error(f"Error in insert_user_meta for user {user_id}: {str(e)}")
    return inserted_meta, updated_meta

def insert_valid_users_to_db(valid_users):
    """Insert valid users into the wp_users table and handle wp_usermeta"""
    if not valid_users:
        return 0, 0, 0, 0, 0, 0, []

    connection = get_database_connection()
    if not connection:
        return 0, 0, 0, 0, 0, 0, ["Error: No se pudo conectar a la base de datos"]

    processed_count = 0
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    inserted_meta_total = 0
    updated_meta_total = 0
    errors = []

    try:
        with connection.cursor() as cursor:
            for user in valid_users:
                try:
                    dni = user.get('dni', '').strip()
                    email = user.get('email', '').strip()

                    # Generate a default password (in production, this should be handled differently)
                    # For now, using a placeholder password that should be changed
                    default_password = '$P$BhKKDxDIIhoOs8dO8wK4fGNqYe3GKS0'

                    # Use DNI as user_login (unique)
                    user_login = dni

                    # Generate display_name (could be improved with more data)
                    display_name = dni  # Or use name if available

                    # Check if user already exists by login (DNI should be unique)
                    cursor.execute("""
                        SELECT ID, user_email, display_name, user_status
                        FROM wp_users
                        WHERE user_login = %s
                    """, (user_login,))
                    existing_user = cursor.fetchone()

                    if existing_user:
                        user_id = existing_user['ID']
                        # Check if data has changed
                        needs_update = (
                            existing_user['user_email'] != email or
                            existing_user['display_name'] != display_name or
                            existing_user['user_status'] != 0
                        )

                        if needs_update:
                            # Update existing user only if data changed
                            sql = """
                                UPDATE wp_users
                                SET user_email = %s, display_name = %s, user_status = 0
                                WHERE ID = %s
                            """
                            result = cursor.execute(sql, (email, display_name, existing_user['ID']))
                            logging.info(f"Updated existing user {user_login} (data changed) - Rows affected: {result}")
                            updated_count += 1
                        else:
                            logging.info(f"Skipped update for user {user_login} (data unchanged)")
                            skipped_count += 1
                    else:
                        # Insert new user
                        sql = """
                            INSERT INTO wp_users (
                                user_login, user_pass, user_nicename, user_email,
                                user_registered, user_status, display_name
                            ) VALUES (%s, %s, %s, %s, NOW(), 0, %s)
                        """
                        result = cursor.execute(sql, (
                            user_login,
                            default_password,
                            user_login,  # user_nicename same as user_login
                            email,
                            display_name
                        ))
                        user_id = cursor.lastrowid
                        logging.info(f"Inserted new user {user_login} - Rows affected: {result}")
                        inserted_count += 1

                    # Handle user meta data for all processed users
                    telefono = user.get('telefono', '')
                    inserted_meta, updated_meta = insert_user_meta(cursor, user_id, dni, telefono)
                    inserted_meta_total += inserted_meta
                    updated_meta_total += updated_meta

                    processed_count += 1

                except Exception as e:
                    error_msg = f"Error insertando usuario {user.get('dni', 'desconocido')}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)

        logging.info(f"Committing transaction with {processed_count} processed users")
        connection.commit()
        logging.info("Transaction committed successfully")

    except Exception as e:
        logging.error(f"Rolling back transaction due to error: {str(e)}")
        connection.rollback()
        errors.append(f"Error en la transacción: {str(e)}")
    finally:
        connection.close()
        logging.info("Database connection closed")

    return processed_count, inserted_count, updated_count, skipped_count, inserted_meta_total, updated_meta_total, errors

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def puede_escribir_archivo(ruta):
    """Check if file can be written"""
    try:
        with open(ruta, 'a'):
            return True
    except PermissionError:
        return False

@app.route('/')
def index():
    """Main page with file upload form"""
    return render_template('index.html')

@app.route('/test-db')
def test_db():
    """Test database connection"""
    success, message = test_database_connection()
    if success:
        flash(f'✅ Conexión exitosa: {message}', 'success')
    else:
        flash(f'❌ Error de conexión: {message}', 'error')
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
            file.save(upload_path)
            
            # Process the file
            results = process_csv_file(upload_path, file_id)
            
            # Clean up uploaded file
            os.remove(upload_path)
            
            return render_template('results.html', results=results, file_id=file_id)
            
        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Tipo de archivo no permitido. Solo se aceptan archivos CSV.', 'error')
        return redirect(url_for('index'))

def process_csv_file(file_path, file_id):
    """Process CSV file and validate data"""
    try:
        logging.info(f"Starting to process CSV file: {file_path}")

        # Read CSV file
        df = pd.read_csv(file_path, sep=';', encoding='utf-8-sig')
        # Normalize column names to lowercase
        df.columns = df.columns.str.lower()
        logging.info(f"CSV loaded successfully. Total records: {len(df)}")
        logging.info(f"Columns found: {list(df.columns)}")
        if len(df) > 0:
            logging.info(f"Sample row: {df.iloc[0].to_dict()}")
        

        # Lists for valid and invalid records
        validos = []
        no_validos = []
        warnings = []

        # Process each row
        total_rows = len(df)
        for idx, fila in df.iterrows():
            if idx % 100 == 0:
                logging.info(f"Processing row {idx + 1}/{total_rows}")

            # add new column old_user
            fila['old_user'] = 1

            # Clean phone number
            raw_telefono = fila.get('telefono', '')
            logging.info(f"Raw telefono for row {idx}: '{raw_telefono}'")
            fila['telefono'] = limpiar_y_elegir_telefono(raw_telefono)
            logging.info(f"Cleaned telefono for row {idx}: '{fila['telefono']}'")
            
            # Validate DNI/NIE/CIF
            dni = str(fila.get('dni', '')).strip()
            dni_valido, motivo_dni = validar_identificador(dni)
            
            # Validate email if present using new regex function
            email_valido = True
            motivo_email = ""
            email_normalizado = ""
            email_original = ""

            from validators import validar_email_Regex
            email_valido, motivo_email, email_normalizado, email_original = validar_email_Regex(fila.get('email', ''))
            # Always update the email field with normalized/corrected version
            fila['email'] = email_normalizado

            # Determine record status
            if dni_valido:
                # DNI is valid, add to validos
                validos.append(fila.copy())
                
                # If email is invalid, also add to warnings
                if not email_valido :
                    fila_warning = fila.copy()
                    fila_warning['email_original'] = email_original
                    fila_warning['motivo_warning'] = f"Email: {motivo_email}"
                    warnings.append(fila_warning)
            else:
                # DNI is invalid, add to no_validos
                fila_con_motivo = fila.copy()
                motivos = [f"DNI: {motivo_dni}"]
                
                if not email_valido:
                    motivos.append(f"Email: {motivo_email}")
                
                fila_con_motivo['motivo_invalido'] = "; ".join(motivos)
                no_validos.append(fila_con_motivo)
        
        # Create DataFrames
        df_validos = pd.DataFrame(validos)
        df_no_validos = pd.DataFrame(no_validos)
        df_warnings = pd.DataFrame(warnings)

        # Insert valid users into database
        processed_count, inserted_count, updated_count, skipped_count, inserted_meta, updated_meta, insert_errors = insert_valid_users_to_db(validos)
        logging.info(f"Processed {processed_count} users into database (inserted: {inserted_count}, updated: {updated_count}, skipped: {skipped_count})")
        logging.info(f"Meta operations: inserted {inserted_meta}, updated {updated_meta}")
        if insert_errors:
            logging.error(f"Database insertion errors: {insert_errors}")
        
        # Generate output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        valid_filename = f"usuarios_validos_{timestamp}.csv"
        invalid_filename = f"usuarios_invalidos_{timestamp}.csv"
        warning_filename = f"usuarios_advertencias_{timestamp}.csv"

        valid_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{file_id}_{valid_filename}")
        invalid_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{file_id}_{invalid_filename}")
        warning_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{file_id}_{warning_filename}")
        
        # Save files
        if len(df_validos) > 0:
            df_validos.to_csv(valid_path, sep=';', index=False, encoding='utf-8-sig')
        
        if len(df_no_validos) > 0:
            df_no_validos.to_csv(invalid_path, sep=';', index=False, encoding='utf-8-sig')

        if len(df_warnings) > 0:
            df_warnings.to_csv(warning_path, sep=';', index=False, encoding='utf-8-sig')

        # Prepare results
        results = {
            'total_records': len(df),
            'valid_records': len(df_validos),
            'invalid_records': len(df_no_validos),
            'warning_records': len(df_warnings),
            'processed_to_db': processed_count,
            'inserted_to_db': inserted_count,
            'updated_to_db': updated_count,
            'skipped_to_db': skipped_count,
            'inserted_meta': inserted_meta,
            'updated_meta': updated_meta,
            'db_insert_errors': insert_errors,
            'valid_file': f"{file_id}_{valid_filename}" if len(df_validos) > 0 else None,
            'invalid_file': f"{file_id}_{invalid_filename}" if len(df_no_validos) > 0 else None,
            'warning_file': f"{file_id}_{warning_filename}" if len(df_warnings) > 0 else None,
            'columns': list(df.columns),
            'invalid_reasons': df_no_validos['motivo_invalido'].value_counts().to_dict() if len(df_no_validos) > 0 else {},
            'warning_reasons': df_warnings['motivo_warning'].value_counts().to_dict() if len(df_warnings) > 0 else {}
        }
        
        return results
        
    except Exception as e:
        logging.error(f"Error in process_csv_file: {str(e)}")
        raise e

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed file"""
    try:
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        flash('Error al descargar el archivo', 'error')
        return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash('El archivo es demasiado grande. Máximo 16MB permitido.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
