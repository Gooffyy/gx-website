// ==============================================================================
// GX MENU — RAILWAY UNIFIED ECOSYSTEM RUNNER
// Launches both the Express Web Server and the Discord Bot simultaneously
// ==============================================================================
const { fork } = require('child_process');
const path = require('path');

console.log('====================================================');
console.log('🚀 [RAILWAY RUNNER] Launching GX MENU Ecosystem...');
console.log('====================================================');

// 1. Spawn Web Server
const serverProcess = fork(path.join(__dirname, 'server/server.js'), [], {
  stdio: 'inherit'
});

serverProcess.on('exit', (code, signal) => {
  console.warn(`[SERVER PROCESS] Exited with code: ${code}, signal: ${signal}`);
});

// 2. Spawn Discord Bot
const botProcess = fork(path.join(__dirname, 'bot/bot.js'), [], {
  stdio: 'inherit'
});

botProcess.on('exit', (code, signal) => {
  console.warn(`[BOT PROCESS] Exited with code: ${code}, signal: ${signal}`);
});

// Graceful process termination handlers for Railway container lifecycle
process.on('SIGTERM', () => {
  console.log('🛑 [RAILWAY] SIGTERM received. Gracefully terminating child processes...');
  serverProcess.kill('SIGTERM');
  botProcess.kill('SIGTERM');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('🛑 [RAILWAY] SIGINT received. Shutting down...');
  serverProcess.kill('SIGINT');
  botProcess.kill('SIGINT');
  process.exit(0);
});
