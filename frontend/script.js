// ============ API Configuration ============
// Ye check karta hai ki website local chal rahi hai ya GitHub par
const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';

// GitHub par daalne ke baad 'https://your-backend-app.onrender.com' jaisa URL yahan daalein
const LIVE_BACKEND_URL = 'https://YOUR_LIVE_BACKEND_URL.com'; 
const LOCAL_BACKEND_URL = 'http://localhost:8000'; // Agar backend 5000 par hai toh ise 5000 kar dein

const API_URL = `${IS_PRODUCTION ? LIVE_BACKEND_URL : LOCAL_BACKEND_URL}/api`;

// User State
let currentUser = null;
let analysisHistory = [];
let selectedFile = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAuthentication();
});

// Setup Event Listeners
function setupEventListeners() {
    // Auth Forms
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const fileInput = document.getElementById('fileInput');
    const voiceBtn = document.getElementById('voiceBtn');

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (signupForm) signupForm.addEventListener('submit', handleSignup);
    if (fileInput) fileInput.addEventListener('change', handleFileUpload);
    if (voiceBtn) voiceBtn.addEventListener('click', startVoiceInput);
}

// ============ AUTHENTICATION ============

function checkAuthentication() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    
    if (token && user) {
        currentUser = JSON.parse(user);
        showMainContent();
    }
}

function switchTab(tab) {
    document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'login') {
        document.getElementById('loginForm').classList.add('active');
        const loginTab = document.querySelector('[onclick="switchTab(\'login\')"]');
        if (loginTab) loginTab.classList.add('active');
    } else {
        document.getElementById('signupForm').classList.add('active');
        const signupTab = document.querySelector('[onclick="switchTab(\'signup\')"]');
        if (signupTab) signupTab.classList.add('active');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorEl = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            currentUser = data.user;
            showMainContent();
        } else {
            if (errorEl) errorEl.textContent = data.message || 'Login failed';
        }
    } catch (error) {
        if (errorEl) errorEl.textContent = `Connection error. Make sure backend is running on ${IS_PRODUCTION ? 'Cloud' : 'localhost'}.`;
    }
}

async function handleSignup(e) {
    e.preventDefault();
    
    const name = document.getElementById('signupName').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    const phone = document.getElementById('signupPhone').value;
    const errorEl = document.getElementById('signupError');
    
    try {
        const response = await fetch(`${API_URL}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password, phone })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            currentUser = data.user;
            showMainContent();
        } else {
            if (errorEl) errorEl.textContent = data.message || 'Signup failed';
        }
    } catch (error) {
        if (errorEl) errorEl.textContent = `Connection error. Make sure backend is running on ${IS_PRODUCTION ? 'Cloud' : 'localhost'}.`;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    currentUser = null;
    analysisHistory = [];
    document.getElementById('authModal').classList.add('active');
    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('loginForm').reset();
    document.getElementById('signupForm').reset();
}

// ============ NAVIGATION ============

function showMainContent() {
    document.getElementById('authModal').classList.remove('active');
    document.getElementById('mainContent').style.display = 'block';
    document.getElementById('userName').textContent = currentUser.name;
    loadAnalysisHistory();
    navigateTo('dashboard');
}

function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    
    switch(page) {
        case 'dashboard':
            document.getElementById('dashboardPage').classList.add('active');
            updateDashboardStats();
            break;
        case 'analysis':
            document.getElementById('analysisPage').classList.add('active');
            document.getElementById('resultsSection').style.display = 'none';
            newAnalysis();
            break;
        case 'history':
            document.getElementById('historyPage').classList.add('active');
            loadAnalysisHistory();
            break;
    }
}

// ============ DASHBOARD ============

function updateDashboardStats() {
    document.getElementById('totalAnalyses').textContent = analysisHistory.length;
    const recentCount = analysisHistory.filter(a => {
        const date = new Date(a.timestamp);
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }).length;
    document.getElementById('recentSessions').textContent = recentCount;
}

// ============ ANALYSIS ============

function newAnalysis() {
    document.getElementById('symptomText').value = '';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    selectedFile = null;
    document.querySelectorAll('.chip').forEach(chip => chip.classList.remove('selected'));
}

function addSymptom(element) {
    element.classList.toggle('selected');
    
    if (element.classList.contains('selected')) {
        document.getElementById('symptomText').value += element.textContent + ', ';
    }
}

function handleFileUpload(e) {
    selectedFile = e.target.files[0];
    if (selectedFile) {
        document.getElementById('fileName').textContent = '✓ ' + selectedFile.name;
    }
}

async function analyzeSymptoms() {
    const symptoms = document.getElementById('symptomText').value.trim();
    
    if (!symptoms) {
        alert('Please enter or select symptoms');
        return;
    }
    
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultCard').innerHTML = '<div class="loading"><div class="spinner"></div><p>AI is analyzing your symptoms...</p></div>';
    
    try {
        const formData = new FormData();
        formData.append('symptoms', symptoms);
        formData.append('userId', currentUser.id);
        
        if (selectedFile) {
            formData.append('file', selectedFile);
        }
        
        const response = await fetch(`${API_URL}/analysis/analyze`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data);
            analysisHistory.unshift({
                id: Date.now(),
                symptoms: symptoms,
                results: data.diagnosis,
                timestamp: new Date().toISOString()
            });
            updateDashboardStats();
        } else {
            document.getElementById('resultCard').innerHTML = 
                '<div class="error"><p>Error: ' + data.message + '</p></div>';
        }
    } catch (error) {
        document.getElementById('resultCard').innerHTML = 
            `<div class="error"><p>Connection error. Make sure backend is running on ${IS_PRODUCTION ? 'Cloud' : 'localhost'}</p></div>`;
    }
}

function displayResults(data) {
    let html = '<div class="result-content">';
    
    if (data.diagnosis && data.diagnosis.length > 0) {
        data.diagnosis.forEach((diagnosis, index) => {
            const confidence = (diagnosis.confidence * 100).toFixed(1);
            html += `
                <div class="result-item">
                    <h3>${index + 1}. ${diagnosis.name}</h3>
                    <p>${diagnosis.description}</p>
                    <div class="probability">Probability: ${confidence}%</div>
                    <p style="margin-top: 10px; color: #666;"><strong>Recommendations:</strong></p>
                    <ul style="margin-left: 20px; color: #666;">
                        ${diagnosis.recommendations.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            `;
        });
    } else {
        html += '<p>No specific diagnosis could be determined. Please consult a healthcare professional.</p>';
    }
    
    html += `
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #ffc107;">
            <strong>⚠️ Important Disclaimer:</strong>
            <p style="font-size: 13px; margin-top: 5px;">
                This analysis is for informational purposes only and should not replace professional medical advice. 
                Always consult with a qualified healthcare professional for diagnosis and treatment.
            </p>
        </div>
    `;
    
    html += '</div>';
    document.getElementById('resultCard').innerHTML = html;
}

// ============ VOICE INPUT ============

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

function startVoiceInput() {
    if (!SpeechRecognition) {
        alert('Speech Recognition not supported in this browser');
        return;
    }
    
    if (!recognition) {
        recognition = new SpeechRecognition();
        
        recognition.continuous = true; 
        recognition.interimResults = true; 
        
        recognition.onstart = () => {
            isListening = true;
            document.getElementById('voiceBtn').style.background = '#e74c3c';
            document.getElementById('voiceStatus').textContent = '🎙️ Listening...';
        };
        
        recognition.onresult = (event) => {
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                let transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                }
            }
            
            if (finalTranscript !== '') {
                document.getElementById('symptomText').value += finalTranscript;
            }
        };
        
        recognition.onend = () => {
            isListening = false;
            document.getElementById('voiceBtn').style.background = 'var(--secondary-color, #3498db)';
            document.getElementById('voiceStatus').textContent = '✓ Done';
        };
    }
    
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

// ============ HISTORY ============

async function loadAnalysisHistory() {
    try {
        const response = await fetch(`${API_URL}/analysis/history`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            analysisHistory = data.analyses;
            displayAnalysisHistory();
        }
    } catch (error) {
        console.log('Using local history');
        displayAnalysisHistory();
    }
}

function displayAnalysisHistory() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;
    
    if (analysisHistory.length === 0) {
        historyList.innerHTML = '<p class="empty-state">No analysis history yet. Start your first analysis!</p>';
        return;
    }
    
    historyList.innerHTML = analysisHistory.map((analysis, index) => {
        const symptomsSnippet = analysis.symptoms ? analysis.symptoms.substring(0, 50) : 'No symptoms listed';
        return `
            <div class="history-item">
                <div class="history-item-info">
                    <h3>Analysis #${analysisHistory.length - index}</h3>
                    <p>${new Date(analysis.timestamp).toLocaleString()}</p>
                    <p>Symptoms: ${symptomsSnippet}...</p>
                </div>
                <div class="history-item-actions">
                    <button onclick="viewAnalysis(${index})">View</button>
                    <button onclick="deleteAnalysis(${index})" style="background: #e74c3c;">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

function viewAnalysis(index) {
    const analysis = analysisHistory[index];
    navigateTo('analysis');
    document.getElementById('symptomText').value = analysis.symptoms;
    document.getElementById('resultsSection').style.display = 'block';
    displayResults(analysis.results);
}

function deleteAnalysis(index) {
    if (confirm('Delete this analysis?')) {
        analysisHistory.splice(index, 1);
        displayAnalysisHistory();
        updateDashboardStats();
    }
}

// ============ REPORT GENERATION ============

function downloadReport() {
    const symptomText = document.getElementById('symptomText').value;
    const resultCard = document.getElementById('resultCard');
    
    let content = `MEDAI HEALTHCARE DIAGNOSTIC REPORT
=====================================

Patient Name: ${currentUser ? currentUser.name : 'Guest'}
Date: ${new Date().toLocaleString()}

SYMPTOMS:
${symptomText}

ANALYSIS RESULTS:
${resultCard ? resultCard.innerText : 'No results found'}

IMPORTANT DISCLAIMER:
This analysis is for informational purposes only and should not replace 
professional medical advice. Always consult with a qualified healthcare professional.

Generated by MedAI Diagnostic System`;
    
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', `MedAI_Report_${Date.now()}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

function printReport() {
    const printContent = `
        <h2>MEDAI HEALTHCARE DIAGNOSTIC REPORT</h2>
        <p><strong>Patient:</strong> ${currentUser ? currentUser.name : 'Guest'}</p>
        <p><strong>Date:</strong> ${new Date().toLocaleString()}</p>
        <h3>Symptoms:</h3>
        <p>${document.getElementById('symptomText').value}</p>
        <h3>Analysis Results:</h3>
        ${document.getElementById('resultCard').innerHTML}
    `;
    
    const printWindow = window.open('', '', 'height=500,width=800');
    if (printWindow) {
        printWindow.document.write('<html><head><title>MedAI Report</title>');
        printWindow.document.write('<link rel="stylesheet" href="style.css">');
        printWindow.document.write('</head><body>');
        printWindow.document.write(printContent);
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.print();
    }
}