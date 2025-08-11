const express = require('express');
const basicAuth = require('express-basic-auth');
const { createProxyMiddleware } = require('http-proxy-middleware');
const bcrypt = require('bcryptjs');

// Load environment variables from .env file
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const FASTAPI_PORT = process.env.FASTAPI_PORT || 8000;

// Environment variables for authentication
const PROTECTED_CONTENT_USERNAME = process.env.PROTECTED_CONTENT_USERNAME || 'researcher';
const PROTECTED_CONTENT_PASSWORD_HASH = process.env.PROTECTED_CONTENT_PASSWORD_HASH;
const PROTECTED_DATASETS = (process.env.PROTECTED_DATASETS || 'detectiveqa').split(',').map(d => d.trim());

if (!PROTECTED_CONTENT_PASSWORD_HASH) {
    console.error('ERROR: PROTECTED_CONTENT_PASSWORD_HASH environment variable is required');
    console.log('Generate a hash with: node -e "console.log(require(\'bcryptjs\').hashSync(\'your-password\', 10))"');
    process.exit(1);
}

// Custom authorizer function using bcrypt
const customAuthorizer = (username, password) => {
    const validUsername = basicAuth.safeCompare(username, PROTECTED_CONTENT_USERNAME);
    const validPassword = bcrypt.compareSync(password, PROTECTED_CONTENT_PASSWORD_HASH);
    return validUsername && validPassword;
};

// HTTP Basic Auth middleware for protected content
const protectedContentAuth = basicAuth({
    authorizer: customAuthorizer,
    challenge: true,
    realm: 'Protected Research Content',
    unauthorizedResponse: (req) => {
        return `
        <html>
            <head><title>Authentication Required</title></head>
            <body>
                <h1>Authentication Required</h1>
                <p>Access to protected content requires authentication for copyright protection.</p>
                <p>Please contact the research team for access credentials.</p>
            </body>
        </html>
        `;
    }
});

// Middleware to protect specified dataset data endpoints
app.use((req, res, next) => {
    const url = req.originalUrl;
    
    // Check if URL contains any protected dataset
    const isProtectedContent = PROTECTED_DATASETS.some(dataset => {
        return url.includes(`/data/outputs/chunks/${dataset}`) || 
               url.includes(`/data/outputs/summaries/${dataset}`) ||
               (url.includes('/data/prompts/') && url.includes(dataset)) ||
               (url.includes('/api/') && url.includes(dataset) && !url.endsWith('/api/files')) || // Exclude /api/files
               url.includes(`/${dataset}/`) || // Dashboard routes like /detectiveqa/collection/item/123
               url.startsWith(`/${dataset}`); // Routes starting with /detectiveqa
    });
    
    if (isProtectedContent) {
        return protectedContentAuth(req, res, next);
    }
    
    next();
});

// Proxy all other requests to FastAPI
const proxyOptions = {
    target: `http://127.0.0.1:${FASTAPI_PORT}`,
    changeOrigin: true,
    ws: true, // Enable websocket proxying if needed
    onError: (err, req, res) => {
        console.error('Proxy error:', err.message);
        res.status(500).send(`
        <html>
            <head><title>Service Unavailable</title></head>
            <body>
                <h1>Service Unavailable</h1>
                <p>The dashboard service is currently unavailable.</p>
                <p>Error: ${err.message}</p>
            </body>
        </html>
        `);
    },
    onProxyReq: (proxyReq, req, res) => {
        // Log protected requests
        const isProtectedContent = PROTECTED_DATASETS.some(dataset => {
            return req.originalUrl.includes(`/data/outputs/chunks/${dataset}`) || 
                   req.originalUrl.includes(`/data/outputs/summaries/${dataset}`) ||
                   (req.originalUrl.includes('/api/') && req.originalUrl.includes(dataset));
        });
        
        if (isProtectedContent) {
            console.log(`[AUTH] Protected data request: ${req.method} ${req.originalUrl}`);
        }
    }
};

// Create proxy middleware
const proxy = createProxyMiddleware(proxyOptions);

// Apply proxy to all requests (after auth middleware)
app.use('/', proxy);

// Start server
app.listen(PORT, () => {
    console.log(`🔒 Express proxy server running on port ${PORT}`);
    console.log(`📡 Proxying to FastAPI on port ${FASTAPI_PORT}`);
    console.log(`🛡️  Protected datasets: ${PROTECTED_DATASETS.join(', ')}`);
    console.log(`👤 Username: ${PROTECTED_CONTENT_USERNAME}`);
    
    if (process.env.NODE_ENV !== 'production') {
        console.log('\n🔧 Development setup:');
        console.log('1. Set PROTECTED_CONTENT_PASSWORD_HASH in your environment');
        console.log('2. Start FastAPI: uvicorn main:app --port 8000');
        console.log('3. Access dashboard at http://localhost:3000');
    }
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Shutting down Express proxy server...');
    process.exit(0);
});