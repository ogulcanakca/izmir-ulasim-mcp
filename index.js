#!/usr/bin/env node

const { spawn } = require('child_process');

const pythonProcess = spawn('python', ['izmir_ulasim_main.py'], {
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