// ==============================================================================
// GX MENU — RAILWAY UNIFIED ECOSYSTEM RUNNER
// Launches both the Express Web Server and the Discord Bot concurrently
// ==============================================================================
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });

console.log('====================================================');
console.log('🚀 [RAILWAY RUNNER] Launching GX MENU Ecosystem...');
console.log('   Port: ' + (process.env.PORT || 8080));
console.log('====================================================');

// Global Error Interceptors
process.on('unhandledRejection', error => {
  console.error('[UNHANDLED REJECTION]', (error && error.message) || error);
});
process.on('uncaughtException', error => {
  console.error('[UNCAUGHT EXCEPTION]', (error && error.message) || error);
});

// 1. Launch Express Web Portal
try {
  require('./server/server.js');
  console.log('✅ [RAILWAY RUNNER] Express Web Server initialized.');
} catch (err) {
  console.error('❌ [RAILWAY RUNNER] Web Server failed to start:', err);
}

// 2. Launch Discord Bot
try {
  require('./bot/bot.js');
  console.log('✅ [RAILWAY RUNNER] Discord Bot initialized.');
} catch (err) {
  console.error('❌ [RAILWAY RUNNER] Discord Bot failed to start:', err);
}
