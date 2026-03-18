from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(__file__))

from db import (
    init_db, insert_upload, insert_remessas, calculate_summary,
    get_dashboard_data, get_top_failures, get_summary_by_ecommerce,
    get_filters_options, get_latest_upload, get_upload_info,
    get_ecommerce_mapping, clear_imported_data
)
from file_processor import save_uploaded_file, process_csv_file, process_excel_file

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
CORS(app)

# Inicializar banco de dados
init_db()

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API para upload de arquivo"""
    try:
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Arquivo vazio'}), 400
        
        # Salvar arquivo
        file_path = save_uploaded_file(file)
        
        # Processar arquivo
        if file.filename.endswith('.csv'):
            data = process_csv_file(file_path)
        else:
            data = process_excel_file(file_path)
        
        # Inserir no banco de dados
        upload_id = insert_upload(file.filename, len(data))
        insert_remessas(upload_id, data)
        
        # Calcular resumo
        calculate_summary(upload_id)
        
        return jsonify({
            'success': True,
            'message': f'{len(data)} registros importados com sucesso',
            'upload_id': upload_id,
            'records_count': len(data)
        }), 200
    
    except Exception as e:
        print(f"Erro no upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """API para obter dados do dashboard"""
    try:
        # Obter upload_id (usar o mais recente)
        upload_id = request.args.get('upload_id')
        if not upload_id:
            upload_id = get_latest_upload()
        
        if not upload_id:
            return jsonify({'success': False, 'message': 'Nenhum upload encontrado'}), 404
        
        upload_id = int(upload_id)
        
        # Obter filtros
        airport = request.args.get('airport')
        ecommerce = request.args.get('ecommerce')
        failure_reason = request.args.get('failure_reason')
        
        # Obter dados
        all_data = get_dashboard_data(upload_id, airport, ecommerce, failure_reason)
        top_failures = get_top_failures(upload_id, airport, ecommerce, limit=3)
        summary_by_ecommerce = get_summary_by_ecommerce(upload_id, airport)
        upload_info = get_upload_info(upload_id)
        
        return jsonify({
            'success': True,
            'upload_info': upload_info,
            'top_failures': top_failures,
            'summary_by_ecommerce': summary_by_ecommerce,
            'all_data': all_data
        }), 200
    
    except Exception as e:
        print(f"Erro ao obter dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/filters', methods=['GET'])
def get_filters():
    """API para obter opções de filtros"""
    try:
        # Obter upload_id
        upload_id = request.args.get('upload_id')
        if not upload_id:
            upload_id = get_latest_upload()
        
        if not upload_id:
            return jsonify({'success': False, 'message': 'Nenhum upload encontrado'}), 404
        
        upload_id = int(upload_id)
        
        # Obter filtros aplicados
        airport = request.args.get('airport')
        ecommerce = request.args.get('ecommerce')
        
        # Obter opções
        filters_options = get_filters_options(upload_id, airport, ecommerce)
        
        return jsonify({
            'success': True,
            'filters': filters_options
        }), 200
    
    except Exception as e:
        print(f"Erro ao obter filtros: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ecommerce-mapping', methods=['GET'])
def get_ecommerce_map():
    """API para obter mapeamento de e-commerce"""
    try:
        mapping = get_ecommerce_mapping()
        return jsonify({
            'success': True,
            'mapping': mapping
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clear-data', methods=['POST'])
def clear_data():
    """API para limpar dados importados (não remove schema nem ecommerce_mapping)"""
    try:
        clear_imported_data()
        return jsonify({'success': True, 'message': 'Dados removidos com sucesso'}), 200
    except Exception as e:
        print(f"Erro ao limpar dados: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/upload-info', methods=['GET'])
def get_upload_details():
    """API para obter informações do upload"""
    try:
        upload_id = request.args.get('upload_id')
        if not upload_id:
            upload_id = get_latest_upload()
        
        if not upload_id:
            return jsonify({'success': False, 'message': 'Nenhum upload encontrado'}), 404
        
        upload_id = int(upload_id)
        info = get_upload_info(upload_id)
        
        return jsonify({
            'success': True,
            'info': info
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    """Tratador de erro 404"""
    return jsonify({'success': False, 'message': 'Rota não encontrada'}), 404

@app.errorhandler(500)
def server_error(e):
    """Tratador de erro 500"""
    return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5033, debug=True)
