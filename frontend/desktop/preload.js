const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'api', {
    // File handling methods
    selectFiles: () => ipcRenderer.invoke('select-files'),
    selectDirectory: () => ipcRenderer.invoke('select-directory'),
    processFiles: (filePaths) => ipcRenderer.invoke('process-files', filePaths),
    getOrganizedFiles: () => ipcRenderer.invoke('get-organized-files'),
    
    // Listen for events from main process
    onFileProcessingComplete: (callback) => {
      ipcRenderer.on('file-processing-complete', (event, result) => callback(result));
      return () => {
        ipcRenderer.removeAllListeners('file-processing-complete');
      };
    }
  }
);
