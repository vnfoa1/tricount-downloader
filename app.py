from flask import Flask, render_template, request, send_file, jsonify
import os
import json
from datetime import datetime
from tricount_handler import TricountHandler
import zipfile
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        tricount_key = data.get('tricount_key', '').strip()
        download_attachments = data.get('download_attachments', False)
        export_csv = data.get('export_csv', True)
        export_excel = data.get('export_excel', True)
        export_sesterce = data.get('export_sesterce', False)
        
        if not tricount_key:
            return jsonify({'error': 'Veuillez fournir une clé Tricount'}), 400
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'tricount_{timestamp}')
        os.makedirs(download_folder, exist_ok=True)
        
        handler = TricountHandler(tricount_key)
        
        tricount_data = handler.get_tricount()
        if not tricount_data:
            return jsonify({'error': 'Impossible de récupérer les données Tricount'}), 400
        
        tricount_title = tricount_data.get('title', 'Tricount')
        files_created = []
        
        if export_csv:
            csv_path = os.path.join(download_folder, f'Transactions_{tricount_title}.csv')
            handler.write_to_csv(csv_path)
            files_created.append(csv_path)
        
        if export_excel:
            excel_path = os.path.join(download_folder, f'Transactions_{tricount_title}.xlsx')
            handler.write_to_excel(excel_path)
            files_created.append(excel_path)
        
        if export_sesterce:
            sesterce_path = os.path.join(download_folder, f'Sesterce_{tricount_title}.csv')
            handler.write_to_sesterce_csv(sesterce_path)
            files_created.append(sesterce_path)
        
        if download_attachments:
            attachments_folder = os.path.join(download_folder, f'Attachments_{tricount_title}')
            handler.download_attachments(attachments_folder)
            if os.path.exists(attachments_folder):
                files_created.append(attachments_folder)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for item in files_created:
                if os.path.isfile(item):
                    zip_file.write(item, os.path.basename(item))
                elif os.path.isdir(item):
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join(os.path.basename(item), 
                                                  os.path.relpath(file_path, item))
                            zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'Tricount_{tricount_title}_{timestamp}.zip'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview', methods=['POST'])
def preview():
    try:
        data = request.get_json()
        tricount_key = data.get('tricount_key', '').strip()
        
        if not tricount_key:
            return jsonify({'error': 'Veuillez fournir une clé Tricount'}), 400
        
        handler = TricountHandler(tricount_key)
        tricount_data = handler.get_tricount()
        
        if not tricount_data:
            return jsonify({'error': 'Impossible de récupérer les données Tricount'}), 400
        
        info = {
            'title': tricount_data.get('title', 'Sans titre'),
            'currency': tricount_data.get('currency_code', 'EUR'),
            'participants': len(tricount_data.get('users', [])),
            'transactions': len(tricount_data.get('expenses', [])),
            'total_amount': sum(float(exp.get('amount', 0)) for exp in tricount_data.get('expenses', []))
        }
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
