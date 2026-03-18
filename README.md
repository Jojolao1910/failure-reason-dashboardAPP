# 📊 Failure Reason Dashboard - v2.0

Sistema web para visualização e análise de dados de failure reasons por e-commerce, com suporte a upload de arquivos Excel/CSV e filtros avançados.

## ✨ Principais Melhorias 

- ✅ **Dados automáticos**: Data e aeroporto agora vêm da planilha (não precisam ser inseridos manualmente)
- ✅ **Cálculo inteligente**: Quantidade e percentual calculados automaticamente por failure reason e e-commerce
- ✅ **Mapeamento de e-commerce**: Nomes completos mapeados para abreviações (MELI, AE, TEMU, SHOPEE, AMAZON)
- ✅ **67.299 registros processados**: Suporta grandes volumes de dados
- ✅ **Filtros dinâmicos**: Aeroporto, E-Commerce, Failure Reason
- ✅ **Top 3 Problemas**: Visualização dos principais problemas
- ✅ **Gráficos interativos**: Charts.js para visualização de dados

## 🛠️ Stack Tecnológico

| Componente | Tecnologia |
|-----------|-----------|
| **Backend** | Flask 3.0.0 + SQLite |
| **Frontend** | JavaScript Vanilla + TailwindCSS (CDN) |
| **Gráficos** | Chart.js 4.4.0 |
| **Processamento** | Pandas + OpenPyXL |

## 📁 Estrutura do Projeto

```
failure-reason-dashboard-app/
├── backend/
│   ├── app.py                    # API Flask
│   ├── db.py                     # Banco de dados SQLite
│   ├── file_processor.py         # Processamento de arquivos
│   ├── failure_reasons.db        # Banco de dados (com dados de teste)
│   └── uploads/                  # Pasta para arquivos enviados
├── frontend/
│   ├── templates/
│   │   └── index.html            # Interface web
│   └── static/
│       └── app.js                # JavaScript da aplicação
├── requirements.txt              # Dependências Python
└── README.md                     # Este arquivo
```

## 🚀 Como Usar

### 1. Instalação

```bash
# Descompactar o ZIP
unzip failure-reason-dashboard-app-v2.zip
cd failure-reason-dashboard-app

# Instalar dependências
pip install -r requirements.txt
# ou com sudo
sudo pip3 install Flask Flask-CORS pandas openpyxl python-dateutil
```

### 2. Iniciar o Servidor

```bash
cd backend
python3 app.py
```

O servidor estará disponível em: **http://localhost:5033**

### 3. Usar a Aplicação

#### **Aba Dashboard**
- Visualize os dados já importados
- Aplique filtros por Aeroporto, E-Commerce e Failure Reason
- Veja o Top 3 de problemas
- Analise gráficos interativos
- Consulte a tabela completa de dados

#### **Aba Upload**
- Envie um novo arquivo CSV ou Excel
- O sistema processará automaticamente
- Data e Aeroporto são extraídos do arquivo
- Quantidade e percentual são calculados automaticamente

## 📋 Formato Esperado do Arquivo

O arquivo deve conter as seguintes colunas:

| Coluna | Descrição | Exemplo |
|--------|-----------|---------|
| Órgão | Órgão responsável | RFB, MAPA |
| Remessa | Número único da remessa | 888001322029290 |
| Data Ocorrência | Data do evento | 24/11/2025 |
| Ocorrência/Failure Reason | Descrição do problema | Dados incorretos/incompletos |
| Airport | Código do aeroporto | VCP, GRU |
| Status CSAT | Status CSAT | Aprovado, Reprovado |
| Status Siscomex | Status Siscomex | Liberado, Bloqueado |
| E-Commerce | Nome da plataforma | MERCADO LIBRE, ALIBABA.COM SINGAPORE E-COMMERCE PRIVATE LIMITED, ELEMENTARY INNOVATION PTE. LTD, SHPS TECNOLOGIA E SERVICOS LTDA., AMAZON |

### Formatos Suportados
- ✓ CSV (com separador `;`)
- ✓ Excel (.xlsx, .xls)

## 🎯 Funcionalidades

### Dashboard
- **Top 3 Problemas**: Mostra os 3 principais failure reasons
- **Filtros Avançados**: Filtre por aeroporto, e-commerce e failure reason
- **Gráficos Interativos**: Visualize distribuição de failure reasons e e-commerce
- **Tabela Completa**: Veja todos os dados com quantidade e percentual
- **Informações do Upload**: Data início/fim e total de registros

### Upload
- **Suporte a múltiplos formatos**: CSV e Excel
- **Processamento automático**: Extrai data e aeroporto do arquivo
- **Cálculo automático**: Quantidade e percentual por failure reason
- **Validação de dados**: Remove registros incompletos
- **Feedback em tempo real**: Mensagens de sucesso/erro

## 🔧 APIs Disponíveis

### GET `/api/dashboard`
Retorna dados do dashboard com filtros opcionais.

**Parâmetros:**
- `airport` (opcional): Filtrar por aeroporto
- `ecommerce` (opcional): Filtrar por e-commerce
- `failure_reason` (opcional): Filtrar por failure reason

**Resposta:**
```json
{
  "success": true,
  "upload_info": {...},
  "top_failures": [...],
  "summary_by_ecommerce": [...],
  "all_data": [...]
}
```

### GET `/api/filters`
Retorna opções disponíveis para filtros.

**Resposta:**
```json
{
  "success": true,
  "filters": {
    "airports": ["VCP", "GRU"],
    "ecommerce": [{"name": "...", "abbr": "..."}],
    "failure_reasons": [...]
  }
}
```

### GET `/api/ecommerce-mapping`
Retorna mapeamento de e-commerce.

**Resposta:**
```json
{
  "success": true,
  "mapping": {
    "MERCADO LIBRE": "MELI",
    "ALIBABA.COM SINGAPORE E-COMMERCE PRIVATE LIMITED": "AE",
    ...
  }
}
```

### POST `/api/upload`
Faz upload de novo arquivo.

**Parâmetros (multipart/form-data):**
- `file`: Arquivo CSV ou Excel

**Resposta:**
```json
{
  "success": true,
  "message": "67299 registros importados com sucesso",
  "upload_id": 1,
  "records_count": 67299
}
```

## 📊 Dados de Teste

- **Aeroportos**: VCP (Viracopos), GRU (Guarulhos)
- **E-commerce**: MELI, AE, TEMU, SHOPEE, AMAZON
- **Failure Reasons**: 38 tipos diferentes

## 🔍 Exemplo de Uso

1. **Abra o navegador**: http://localhost:5033
2. **Veja o Dashboard**: Dados já carregados
3. **Aplique filtros**: Selecione aeroporto, e-commerce ou failure reason
4. **Clique em "Aplicar Filtros"**: Os dados serão atualizados
5. **Analise os gráficos**: Veja a distribuição dos dados
6. **Faça upload**: Vá para a aba "Upload de Dados" e envie um novo arquivo

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'flask'"
```bash
sudo pip3 install Flask Flask-CORS pandas openpyxl python-dateutil
```

### Erro: "Port 5033 already in use"
```bash
# Matar processo na porta 5033
lsof -i :5033
kill -9 <PID>
```

### Erro ao fazer upload
- Verifique se o arquivo tem o formato correto
- Certifique-se de que todas as colunas obrigatórias estão presentes
- Tente com o arquivo de teste fornecido

## 📄 Licença

Este projeto é fornecido como está para fins de análise de dados.

---

**Versão**: 2.0  
**Data**: 03/02/2026  
**Status**: ✅ Funcionando
