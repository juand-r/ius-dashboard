#!/usr/bin/env node

const bcrypt = require('bcryptjs');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('🔐 Protected Content Password Hash Generator');
console.log('============================================');

rl.question('Enter password to hash: ', (password) => {
  if (!password || password.trim().length === 0) {
    console.error('❌ Password cannot be empty');
    process.exit(1);
  }

  console.log('\n🔄 Generating hash...');
  
  const hash = bcrypt.hashSync(password.trim(), 10);
  
  console.log('\n✅ Password hash generated successfully!');
  console.log('\n📋 Add this to your environment variables:');
  console.log('==========================================');
  console.log(`PROTECTED_CONTENT_USERNAME=researcher`);
  console.log(`PROTECTED_CONTENT_PASSWORD_HASH=${hash}`);
  console.log(`PROTECTED_DATASETS=detectiveqa`);
  console.log('\n🚀 For Railway deployment:');
  console.log('Set these variables in your Railway dashboard under "Variables"');
  console.log('\n🔧 For local development:');
  console.log('Add these to your .env file in the project root');
  
  rl.close();
});

rl.on('SIGINT', () => {
  console.log('\n👋 Goodbye!');
  process.exit(0);
});