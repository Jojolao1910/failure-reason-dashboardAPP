import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'failure_reasons.db')

def get_connection():
    """Retorna conexão com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com novo schema"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de uploads
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_records INTEGER DEFAULT 0
        )
    ''')
    
    # Tabela de dados brutos (remessas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS remessas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id INTEGER NOT NULL,
            orgao TEXT,
            remessa TEXT UNIQUE,
            data_ocorrencia DATE,
            failure_reason TEXT,
            airport TEXT,
            status_csat TEXT,
            status_siscomex TEXT,
            ecommerce TEXT,
            ecommerce_abbr TEXT,
            FOREIGN KEY (upload_id) REFERENCES uploads(id),
            UNIQUE(remessa)
        )
    ''')
    
    # Tabela de resumo agregado (quantidade e percentual por failure reason e e-commerce)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS failure_reason_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id INTEGER NOT NULL,
            airport TEXT,
            data_inicio DATE,
            data_fim DATE,
            ecommerce TEXT,
            ecommerce_abbr TEXT,
            failure_reason TEXT,
            quantidade INTEGER DEFAULT 0,
            percentual REAL DEFAULT 0.0,
            FOREIGN KEY (upload_id) REFERENCES uploads(id)
        )
    ''')
    
    # Tabela de mapeamento de e-commerce
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ecommerce_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT UNIQUE,
            abreviacao TEXT UNIQUE
        )
    ''')
    
    # Inserir mapeamento de e-commerce
    ecommerce_map = [
        ('MERCADO LIBRE', 'MELI'),
        ('ALIBABA.COM SINGAPORE E-COMMERCE PRIVATE LIMITED', 'AE'),
        ('ELEMENTARY INNOVATION PTE. LTD', 'TEMU'),
        ('SHPS TECNOLOGIA E SERVICOS LTDA.', 'SHOPEE'),
        ('AMAZON', 'AMAZON'),
    ]
    
    for nome, abbr in ecommerce_map:
        cursor.execute('''
            INSERT OR IGNORE INTO ecommerce_mapping (nome_completo, abreviacao)
            VALUES (?, ?)
        ''', (nome, abbr))
    
    conn.commit()
    conn.close()

def insert_upload(filename, records_count):
    """Insere novo upload e retorna o ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO uploads (filename, total_records)
        VALUES (?, ?)
    ''', (filename, records_count))
    
    upload_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return upload_id

def insert_remessas(upload_id, data):
    """Insere remessas no banco de dados"""
    conn = get_connection()
    cursor = conn.cursor()
    
    for row in data:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO remessas 
                (upload_id, orgao, remessa, data_ocorrencia, failure_reason, airport, 
                 status_csat, status_siscomex, ecommerce, ecommerce_abbr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                upload_id,
                row.get('orgao'),
                row.get('remessa'),
                row.get('data_ocorrencia'),
                row.get('failure_reason'),
                row.get('airport'),
                row.get('status_csat'),
                row.get('status_siscomex'),
                row.get('ecommerce'),
                row.get('ecommerce_abbr')
            ))
        except sqlite3.IntegrityError:
            # Remessa já existe, pular
            pass
    
    conn.commit()
    conn.close()

def calculate_summary(upload_id):
    """Calcula resumo agregado de failure reasons por e-commerce"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Obter data mínima e máxima do upload
    cursor.execute('''
        SELECT MIN(data_ocorrencia) as data_min, MAX(data_ocorrencia) as data_max
        FROM remessas WHERE upload_id = ?
    ''', (upload_id,))
    
    result = cursor.fetchone()
    data_inicio = result['data_min']
    data_fim = result['data_max']
    
    # Limpar resumo anterior para este upload
    cursor.execute('DELETE FROM failure_reason_summary WHERE upload_id = ?', (upload_id,))
    
    # Obter dados agrupados por airport, ecommerce e failure_reason
    cursor.execute('''
        SELECT 
            airport,
            ecommerce,
            ecommerce_abbr,
            failure_reason,
            COUNT(*) as quantidade
        FROM remessas
        WHERE upload_id = ?
        GROUP BY airport, ecommerce, ecommerce_abbr, failure_reason
    ''', (upload_id,))
    
    grouped_data = cursor.fetchall()
    
    # Calcular total por airport e ecommerce
    totals_by_airport_ecommerce = {}
    for row in grouped_data:
        key = (row['airport'], row['ecommerce'])
        if key not in totals_by_airport_ecommerce:
            totals_by_airport_ecommerce[key] = 0
        totals_by_airport_ecommerce[key] += row['quantidade']
    
    # Inserir resumo com percentuais calculados
    for row in grouped_data:
        key = (row['airport'], row['ecommerce'])
        total = totals_by_airport_ecommerce[key]
        percentual = (row['quantidade'] / total * 100) if total > 0 else 0
        
        cursor.execute('''
            INSERT INTO failure_reason_summary
            (upload_id, airport, data_inicio, data_fim, ecommerce, ecommerce_abbr, 
             failure_reason, quantidade, percentual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            upload_id,
            row['airport'],
            data_inicio,
            data_fim,
            row['ecommerce'],
            row['ecommerce_abbr'],
            row['failure_reason'],
            row['quantidade'],
            percentual
        ))
    
    conn.commit()
    conn.close()

def get_ecommerce_mapping():
    """Retorna mapeamento de e-commerce"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT nome_completo, abreviacao FROM ecommerce_mapping')
    mapping = {row['nome_completo']: row['abreviacao'] for row in cursor.fetchall()}
    
    conn.close()
    return mapping

def get_dashboard_data(upload_id, airport=None, ecommerce=None, failure_reason=None):
    """Retorna dados do dashboard com filtros aplicados"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calcular total global de remessas para o contexto filtrado (sem considerar cada item)
    # Observação: propositalmente NÃO aplicamos o filtro de failure_reason aqui,
    # para que o percentual "valores" seja relativo ao total do recorte.
    total_query = '''
        SELECT COALESCE(SUM(quantidade), 0) AS total_quantidade
        FROM failure_reason_summary
        WHERE upload_id = ?
    '''
    total_params = [upload_id]
    if airport:
        total_query += ' AND airport = ?'
        total_params.append(airport)
    if ecommerce:
        total_query += ' AND ecommerce = ?'
        total_params.append(ecommerce)
    cursor.execute(total_query, total_params)
    total_row = cursor.fetchone()
    total_quantidade = int(total_row['total_quantidade'] or 0)

    # Query base
    query = '''
        SELECT 
            airport,
            ecommerce,
            ecommerce_abbr,
            failure_reason,
            quantidade,
            percentual,
            data_inicio,
            data_fim
        FROM failure_reason_summary
        WHERE upload_id = ?
    '''
    
    params = [upload_id]
    
    # Aplicar filtros
    if airport:
        query += ' AND airport = ?'
        params.append(airport)
    
    if ecommerce:
        query += ' AND ecommerce = ?'
        params.append(ecommerce)
    
    if failure_reason:
        query += ' AND failure_reason = ?'
        params.append(failure_reason)
    
    # Ordenar por quantidade decrescente
    query += ' ORDER BY quantidade DESC'
    
    cursor.execute(query, params)
    data = [dict(row) for row in cursor.fetchall()]

    # Adicionar visão "valores": quantidade do item / total de remessas do recorte
    for row in data:
        qtd = int(row.get('quantidade') or 0)
        row['valores'] = (qtd / total_quantidade) if total_quantidade > 0 else 0.0
    
    conn.close()
    return data

def get_top_failures(upload_id, airport=None, ecommerce=None, limit=3):
    """Retorna top N failure reasons"""
    data = get_dashboard_data(upload_id, airport, ecommerce)
    return data[:limit]

def get_summary_by_ecommerce(upload_id, airport=None):
    """Retorna resumo agregado por e-commerce"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            ecommerce,
            ecommerce_abbr,
            SUM(quantidade) as total_quantidade,
            AVG(percentual) as avg_percentual
        FROM failure_reason_summary
        WHERE upload_id = ?
    '''
    
    params = [upload_id]
    
    if airport:
        query += ' AND airport = ?'
        params.append(airport)
    
    query += ' GROUP BY ecommerce, ecommerce_abbr ORDER BY total_quantidade DESC'
    
    cursor.execute(query, params)
    data = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return data

def get_filters_options(upload_id, airport=None, ecommerce=None):
    """Retorna opções disponíveis para filtros"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Aeroportos
    cursor.execute('SELECT DISTINCT airport FROM failure_reason_summary WHERE upload_id = ? ORDER BY airport', (upload_id,))
    airports = [row['airport'] for row in cursor.fetchall()]
    
    # E-commerce
    query = 'SELECT DISTINCT ecommerce, ecommerce_abbr FROM failure_reason_summary WHERE upload_id = ?'
    params = [upload_id]
    
    if airport:
        query += ' AND airport = ?'
        params.append(airport)
    
    query += ' ORDER BY ecommerce'
    cursor.execute(query, params)
    ecommerce_list = [{'name': row['ecommerce'], 'abbr': row['ecommerce_abbr']} for row in cursor.fetchall()]
    
    # Failure Reasons
    query = 'SELECT DISTINCT failure_reason FROM failure_reason_summary WHERE upload_id = ?'
    params = [upload_id]
    
    if airport:
        query += ' AND airport = ?'
        params.append(airport)
    
    if ecommerce:
        query += ' AND ecommerce = ?'
        params.append(ecommerce)
    
    query += ' ORDER BY failure_reason'
    cursor.execute(query, params)
    failure_reasons = [row['failure_reason'] for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'airports': airports,
        'ecommerce': ecommerce_list,
        'failure_reasons': failure_reasons
    }

def get_latest_upload():
    """Retorna o upload mais recente"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM uploads ORDER BY upload_date DESC LIMIT 1')
    result = cursor.fetchone()
    
    conn.close()
    
    return result['id'] if result else None

def get_upload_info(upload_id):
    """Retorna informações do upload"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            id,
            filename,
            upload_date,
            total_records,
            (SELECT MIN(data_ocorrencia) FROM remessas WHERE upload_id = ?) as data_inicio,
            (SELECT MAX(data_ocorrencia) FROM remessas WHERE upload_id = ?) as data_fim
        FROM uploads
        WHERE id = ?
    ''', (upload_id, upload_id, upload_id))
    
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def clear_imported_data():
    """Remove dados importados (uploads, remessas e resumos) preservando o schema e o ecommerce_mapping."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM failure_reason_summary')
    cursor.execute('DELETE FROM remessas')
    cursor.execute('DELETE FROM uploads')

    conn.commit()
    conn.close()
