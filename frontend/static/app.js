// Estado global
let currentUploadId = null;
let ecommerceMapping = {};
let chartInstances = {};

let lastDashboardData = null;
let lastTopFailures = null;
let lastFiltersPayload = null;

const FAILURE_REASON_TRANSLATIONS_STORAGE_KEY = 'failure_reason_translations_v1';
let failureReasonTranslations = {};

try {
    const cached = localStorage.getItem(FAILURE_REASON_TRANSLATIONS_STORAGE_KEY);
    if (cached) {
        const parsed = JSON.parse(cached);
        if (parsed && typeof parsed === 'object') {
            failureReasonTranslations = parsed;
        }
    }
} catch (e) {
    // ignore
}

function normalizeTextForDisplay(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replaceAll('??', '�')
        .replaceAll('?º', 'º')
        .replaceAll('?ª', 'ª')
        .trim();
}

function translateFailureReason(reason) {
    const r = normalizeTextForDisplay(reason);

    const rules = [
        [/ENCAMINHAR PARA AN[ÁA]LISE ANATEL/i, 'Forwarded to ANATEL review'],
        [/AGUARDANDO LAUDO DE REPRESENTANTE DE MARCA/i, 'Awaiting brand representative report'],
        [/RETEN.*COMPROVA.*VALOR.*RCV/i, 'Held for value verification (RCV)'],
        [/DADOS INCORRETOS\/?INCOMPLETOS DO DESTINAT/i, 'Incorrect/incomplete recipient data'],
        [/VERIFICA.*F[ÍI]SICA REQUISITADA/i, 'Physical inspection requested'],
        [/MULTA ART\.?\s*703/i, 'Fine (Art. 703)'],
        [/MULTA ART\.?\s*725/i, 'Fine (Art. 725)'],
        [/CONTROLE\s+ANVISA/i, 'ANVISA control'],
        [/DESTINA.*COMERCIAL\s+PF/i, 'Commercial destination (individual)'],
        [/DESCRI.*INSUFICIENTE\/?INCOMPLETA/i, 'Insufficient/incomplete description']
    ];

    for (const [pattern, replacement] of rules) {
        if (pattern.test(r)) return replacement;
    }

    return '';
}

function getFailureReasonDisplay(reason) {
    const original = normalizeTextForDisplay(reason);
    if (!original) return '';

    const cached = failureReasonTranslations[original];
    if (cached) return cached;

    const ruleBased = translateFailureReason(original);
    return ruleBased || original;
}

function persistFailureReasonTranslations() {
    try {
        localStorage.setItem(FAILURE_REASON_TRANSLATIONS_STORAGE_KEY, JSON.stringify(failureReasonTranslations));
    } catch (e) {
        // ignore
    }
}

async function translateFailureReasonRemote(text) {
    const q = normalizeTextForDisplay(text);
    if (!q) return '';

    const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(q)}&langpair=pt|en`;
    const resp = await fetch(url);
    const json = await resp.json();
    const translated = json?.responseData?.translatedText;
    if (!translated || typeof translated !== 'string') return '';

    // Some free translators return the same source text; treat it as no-translation
    const cleaned = translated.trim();
    if (!cleaned) return '';
    if (cleaned.toLowerCase() === q.toLowerCase()) return '';
    return cleaned;
}

async function ensureFailureReasonTranslations(failureReasons) {
    if (!failureReasons || failureReasons.length === 0) return;

    const originals = [...new Set(failureReasons.map(fr => normalizeTextForDisplay(fr)).filter(Boolean))];
    const missing = originals.filter(fr => !failureReasonTranslations[fr]);
    if (missing.length === 0) return;

    for (const fr of missing) {
        const already = failureReasonTranslations[fr];
        if (already) continue;

        const local = translateFailureReason(fr);
        if (local && local !== fr && !failureReasonTranslations[fr]) {
            failureReasonTranslations[fr] = local;
            continue;
        }

        try {
            const remote = await translateFailureReasonRemote(fr);
            if (remote) {
                failureReasonTranslations[fr] = remote;
            }
        } catch (e) {
            // ignore
        }
    }

    persistFailureReasonTranslations();

    if (lastFiltersPayload) {
        renderFailureReasonFilterOptions(lastFiltersPayload);
    }
    if (lastTopFailures) {
        renderTop3(lastTopFailures);
    }
    if (lastDashboardData) {
        renderTable(lastDashboardData);
        renderCharts(lastDashboardData);
    }
}

function renderFailureReasonFilterOptions(filters) {
    const failureSelect = document.getElementById('filterFailureReason');
    const currentFailure = failureSelect.value;

    failureSelect.innerHTML = '<option value="">All</option>';
    filters.failure_reasons.forEach(fr => {
        const option = document.createElement('option');
        option.value = fr;
        option.textContent = getFailureReasonDisplay(fr);
        failureSelect.appendChild(option);
    });
    failureSelect.value = currentFailure;
}

// Inicializar aplicação
document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    setupEventListeners();
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }

    if (window.Chart) {
        Chart.defaults.font.family = "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'";
        Chart.defaults.color = '#0f172a';
    }
    loadEcommerceMapping();
    loadDashboard();
});

// Setup de navegação entre abas
function setupTabNavigation() {
    document.getElementById('tabDashboard').addEventListener('click', () => {
        showTab('dashboard');
    });
    
    document.getElementById('tabUpload').addEventListener('click', () => {
        showTab('upload');
    });
}

function showTab(tabName) {
    // Esconder todas as abas
    document.getElementById('dashboardTab').classList.add('hidden');
    document.getElementById('uploadTab').classList.add('hidden');
    
    const tabDashboardBtn = document.getElementById('tabDashboard');
    const tabUploadBtn = document.getElementById('tabUpload');

    // Reset visual
    tabDashboardBtn.classList.remove('bg-blue-50', 'text-blue-600');
    tabUploadBtn.classList.remove('bg-blue-50', 'text-blue-600');
    tabDashboardBtn.classList.add('text-gray-600');
    tabUploadBtn.classList.add('text-gray-600');
    
    // Mostrar aba selecionada
    if (tabName === 'dashboard') {
        document.getElementById('dashboardTab').classList.remove('hidden');
        tabDashboardBtn.classList.remove('text-gray-600');
        tabDashboardBtn.classList.add('bg-blue-50', 'text-blue-600');
    } else {
        document.getElementById('uploadTab').classList.remove('hidden');
        tabUploadBtn.classList.remove('text-gray-600');
        tabUploadBtn.classList.add('bg-blue-50', 'text-blue-600');
    }
}

// Setup de event listeners
function setupEventListeners() {
    document.getElementById('btnApplyFilters').addEventListener('click', loadDashboard);
    document.getElementById('uploadForm').addEventListener('submit', handleUpload);
    document.getElementById('btnClearUpload').addEventListener('click', handleClearData);
}

function clearUploadForm() {
    const form = document.getElementById('uploadForm');
    if (form) {
        form.reset();
    }

    const messageDiv = document.getElementById('uploadMessage');
    if (messageDiv) {
        messageDiv.classList.add('hidden');
        messageDiv.textContent = '';
        messageDiv.className = 'mt-6 hidden';
    }
}

async function handleClearData() {
    const confirmed = confirm('This will delete all imported data from the database (uploads/shipments/summaries). Do you want to continue?');
    if (!confirmed) return;

    try {
        showUploadMessage('Clearing data...', 'info');

        const response = await fetch('/api/clear-data', {
            method: 'POST'
        });
        const data = await response.json();

        if (!data.success) {
            showUploadMessage(`❌ ${data.message}`, 'error');
            return;
        }

        clearUploadForm();
        showUploadMessage('✅ Data cleared successfully. You can upload a new file now.', 'success');

        // Recarregar dashboard para refletir que não existem mais dados
        setTimeout(() => {
            showTab('dashboard');
            loadDashboard();
        }, 500);
    } catch (error) {
        console.error('Erro ao limpar dados:', error);
        showUploadMessage('Error clearing data', 'error');
    }
}

// Carregar mapeamento de e-commerce
async function loadEcommerceMapping() {
    try {
        const response = await fetch('/api/ecommerce-mapping');
        const data = await response.json();
        if (data.success) {
            ecommerceMapping = data.mapping;
        }
    } catch (error) {
        console.error('Erro ao carregar mapeamento de e-commerce:', error);
    }
}

// Obter abreviação de e-commerce
function getEcommerceAbbr(name) {
    return ecommerceMapping[name] || name;
}

// Carregar dashboard
async function loadDashboard() {
    try {
        // Obter filtros
        const airport = document.getElementById('filterAirport').value;
        const ecommerce = document.getElementById('filterEcommerce').value;
        const failureReason = document.getElementById('filterFailureReason').value;
        
        // Construir URL
        let url = '/api/dashboard';
        const params = new URLSearchParams();
        if (airport) params.append('airport', airport);
        if (ecommerce) params.append('ecommerce', ecommerce);
        if (failureReason) params.append('failure_reason', failureReason);
        if (params.toString()) url += '?' + params.toString();
        
        // Buscar dados
        const response = await fetch(url);
        const data = await response.json();
        
        if (!data.success) {
            showInfo('No data available. Upload a file first.', 'warning');
            return;
        }
        
        currentUploadId = data.upload_info?.id;
        
        // Atualizar info box
        if (data.upload_info) {
            const info = data.upload_info;
            showInfo(`Data from ${info.data_inicio} to ${info.data_fim} - ${info.total_records} records`);
        }
        
        // Carregar filtros
        await loadFilters();
        
        lastTopFailures = data.top_failures;
        renderTop3(data.top_failures);

        // Renderizar tabela
        lastDashboardData = data.all_data;
        renderTable(data.all_data);

        // Renderizar gráficos
        renderCharts(data.all_data);

        if (lastFiltersPayload?.failure_reasons) {
            ensureFailureReasonTranslations(lastFiltersPayload.failure_reasons);
        }
        
    } catch (error) {
        console.error('Erro ao carregar dashboard:', error);
        showInfo('Error loading data', 'error');
    }
}

// Carregar filtros
async function loadFilters() {
    try {
        const airport = document.getElementById('filterAirport').value;
        const ecommerce = document.getElementById('filterEcommerce').value;
        
        let url = '/api/filters';
        const params = new URLSearchParams();
        if (airport) params.append('airport', airport);
        if (ecommerce) params.append('ecommerce', ecommerce);
        if (params.toString()) url += '?' + params.toString();
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (!data.success) return;
        
        const filters = data.filters;
        lastFiltersPayload = filters;
        
        // Atualizar select de aeroporto
        const airportSelect = document.getElementById('filterAirport');
        const currentAirport = airportSelect.value;
        airportSelect.innerHTML = '<option value="">All</option>';
        filters.airports.forEach(ap => {
            const option = document.createElement('option');
            option.value = ap;
            option.textContent = ap;
            airportSelect.appendChild(option);
        });
        airportSelect.value = currentAirport;
        
        // Atualizar select de e-commerce
        const ecommerceSelect = document.getElementById('filterEcommerce');
        const currentEcommerce = ecommerceSelect.value;
        ecommerceSelect.innerHTML = '<option value="">All</option>';
        filters.ecommerce.forEach(ec => {
            const option = document.createElement('option');
            option.value = ec.name;
            option.textContent = `${ec.abbr} (${ec.name})`;
            ecommerceSelect.appendChild(option);
        });
        ecommerceSelect.value = currentEcommerce;
        
        renderFailureReasonFilterOptions(filters);

        ensureFailureReasonTranslations(filters.failure_reasons);
        
    } catch (error) {
        console.error('Erro ao carregar filtros:', error);
    }
}

// Renderizar top 3
function renderTop3(failures) {
    const container = document.getElementById('top3Container');
    
    if (!failures || failures.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 col-span-3">No data available</div>';
        return;
    }
    
    container.innerHTML = failures.map((failure, index) => `
        <div class="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
            <div class="text-3xl font-bold text-blue-600 mb-2">#${index + 1}</div>
            <div class="font-semibold text-gray-900 mb-2">${getFailureReasonDisplay(failure.failure_reason)}</div>
            <div class="text-sm text-gray-600">
                <div>📦 ${failure.quantidade.toLocaleString('pt-BR')} shipments</div>
                <div>📊 ${failure.percentual.toFixed(2)}%</div>
                <div>🏢 ${failure.ecommerce_abbr}</div>
            </div>
        </div>
    `).join('');
}

// Renderizar tabela
function renderTable(data) {
    const tbody = document.getElementById('tableBody');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-3 text-center text-gray-500">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => `
        <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-900">${row.airport}</td>
            <td class="px-4 py-3 text-gray-900">${row.ecommerce_abbr}</td>
            <td class="px-4 py-3 text-gray-900">${getFailureReasonDisplay(row.failure_reason)}</td>
            <td class="px-4 py-3 text-right text-gray-900 font-medium">${row.quantidade.toLocaleString('pt-BR')}</td>
            <td class="px-4 py-3 text-right text-gray-900 font-medium">${row.percentual.toFixed(2)}%</td>
            <td class="px-4 py-3 text-right text-gray-900 font-medium">${(row.valores ?? 0).toFixed(4)}</td>
        </tr>
    `).join('');
}

// Renderizar gráficos
function renderCharts(data) {
    if (!data || data.length === 0) return;
    
    // Agrupar por failure reason
    const failureReasons = {};
    const ecommerces = {};
    
    data.forEach(row => {
        const failureReasonDisplay = getFailureReasonDisplay(row.failure_reason);

        // Failure reasons
        if (!failureReasons[failureReasonDisplay]) {
            failureReasons[failureReasonDisplay] = 0;
        }
        failureReasons[failureReasonDisplay] += row.quantidade;
        
        // E-commerce
        if (!ecommerces[row.ecommerce_abbr]) {
            ecommerces[row.ecommerce_abbr] = 0;
        }
        ecommerces[row.ecommerce_abbr] += row.quantidade;
    });
    
    // Ordenar e pegar top 10
    const topFailures = Object.entries(failureReasons)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    const topEcommerces = Object.entries(ecommerces)
        .sort((a, b) => b[1] - a[1]);
    
    // Cores
    const colors = [
        '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16'
    ];
    
    // Gráfico de Failure Reasons
    renderChart(
        'chartFailureReasons',
        'Failure Reasons (Top 10)',
        topFailures.map(f => f[0]),
        topFailures.map(f => f[1]),
        colors
    );
    
    // Gráfico de E-Commerce
    renderChart(
        'chartEcommerce',
        'E-Commerce',
        topEcommerces.map(e => e[0]),
        topEcommerces.map(e => e[1]),
        colors.slice(0, topEcommerces.length)
    );
}

// Renderizar gráfico individual
function renderChart(canvasId, label, labels, data, colors) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Destruir gráfico anterior se existir
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    
    const ctx = canvas.getContext('2d');
    
    // Para Failure Reasons, usar gráfico de pizza/donut para melhor visualização
    const chartType = canvasId === 'chartFailureReasons' ? 'doughnut' : 'bar';

    const palette = (colors && colors.length) ? colors : ['#3b82f6'];
    const backgroundColors = data.map((_, i) => (palette[i % palette.length] + '99'));
    const borderColors = data.map((_, i) => palette[i % palette.length]);

    const datasetBase = {
        label: label,
        data: data,
        backgroundColor: backgroundColors,
        borderColor: borderColors,
        borderWidth: 2
    };

    const dataset = chartType === 'bar'
        ? {
            ...datasetBase,
            minBarLength: 2,
            borderRadius: 10,
            borderSkipped: false,
            barPercentage: 0.7,
            categoryPercentage: 0.75
        }
        : {
            ...datasetBase,
            borderColor: 'rgba(255, 255, 255, 0.9)',
            borderWidth: 2,
            spacing: 2,
            hoverOffset: 8
        };
    
    chartInstances[canvasId] = new Chart(ctx, {
        type: chartType,
        data: {
            labels: labels,
            datasets: [dataset]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: 8
            },
            animation: {
                duration: 600,
                easing: 'easeOutQuart'
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: chartType === 'doughnut',
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: {
                            size: 11
                        },
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                const dataset = data.datasets[0];
                                const total = dataset.data.reduce((a, b) => a + b, 0);
                                return data.labels.map((label, i) => {
                                    const value = dataset.data[i];
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return {
                                        text: `${label}: ${percentage}%`,
                                        fillStyle: dataset.backgroundColor[i],
                                        strokeStyle: dataset.borderColor[i],
                                        lineWidth: dataset.borderWidth,
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.92)',
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    padding: 10,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toLocaleString('pt-BR')} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: chartType === 'doughnut' ? '68%' : undefined,
            scales: chartType === 'bar' ? {
                y: {
                    beginAtZero: true,
                    grace: '8%',
                    grid: {
                        display: true,
                        color: 'rgba(2, 6, 23, 0.06)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('pt-BR');
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: 'rgba(15, 23, 42, 0.8)'
                    }
                }
            } : {}
        }
    });
}

// Mostrar mensagem de info
function showInfo(message, type = 'info') {
    const infoBox = document.getElementById('infoBox');
    const infoText = document.getElementById('infoText');
    
    infoText.textContent = message;
    
    infoBox.className = 'rounded-lg p-4 border';
    if (type === 'info') {
        infoBox.className += ' bg-blue-50 border-blue-200 text-blue-800';
    } else if (type === 'warning') {
        infoBox.className += ' bg-yellow-50 border-yellow-200 text-yellow-800';
    } else if (type === 'error') {
        infoBox.className += ' bg-red-50 border-red-200 text-red-800';
    } else if (type === 'success') {
        infoBox.className += ' bg-green-50 border-green-200 text-green-800';
    }
}

// Lidar com upload
async function handleUpload(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showUploadMessage('Select a file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showUploadMessage('Uploading file...', 'info');
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showUploadMessage(`✅ ${data.message}`, 'success');
            document.getElementById('uploadForm').reset();
            
            // Recarregar dashboard
            setTimeout(() => {
                showTab('dashboard');
                loadDashboard();
            }, 1500);
        } else {
            showUploadMessage(`❌ ${data.message}`, 'error');
        }
    } catch (error) {
        console.error('Erro no upload:', error);
        showUploadMessage('Error uploading file', 'error');
    }
}

// Mostrar mensagem de upload
function showUploadMessage(message, type) {
    const messageDiv = document.getElementById('uploadMessage');
    messageDiv.classList.remove('hidden');
    messageDiv.textContent = message;
    
    messageDiv.className = 'mt-6 p-4 rounded-lg';
    if (type === 'success') {
        messageDiv.className += ' bg-green-50 border border-green-200 text-green-800';
    } else if (type === 'error') {
        messageDiv.className += ' bg-red-50 border border-red-200 text-red-800';
    } else {
        messageDiv.className += ' bg-blue-50 border border-blue-200 text-blue-800';
    }
}
