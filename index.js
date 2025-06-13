#!/usr/bin/env node

const path = require('path');
const { spawn } = require('child_process');

const pythonScriptPath = path.join(__dirname, 'izmir_ulasim_main.py');

const pythonProcess = spawn('python', [pythonScriptPath], {
    stdio: 'inherit'
});

pythonProcess.on('close', (code) => {
    if (code !== 0) {
        console.error(`Python script exited with code ${code}`);
    } else {
        console.log('Python script finished successfully.');
    }
});

pythonProcess.on('error', (err) => {
    console.error('Failed to start Python script:', err);
});