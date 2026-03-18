import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Mapeamento de e-commerce
ECOMMERCE_MAPPING = {
    'MERCADO LIBRE': 'MELI',
    'ALIBABA.COM SINGAPORE E-COMMERCE PRIVATE LIMITED': 'AE',
    'ELEMENTARY INNOVATION PTE. LTD': 'TEMU',
    'SHPS TECNOLOGIA E SERVICOS LTDA.': 'SHOPEE',
    'AMAZON': 'AMAZON',
}

def normalize_ecommerce_name(ecommerce_name):
    if ecommerce_name is None or pd.isna(ecommerce_name):
        return ''
    return str(ecommerce_name).strip().upper()

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ecommerce_abbr(ecommerce_name):
    """Retorna abreviação do e-commerce"""
    name = normalize_ecommerce_name(ecommerce_name)
    if not name:
        return ''

    if name in ECOMMERCE_MAPPING:
        return ECOMMERCE_MAPPING[name]

    # Regras para variações comuns (evita depender do nome exato)
    if 'SHOPEE' in name or 'SHPS TECNOLOGIA' in name:
        return 'SHOPEE'
    if 'TEMU' in name or 'ELEMENTARY INNOVATION' in name:
        return 'TEMU'
    if 'MERCADO LIBRE' in name or 'MERCADO LIVRE' in name:
        return 'MELI'
    if 'ALIBABA' in name:
        return 'AE'
    if 'AMAZON' in name:
        return 'AMAZON'

    return name

def parse_date(date_str):
    """Converte string de data para formato YYYY-MM-DD"""
    if not date_str or pd.isna(date_str):
        return None
    
    try:
        # Tentar formato DD/MM/YYYY
        return pd.to_datetime(date_str, format='%d/%m/%Y').strftime('%Y-%m-%d')
    except:
        try:
            # Tentar formato YYYY-MM-DD
            return pd.to_datetime(date_str, format='%Y-%m-%d').strftime('%Y-%m-%d')
        except:
            return None

def process_csv_file(file_path):
    """Processa arquivo CSV com dados de remessas"""
    try:
        # Ler o arquivo CSV com encoding latin-1
        df = pd.read_csv(file_path, sep=';', encoding='latin-1', header=1)
        
        # Limpar nomes das colunas
        df.columns = df.columns.str.strip()
        
        print(f"Colunas encontradas: {df.columns.tolist()}")
        print(f"Total de linhas: {len(df)}")
        
        # Mapear colunas esperadas
        column_mapping = {
            'Órgão': 'orgao',
            '?rg?o': 'orgao',
            'Remessa': 'remessa',
            'Data Ocorrência': 'data_ocorrencia',
            'Data Ocorr?ncia': 'data_ocorrencia',
            'Ocorrência/Failure Reason': 'failure_reason',
            'Ocorr?ncia/Failure Reason': 'failure_reason',
            'Airport': 'airport',
            'Status CSAT': 'status_csat',
            'Status Siscomex': 'status_siscomex',
            'E-Commerce': 'ecommerce',
        }
        
        # Renomear colunas
        df_clean = df.copy()
        for old_col, new_col in column_mapping.items():
            if old_col in df_clean.columns:
                df_clean = df_clean.rename(columns={old_col: new_col})
        
        # Manter apenas colunas necessárias
        required_cols = ['orgao', 'remessa', 'data_ocorrencia', 'failure_reason', 
                        'airport', 'status_csat', 'status_siscomex', 'ecommerce']
        
        cols_to_keep = [col for col in required_cols if col in df_clean.columns]
        df_clean = df_clean[cols_to_keep]
        
        # Limpar dados
        df_clean = df_clean.dropna(subset=['remessa', 'ecommerce', 'failure_reason'], how='any')
        
        # Limpar espaços em branco
        for col in ['orgao', 'remessa', 'failure_reason', 'airport', 'status_csat', 'status_siscomex', 'ecommerce']:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()
        
        # Converter datas
        df_clean['data_ocorrencia'] = df_clean['data_ocorrencia'].apply(parse_date)
        
        # Adicionar abreviação de e-commerce
        df_clean['ecommerce_abbr'] = df_clean['ecommerce'].apply(get_ecommerce_abbr)
        
        # Converter para dicionário
        data = df_clean.to_dict('records')
        
        print(f"Registros processados: {len(data)}")
        
        return data
    
    except Exception as e:
        print(f"Erro ao processar arquivo CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def process_excel_file(file_path):
    """Processa arquivo Excel com dados de remessas"""
    try:
        # Ler o arquivo Excel
        df = pd.read_excel(file_path, sheet_name=0)
        
        # Limpar nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Verificar se a primeira linha é cabeçalho
        first_row = df.iloc[0]
        first_row_str = ' '.join(str(x).lower() for x in first_row)
        
        header_keywords = ['órgão', 'orgao', 'remessa', 'data', 'ocorrência', 'failure', 'airport', 'e-commerce', 'ecommerce']
        if any(keyword in first_row_str for keyword in header_keywords):
            # Usar primeira linha como cabeçalho
            df.columns = first_row.values
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = df.columns.astype(str).str.strip()
        
        # Mapear colunas por posição se tiver 8 colunas
        if len(df.columns) >= 8:
            column_mapping = {
                df.columns[0]: 'orgao',
                df.columns[1]: 'remessa',
                df.columns[2]: 'data_ocorrencia',
                df.columns[3]: 'failure_reason',
                df.columns[4]: 'airport',
                df.columns[5]: 'status_csat',
                df.columns[6]: 'status_siscomex',
                df.columns[7]: 'ecommerce'
            }
            df = df.rename(columns=column_mapping)
        
        # Manter apenas colunas necessárias
        required_cols = ['orgao', 'remessa', 'data_ocorrencia', 'failure_reason', 
                        'airport', 'status_csat', 'status_siscomex', 'ecommerce']
        
        cols_to_keep = [col for col in required_cols if col in df.columns]
        df = df[cols_to_keep]
        
        # Limpar dados
        df = df.dropna(subset=['remessa', 'ecommerce', 'failure_reason'], how='any')
        
        # Limpar espaços em branco
        for col in ['orgao', 'remessa', 'failure_reason', 'airport', 'status_csat', 'status_siscomex', 'ecommerce']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        # Converter datas
        df['data_ocorrencia'] = df['data_ocorrencia'].apply(parse_date)
        
        # Adicionar abreviação de e-commerce
        df['ecommerce_abbr'] = df['ecommerce'].apply(get_ecommerce_abbr)
        
        # Converter para dicionário
        data = df.to_dict('records')
        
        return data
    
    except Exception as e:
        print(f"Erro ao processar arquivo Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def save_uploaded_file(file):
    """Salva arquivo enviado e retorna caminho"""
    if not allowed_file(file.filename):
        raise ValueError("Tipo de arquivo não permitido")
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    return file_path
