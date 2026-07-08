const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 8000;

// ============ CONFIGURATION & CORS ============
app.use(express.json());

// GITHUB_USERNAME ki jagah apna asli GitHub username daalein
const allowedOrigins = [
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'http://localhost:3000',
    'https://YOUR_GITHUB_USERNAME.github.io' 
];

app.use(cors({
    origin: function (origin, callback) {
        if (!origin || allowedOrigins.indexOf(origin) !== -1) {
            callback(null, true);
        } else {
            callback(new Error('CORS Policy: This origin is not allowed by MedAI'));
        }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// ============ DUMMY DATABASE (Testing ke liye) ============
const users = [];
const dummyDiagnosis = [
    {
        name: "Common Cold (Sardi-Zukaam)",
        description: "Halki khansi, naak behna aur gale me kharash.",
        confidence: 0.85,
        recommendations: ["Garam paani piyein", "Aaram karein", "Vicks ka bhaap lein"]
    }
];

// ============ ROUTES ============

// 1. Signup Route
app.post('/api/auth/signup', (req, res) => {
    const { name, email, password, phone } = req.body;
    if (!name || !email || !password) {
        return res.status(400).json({ message: "Sari fields bharna zaroori hai" });
    }
    const newUser = { id: Date.now().toString(), name, email, phone };
    users.push(newUser);
    res.status(201).json({ token: "dummy-jwt-token-12345", user: newUser });
});

// 2. Login Route
app.post('/api/auth/login', (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) {
        return res.status(400).json({ message: "Email aur password daalein" });
    }
    // Dummy user login bypass
    const user = { id: "101", name: "Test Patient", email: email };
    res.status(200).json({ token: "dummy-jwt-token-12345", user });
});

// 3. Symptom Analysis Route
app.post('/api/analysis/analyze', (req, res) => {
    // Note: Agar frontend se FormData aa raha hai toh backend par 'multer' package lagana padta hai file save karne ke liye.
    // Abhi ke liye hum simple response bhej rahe hain.
    res.status(200).json({ diagnosis: dummyDiagnosis });
});

// 4. History Route
app.get('/api/analysis/history', (req, res) => {
    res.status(200).json({ analyses: [] });
});

// Start Server
app.listen(PORT, () => {
    console.log(`Backend server successfully running on port ${PORT}`);
});