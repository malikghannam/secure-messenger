/**
 * Secure File Sharing Module
 * Handles file upload, policy selection, and secure viewing
 */

class FileSharing {
  constructor() {
    this.selectedFile = null;
    this.selectedPolicies = [];
    this.currentViewSession = null;
    this.timerInterval = null;
    
    this.initElements();
    this.bindEvents();
  }
  
  initElements() {
    // Input elements
    this.attachBtn = document.getElementById('attachButton');
    this.fileInput = document.getElementById('fileInput');
    this.dropZone = document.getElementById('fileDropZone');
    
    // Preview modal
    this.previewModal = document.getElementById('filePreviewModal');
    this.previewArea = document.getElementById('filePreviewArea');
    this.fileName = document.getElementById('fileName');
    this.fileSize = document.getElementById('fileSize');
    this.previewClose = document.getElementById('filePreviewClose');
    this.previewCancel = document.getElementById('filePreviewCancel');
    this.previewSend = document.getElementById('filePreviewSend');
    
    // Policy checkboxes (only view_once and time_limited)
    this.policyViewOnce = document.getElementById('policyViewOnce');
    this.policyTimeLimited = document.getElementById('policyTimeLimited');
    
    // Policy configs
    this.timeLimitedConfig = document.getElementById('timeLimitedConfig');
    
    // Secure viewer modal
    this.viewerModal = document.getElementById('secureFileViewerModal');
    this.viewerPolicies = document.getElementById('viewerPolicies');
    this.viewerTimer = document.getElementById('viewerTimer');
    this.timerDisplay = document.getElementById('timerDisplay');
    this.viewerLoading = document.getElementById('viewerLoading');
    this.viewerContent = document.getElementById('viewerContent');
    this.viewerFilename = document.getElementById('viewerFilename');
    this.viewerSender = document.getElementById('viewerSender');
    this.viewerClose = document.getElementById('secureViewerClose');
    
    // View once warning modal
    this.viewOnceModal = document.getElementById('viewOnceWarningModal');
    this.viewOnceCancel = document.getElementById('viewOnceCancel');
    this.viewOnceConfirm = document.getElementById('viewOnceConfirm');
  }
  
  bindEvents() {
    // Attach button click
    if (this.attachBtn) {
      this.attachBtn.addEventListener('click', () => this.fileInput?.click());
    }
    
    // File input change
    if (this.fileInput) {
      this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }
    
    // Drag and drop
    const chatPanel = document.getElementById('chatPanel');
    if (chatPanel) {
      chatPanel.addEventListener('dragover', (e) => this.handleDragOver(e));
      chatPanel.addEventListener('dragleave', (e) => this.handleDragLeave(e));
      chatPanel.addEventListener('drop', (e) => this.handleDrop(e));
    }
    
    // Preview modal
    if (this.previewClose) {
      this.previewClose.addEventListener('click', () => this.closePreviewModal());
    }
    if (this.previewCancel) {
      this.previewCancel.addEventListener('click', () => this.closePreviewModal());
    }
    if (this.previewSend) {
      this.previewSend.addEventListener('click', () => this.sendFile());
    }
    
    // Policy toggle for time_limited only
    this.bindPolicyToggle(this.policyTimeLimited, this.timeLimitedConfig);
    
    // Viewer modal
    if (this.viewerClose) {
      this.viewerClose.addEventListener('click', () => this.closeViewer());
    }
    
    // View once warning
    if (this.viewOnceCancel) {
      this.viewOnceCancel.addEventListener('click', () => this.closeViewOnceWarning());
    }
    if (this.viewOnceConfirm) {
      this.viewOnceConfirm.addEventListener('click', () => this.confirmViewOnce());
    }
    
    // Close modals on backdrop click
    [this.previewModal, this.viewerModal, this.viewOnceModal].forEach(modal => {
      if (modal) {
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            this.closeAllModals();
          }
        });
      }
    });
  }
  
  bindPolicyToggle(checkbox, configEl) {
    if (checkbox && configEl) {
      checkbox.addEventListener('change', () => {
        configEl.classList.toggle('hidden', !checkbox.checked);
      });
    }
  }
  
  handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    if (this.dropZone) {
      this.dropZone.classList.remove('hidden');
    }
  }
  
  handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.target === this.dropZone || !this.dropZone?.contains(e.relatedTarget)) {
      this.dropZone?.classList.add('hidden');
    }
  }
  
  handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    this.dropZone?.classList.add('hidden');
    
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      this.processFile(files[0]);
    }
  }
  
  handleFileSelect(e) {
    const files = e.target?.files;
    if (files && files.length > 0) {
      this.processFile(files[0]);
    }
    // Reset input
    if (this.fileInput) {
      this.fileInput.value = '';
    }
  }
  
  processFile(file) {
    // Validate file size (max 25MB)
    const maxSize = 25 * 1024 * 1024;
    if (file.size > maxSize) {
      this.showToast('حجم الملف كبير جداً (الحد الأقصى 25MB)', 'error');
      return;
    }
    
    // Validate file type
    const supportedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'video/mp4', 'video/webm',
      'audio/mpeg', 'audio/ogg', 'audio/wav',
      'application/pdf',
      'text/plain',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];
    
    if (!supportedTypes.includes(file.type) && !file.type.startsWith('image/')) {
      this.showToast('نوع الملف غير مدعوم', 'error');
      return;
    }
    
    this.selectedFile = file;
    this.showPreviewModal();
  }
  
  showPreviewModal() {
    if (!this.selectedFile || !this.previewModal) return;
    
    // Update file info
    if (this.fileName) {
      this.fileName.textContent = this.selectedFile.name;
    }
    if (this.fileSize) {
      this.fileSize.textContent = this.formatFileSize(this.selectedFile.size);
    }
    
    // Show preview
    this.renderFilePreview();
    
    // Reset policies
    this.resetPolicies();
    
    // Set default expiry date to tomorrow
    const expiryInput = document.getElementById('expiryDateTime');
    if (expiryInput) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      expiryInput.value = tomorrow.toISOString().slice(0, 16);
    }
    
    // Show modal
    this.previewModal.classList.remove('hidden');
  }
  
  renderFilePreview() {
    if (!this.previewArea || !this.selectedFile) return;
    
    const file = this.selectedFile;
    
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.previewArea.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
      };
      reader.readAsDataURL(file);
    } else if (file.type.startsWith('video/')) {
      const url = URL.createObjectURL(file);
      this.previewArea.innerHTML = `<video src="${url}" controls></video>`;
    } else if (file.type.startsWith('audio/')) {
      const url = URL.createObjectURL(file);
      this.previewArea.innerHTML = `<audio src="${url}" controls></audio>`;
    } else {
      // Document preview
      const icon = this.getFileIcon(file.type);
      this.previewArea.innerHTML = `
        <div class="file-preview-placeholder">
          ${icon}
          <span>${file.name}</span>
        </div>
      `;
    }
  }
  
  getFileIcon(mimeType) {
    if (mimeType === 'application/pdf') {
      return `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10 9 9 9 8 9"></polyline>
      </svg>`;
    }
    return `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      <polyline points="14 2 14 8 20 8"></polyline>
    </svg>`;
  }
  
  resetPolicies() {
    // Reset only the two supported policies
    if (this.policyViewOnce) this.policyViewOnce.checked = false;
    if (this.policyTimeLimited) this.policyTimeLimited.checked = false;
    
    this.timeLimitedConfig?.classList.add('hidden');
  }
  
  closePreviewModal() {
    this.previewModal?.classList.add('hidden');
    this.selectedFile = null;
    if (this.previewArea) {
      this.previewArea.innerHTML = `
        <div class="file-preview-placeholder">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
        </div>
      `;
    }
  }
  
  collectPolicies() {
    const policies = [];
    
    if (this.policyViewOnce?.checked) {
      policies.push({ type: 'view_once' });
    }
    
    if (this.policyTimeLimited?.checked) {
      const duration = parseInt(document.getElementById('timeLimitedDuration')?.value || '30');
      policies.push({ type: 'time_limited', duration_seconds: duration });
    }
    
    return policies;
  }
  
  async sendFile() {
    if (!this.selectedFile) return;
    
    const policies = this.collectPolicies();
    const currentPeer = window.AppState?.ui?.currentPeer || window.currentPeer;
    
    if (!currentPeer) {
      this.showToast('اختر جهة اتصال أولاً', 'error');
      return;
    }
    
    // Disable send button
    if (this.previewSend) {
      this.previewSend.disabled = true;
      this.previewSend.innerHTML = '<div class="loading-spinner" style="width:16px;height:16px;"></div> جاري الإرسال...';
    }
    
    try {
      // Read file as base64
      const fileData = await this.readFileAsBase64(this.selectedFile);
      
      // Create file message object
      const fileMessage = {
        type: 'file',
        filename: this.selectedFile.name,
        file_type: this.selectedFile.type,
        file_size: this.selectedFile.size,
        data: fileData,
        policies: policies,
        recipient: currentPeer
      };
      
      // Send via existing message API (same as text messages)
      const fileText = `[FILE:${JSON.stringify({
        filename: fileMessage.filename,
        file_type: fileMessage.file_type,
        file_size: fileMessage.file_size,
        data: fileMessage.data,
        policies: fileMessage.policies
      })}]`;
      
      const response = await fetch('/api/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ to: currentPeer, text: fileText })
      });
      
      const result = await response.json();
      
      if (result.ok) {
        // Add optimistic message to UI
        this.addFileMessageToUI(fileMessage, true);
        this.closePreviewModal();
        this.showToast('تم إرسال الملف بنجاح', 'success');
      } else {
        throw new Error(result.error || 'Failed to send file');
      }
      
    } catch (error) {
      console.error('Error sending file:', error);
      this.showToast('فشل إرسال الملف: ' + error.message, 'error');
    } finally {
      if (this.previewSend) {
        this.previewSend.disabled = false;
        this.previewSend.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
          إرسال
        `;
      }
    }
  }
  
  readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
  
  addFileMessageToUI(fileMessage, isOutgoing = true) {
    const messageList = document.getElementById('messageList');
    if (!messageList) return;
    
    const chatEmpty = document.getElementById('chatEmpty');
    if (chatEmpty) chatEmpty.classList.add('hidden');
    
    const messageEl = document.createElement('div');
    messageEl.className = `message ${isOutgoing ? 'outgoing' : 'incoming'}`;
    
    const policyBadges = this.renderPolicyBadges(fileMessage.policies || []);
    const thumbnail = this.renderFileThumbnail(fileMessage);
    
    messageEl.innerHTML = `
      <div class="message-bubble">
        <div class="message-file">
          <div class="file-thumbnail">
            ${thumbnail}
            ${policyBadges ? `<div class="secure-overlay"><div class="policy-badges">${policyBadges}</div></div>` : ''}
          </div>
          <div class="file-details">
            <span class="file-name">${this.escapeHtml(fileMessage.filename)}</span>
            <span class="file-size">${this.formatFileSize(fileMessage.file_size)}</span>
          </div>
          <button class="file-action-btn" onclick="fileSharing.openFile('${fileMessage.file_id || ''}')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            عرض الملف
          </button>
        </div>
        <div class="message-meta">
          <span class="message-time">${this.formatTime(new Date())}</span>
        </div>
      </div>
    `;
    
    messageList.appendChild(messageEl);
    messageList.scrollTop = messageList.scrollHeight;
  }
  
  renderFileThumbnail(fileMessage) {
    if (fileMessage.file_type?.startsWith('image/') && fileMessage.data) {
      return `<img src="data:${fileMessage.file_type};base64,${fileMessage.data}" alt="Preview">`;
    }
    return `<div class="file-icon">${this.getFileIcon(fileMessage.file_type)}</div>`;
  }
  
  renderPolicyBadges(policies) {
    if (!policies || policies.length === 0) return '';
    
    const badges = policies.map(p => {
      const icons = {
        'view_once': '👁️',
        'time_limited': '⏱️'
      };
      return `<span class="policy-badge">${icons[p.type] || '🔒'}</span>`;
    });
    
    return badges.join('');
  }
  
  openFile(fileId, fileData = null) {
    // Check for view_once policy
    if (fileData?.policies?.some(p => p.type === 'view_once')) {
      this.pendingFileData = fileData;
      this.viewOnceModal?.classList.remove('hidden');
      return;
    }
    
    this.showSecureViewer(fileData || { file_id: fileId });
  }
  
  closeViewOnceWarning() {
    this.viewOnceModal?.classList.add('hidden');
    this.pendingFileData = null;
  }
  
  confirmViewOnce() {
    this.viewOnceModal?.classList.add('hidden');
    if (this.pendingFileData) {
      this.showSecureViewer(this.pendingFileData);
      this.pendingFileData = null;
    }
  }
  
  showSecureViewer(fileData) {
    if (!this.viewerModal) return;
    
    // Show loading
    this.viewerLoading?.classList.remove('hidden');
    this.viewerContent?.classList.add('hidden');
    
    // Update info
    if (this.viewerFilename) {
      this.viewerFilename.textContent = fileData.filename || 'ملف';
    }
    if (this.viewerSender) {
      this.viewerSender.textContent = `من: ${fileData.sender || 'مجهول'}`;
    }
    
    // Show policy badges
    if (this.viewerPolicies) {
      this.viewerPolicies.innerHTML = this.renderViewerPolicyBadges(fileData.policies || []);
    }
    
    // Check for time-limited policy
    const timeLimitedPolicy = fileData.policies?.find(p => p.type === 'time_limited');
    if (timeLimitedPolicy) {
      this.startTimer(timeLimitedPolicy.duration_seconds || 30);
    } else {
      this.viewerTimer?.classList.add('hidden');
    }
    
    // Show modal
    this.viewerModal.classList.remove('hidden');
    
    // Load content
    setTimeout(() => {
      this.renderViewerContent(fileData);
      this.viewerLoading?.classList.add('hidden');
      this.viewerContent?.classList.remove('hidden');
    }, 500);
  }
  
  renderViewerPolicyBadges(policies) {
    const badgeInfo = {
      'view_once': { class: 'view-once', text: 'عرض مرة واحدة' },
      'time_limited': { class: 'time-limited', text: 'محدود الوقت' }
    };
    
    return policies.map(p => {
      const info = badgeInfo[p.type];
      if (!info) return '';
      return `<span class="viewer-policy-badge ${info.class}">${info.text}</span>`;
    }).join('');
  }
  
  renderViewerContent(fileData) {
    if (!this.viewerContent) return;
    
    if (fileData.file_type?.startsWith('image/') && fileData.data) {
      this.viewerContent.innerHTML = `<img src="data:${fileData.file_type};base64,${fileData.data}" alt="Secure Image" draggable="false">`;
    } else if (fileData.file_type?.startsWith('video/') && fileData.data) {
      this.viewerContent.innerHTML = `<video src="data:${fileData.file_type};base64,${fileData.data}" controls controlsList="nodownload"></video>`;
    } else if (fileData.file_type?.startsWith('audio/') && fileData.data) {
      this.viewerContent.innerHTML = `<audio src="data:${fileData.file_type};base64,${fileData.data}" controls controlsList="nodownload"></audio>`;
    } else {
      this.viewerContent.innerHTML = `
        <div class="document-preview">
          ${this.getFileIcon(fileData.file_type)}
          <span>${fileData.filename || 'مستند'}</span>
          <p style="color: var(--text-muted); font-size: var(--font-size-sm);">
            لا يمكن عرض هذا النوع من الملفات مباشرة
          </p>
        </div>
      `;
    }
  }
  
  startTimer(seconds) {
    if (!this.viewerTimer || !this.timerDisplay) return;
    
    this.viewerTimer.classList.remove('hidden', 'warning');
    let remaining = seconds;
    
    const updateDisplay = () => {
      const mins = Math.floor(remaining / 60);
      const secs = remaining % 60;
      this.timerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      
      if (remaining <= 10) {
        this.viewerTimer.classList.add('warning');
      }
      
      if (remaining <= 0) {
        this.closeViewer();
        this.showToast('انتهى وقت عرض الملف', 'warning');
      }
    };
    
    updateDisplay();
    this.timerInterval = setInterval(() => {
      remaining--;
      updateDisplay();
    }, 1000);
  }
  
  closeViewer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    
    this.viewerModal?.classList.add('hidden');
    
    if (this.viewerContent) {
      this.viewerContent.innerHTML = '';
    }
    
    // Notify server that file was viewed/closed
    if (this.currentViewSession && window.socket) {
      window.socket.emit('file_view_closed', { session_id: this.currentViewSession });
    }
    this.currentViewSession = null;
  }
  
  closeAllModals() {
    this.closePreviewModal();
    this.closeViewer();
    this.closeViewOnceWarning();
  }
  
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
  
  formatTime(date) {
    return date.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
      success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
      error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
      warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
      info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };
    
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <div class="toast-content">
        <span class="toast-message">${message}</span>
      </div>
      <button class="toast-dismiss" onclick="this.parentElement.remove()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('hiding');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

// Initialize on DOM ready
let fileSharing;
document.addEventListener('DOMContentLoaded', () => {
  fileSharing = new FileSharing();
});
