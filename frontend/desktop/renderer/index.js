// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  // Get UI elements
  const selectFilesBtn = document.getElementById('select-files-btn');
  const selectDirectoryBtn = document.getElementById('select-directory-btn');
  const fileListElement = document.getElementById('file-list');
  const fileDetailsElement = document.getElementById('file-details');
  const filePreviewElement = document.getElementById('file-preview');
  
  // Current state
  let selectedFileId = null;
  let organizedFiles = [];
  
  // Event listeners
  selectFilesBtn.addEventListener('click', async () => {
    try {
      const filePaths = await window.api.selectFiles();
      if (filePaths.length > 0) {
        processSelectedFiles(filePaths);
      }
    } catch (error) {
      console.error('Error selecting files:', error);
      showError('Failed to select files');
    }
  });
  
  selectDirectoryBtn.addEventListener('click', async () => {
    try {
      const directoryPath = await window.api.selectDirectory();
      if (directoryPath) {
        processSelectedDirectory(directoryPath);
      }
    } catch (error) {
      console.error('Error selecting directory:', error);
      showError('Failed to select directory');
    }
  });
  
  // Process selected files
  async function processSelectedFiles(filePaths) {
    showLoading('Processing files...');
    try {
      const result = await window.api.processFiles(filePaths);
      if (result.success) {
        showMessage('Files processed successfully');
        loadOrganizedFiles();
      } else {
        showError(result.error || 'Failed to process files');
      }
    } catch (error) {
      console.error('Error processing files:', error);
      showError('Failed to process files');
    }
  }
  
  // Process selected directory
  async function processSelectedDirectory(directoryPath) {
    showLoading('Scanning directory...');
    try {
      const result = await window.api.processFiles([directoryPath]);
      if (result.success) {
        showMessage('Directory scanned successfully');
        loadOrganizedFiles();
      } else {
        showError(result.error || 'Failed to scan directory');
      }
    } catch (error) {
      console.error('Error scanning directory:', error);
      showError('Failed to scan directory');
    }
  }
  
  // Load organized files from the backend
  async function loadOrganizedFiles() {
    showLoading('Loading files...');
    try {
      const result = await window.api.getOrganizedFiles();
      if (result.success) {
        organizedFiles = result.files || [];
        renderFileList();
        showMessage('Files loaded successfully');
      } else {
        showError(result.error || 'Failed to load files');
      }
    } catch (error) {
      console.error('Error loading files:', error);
      showError('Failed to load files');
    }
  }
  
  // Render the file list in the sidebar
  function renderFileList() {
    fileListElement.innerHTML = '';
    
    if (organizedFiles.length === 0) {
      fileListElement.innerHTML = '<p class="empty-message">No files found</p>';
      return;
    }
    
    organizedFiles.forEach(file => {
      const fileItem = document.createElement('div');
      fileItem.classList.add('file-item');
      if (file.id === selectedFileId) {
        fileItem.classList.add('selected');
      }
      
      fileItem.textContent = file.name;
      fileItem.dataset.id = file.id;
      
      fileItem.addEventListener('click', () => {
        selectFile(file.id);
      });
      
      fileListElement.appendChild(fileItem);
    });
  }
  
  // Select a file from the list
  function selectFile(fileId) {
    selectedFileId = fileId;
    
    // Update UI to show selected file
    document.querySelectorAll('.file-item').forEach(item => {
      item.classList.toggle('selected', item.dataset.id === fileId);
    });
    
    // Find the selected file object
    const selectedFile = organizedFiles.find(file => file.id === fileId);
    
    if (selectedFile) {
      renderFileDetails(selectedFile);
      renderFilePreview(selectedFile);
    }
  }
  
  // Render file details
  function renderFileDetails(file) {
    const details = `
      <table class="details-table">
        <tr>
          <th>Name:</th>
          <td>${file.name}</td>
        </tr>
        <tr>
          <th>Type:</th>
          <td>${file.type}</td>
        </tr>
        <tr>
          <th>Path:</th>
          <td>${file.path}</td>
        </tr>
        <tr>
          <th>Size:</th>
          <td>${formatFileSize(file.size)}</td>
        </tr>
        <tr>
          <th>Modified:</th>
          <td>${new Date(file.modified).toLocaleString()}</td>
        </tr>
      </table>
    `;
    
    fileDetailsElement.innerHTML = details;
  }
  
  // Render file preview (placeholder for now)
  function renderFilePreview(file) {
    // This would be replaced with actual preview rendering depending on file type
    filePreviewElement.innerHTML = `<div class="preview-placeholder">
      <p>Preview not available for ${file.type} files yet</p>
    </div>`;
  }
  
  // Helper functions
  function formatFileSize(sizeInBytes) {
    if (sizeInBytes < 1024) {
      return sizeInBytes + ' B';
    } else if (sizeInBytes < 1024 * 1024) {
      return (sizeInBytes / 1024).toFixed(2) + ' KB';
    } else if (sizeInBytes < 1024 * 1024 * 1024) {
      return (sizeInBytes / (1024 * 1024)).toFixed(2) + ' MB';
    } else {
      return (sizeInBytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }
  }
  
  function showMessage(message) {
    // Implement your notification system here
    console.log('Message:', message);
  }
  
  function showError(error) {
    // Implement your error notification system here
    console.error('Error:', error);
  }
  
  function showLoading(message) {
    // Implement your loading indicator here
    console.log('Loading:', message);
  }
  
  // Initialize the app
  loadOrganizedFiles();
  
  // Listen for file processing events from main process
  const cleanupListener = window.api.onFileProcessingComplete((result) => {
    if (result.success) {
      showMessage(result.message || 'File processing complete');
      loadOrganizedFiles();
    } else {
      showError(result.error || 'File processing failed');
    }
  });
  
  // Clean up event listeners when window is closed
  window.addEventListener('beforeunload', () => {
    if (cleanupListener) cleanupListener();
  });
});
