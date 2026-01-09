/**
 * TOTP Settings Manager
 * Handles Two-Factor Authentication setup, disable, and backup code management
 */

var TOTPManager = {
  sessionId: null,
  secret: null,
  qrUri: null,
  backupCodes: [],
  newBackupCodes: [],
  currentStep: 1,
  isEnabled: false,
  initialized: false,
  
  // Initialize TOTP settings
  init: function() {
    if (this.initialized) return;
    this.initialized = true;
    console.log('TOTPManager initializing...');
    this.bindEvents();
  },
  
  // Bind all event listeners using event delegation
  bindEvents: function() {
    var self = this;
    
    // Use event delegation on document for all TOTP buttons
    document.addEventListener('click', function(e) {
      var target = e.target.closest('button');
      if (!target) return;
      
      var id = target.id;
      
      // Enable button
      if (id === 'totpEnableBtn') {
        console.log('Enable 2FA clicked');
        self.openSetupWizard();
      }
      // Disable button
      else if (id === 'totpDisableBtn') {
        self.openDisableModal();
      }
      // Regenerate button
      else if (id === 'totpRegenerateBtn') {
        self.openRegenerateModal();
      }
      // Setup wizard close
      else if (id === 'totpSetupClose') {
        self.closeSetupWizard();
      }
      // Setup wizard next
      else if (id === 'totpWizardNext') {
        self.nextStep();
      }
      // Setup wizard back
      else if (id === 'totpWizardBack') {
        self.prevStep();
      }
      // Copy secret
      else if (id === 'copySecretBtn') {
        self.copySecret();
      }
      // Copy backup codes
      else if (id === 'copyBackupCodesBtn') {
        self.copyBackupCodes();
      }
      // Download backup codes
      else if (id === 'downloadBackupCodesBtn') {
        self.downloadBackupCodes();
      }
      // Disable modal close
      else if (id === 'totpDisableClose' || id === 'totpDisableCancel') {
        self.closeDisableModal();
      }
      // Disable confirm
      else if (id === 'totpDisableConfirm') {
        self.confirmDisable();
      }
      // Regenerate modal close
      else if (id === 'totpRegenerateClose' || id === 'totpRegenerateCancel') {
        self.closeRegenerateModal();
      }
      // Regenerate confirm
      else if (id === 'totpRegenerateConfirm') {
        self.confirmRegenerate();
      }
      // Regenerate done
      else if (id === 'totpRegenerateDone') {
        self.closeRegenerateModal();
      }
      // Copy new backup codes
      else if (id === 'copyNewBackupCodesBtn') {
        self.copyNewBackupCodes();
      }
      // Download new backup codes
      else if (id === 'downloadNewBackupCodesBtn') {
        self.downloadNewBackupCodes();
      }
    });
    
    // Input event listeners
    document.addEventListener('input', function(e) {
      var target = e.target;
      var id = target.id;
      
      if (id === 'totpVerifyCode' || id === 'disableTotpCode' || id === 'regenerateTotpCode') {
        target.value = target.value.replace(/[^0-9]/g, '');
        
        // Auto-submit on 6 digits for verify code
        if (id === 'totpVerifyCode' && target.value.length === 6) {
          self.verifySetupCode();
        }
      }
    });
    
    // Keypress for enter key
    document.addEventListener('keypress', function(e) {
      if (e.key !== 'Enter') return;
      var target = e.target;
      var id = target.id;
      
      if (id === 'disableTotpCode' && target.value.length === 6) {
        self.confirmDisable();
      }
      else if (id === 'regenerateTotpCode' && target.value.length === 6) {
        self.confirmRegenerate();
      }
    });
    
    // Modal backdrop clicks
    document.addEventListener('click', function(e) {
      if (e.target.id === 'totpSetupModal') {
        self.closeSetupWizard();
      }
      else if (e.target.id === 'totpDisableModal') {
        self.closeDisableModal();
      }
      else if (e.target.id === 'totpRegenerateModal') {
        self.closeRegenerateModal();
      }
    });
    
    console.log('TOTPManager events bound');
  },
  
  // Load TOTP status from server
  loadStatus: function() {
    var self = this;
    console.log('Loading TOTP status...');
    
    var username = window.APP_STATE ? window.APP_STATE.me : '';
    apiPost('/api/totp/status', {username: username}).then(function(res) {
      console.log('TOTP status response:', res);
      if (res.ok) {
        self.isEnabled = res.enabled;
        self.updateStatusUI(res.enabled, res.backup_codes_count);
      } else {
        self.updateStatusUI(false, 0);
      }
    }).catch(function(err) {
      console.error('Failed to load TOTP status:', err);
      self.updateStatusUI(false, 0);
    });
  },
  
  // Update the status card UI
  updateStatusUI: function(enabled, backupCodesCount) {
    var statusIcon = document.getElementById('totpStatusIcon');
    var statusLabel = document.getElementById('totpStatusLabel');
    var statusDesc = document.getElementById('totpStatusDesc');
    var statusBadge = document.getElementById('totpStatusBadge');
    var enableBtn = document.getElementById('totpEnableBtn');
    var disableBtn = document.getElementById('totpDisableBtn');
    var regenerateBtn = document.getElementById('totpRegenerateBtn');
    
    console.log('Updating TOTP UI, enabled:', enabled);
    
    if (enabled) {
      if (statusIcon) statusIcon.className = 'totp-status-icon enabled';
      if (statusLabel) statusLabel.textContent = 'Two-Factor Authentication is ON';
      if (statusDesc) {
        var codesText = backupCodesCount !== undefined ? backupCodesCount + ' backup codes remaining' : 'Your account is protected';
        statusDesc.textContent = codesText;
      }
      if (statusBadge) statusBadge.innerHTML = '<span class="badge badge-enabled">Enabled</span>';
      if (enableBtn) enableBtn.style.display = 'none';
      if (disableBtn) disableBtn.style.display = 'inline-flex';
      if (regenerateBtn) regenerateBtn.style.display = 'inline-flex';
    } else {
      if (statusIcon) statusIcon.className = 'totp-status-icon disabled';
      if (statusLabel) statusLabel.textContent = 'Two-Factor Authentication is OFF';
      if (statusDesc) statusDesc.textContent = 'Add an extra layer of security to your account';
      if (statusBadge) statusBadge.innerHTML = '<span class="badge badge-disabled">Disabled</span>';
      if (enableBtn) enableBtn.style.display = 'inline-flex';
      if (disableBtn) disableBtn.style.display = 'none';
      if (regenerateBtn) regenerateBtn.style.display = 'none';
    }
  },

  // ============ Setup Wizard ============
  
  openSetupWizard: function() {
    console.log('Opening setup wizard');
    this.currentStep = 1;
    this.sessionId = null;
    this.secret = null;
    this.qrUri = null;
    this.backupCodes = [];
    
    var modal = document.getElementById('totpSetupModal');
    if (modal) {
      modal.classList.remove('hidden');
      this.updateWizardUI();
      console.log('Setup wizard opened');
    } else {
      console.error('totpSetupModal not found!');
    }
  },
  
  closeSetupWizard: function() {
    var modal = document.getElementById('totpSetupModal');
    if (modal) {
      modal.classList.add('hidden');
    }
    this.currentStep = 1;
    this.resetWizardUI();
  },
  
  updateWizardUI: function() {
    // Update step indicators
    for (var i = 1; i <= 4; i++) {
      var stepEl = document.querySelector('.wizard-step[data-step="' + i + '"]');
      if (stepEl) {
        stepEl.classList.remove('active', 'completed');
        if (i < this.currentStep) {
          stepEl.classList.add('completed');
        } else if (i === this.currentStep) {
          stepEl.classList.add('active');
        }
      }
    }
    
    // Show/hide panels
    for (var j = 1; j <= 4; j++) {
      var panel = document.getElementById('totpStep' + j);
      if (panel) {
        panel.classList.toggle('hidden', j !== this.currentStep);
      }
    }
    
    // Update buttons
    var backBtn = document.getElementById('totpWizardBack');
    var nextBtn = document.getElementById('totpWizardNext');
    
    if (backBtn) {
      backBtn.style.display = this.currentStep > 1 && this.currentStep < 4 ? 'inline-flex' : 'none';
    }
    
    if (nextBtn) {
      if (this.currentStep === 4) {
        nextBtn.textContent = 'Done';
      } else if (this.currentStep === 3) {
        nextBtn.textContent = 'Verify';
      } else {
        nextBtn.textContent = 'Next';
      }
    }
  },
  
  resetWizardUI: function() {
    var verifyInput = document.getElementById('totpVerifyCode');
    if (verifyInput) verifyInput.value = '';
    
    var verifyError = document.getElementById('verifyError');
    if (verifyError) verifyError.classList.add('hidden');
    
    var qrContainer = document.getElementById('qrContainer');
    if (qrContainer) {
      qrContainer.innerHTML = '<div class="qr-loading"><div class="loading-spinner"></div><span>Generating QR code...</span></div>';
    }
    
    var secretCode = document.getElementById('totpSecretCode');
    if (secretCode) secretCode.textContent = 'Loading...';
  },
  
  nextStep: function() {
    var self = this;
    
    if (this.currentStep === 1) {
      this.currentStep = 2;
      this.updateWizardUI();
      this.initiateSetup();
    } else if (this.currentStep === 2) {
      this.currentStep = 3;
      this.updateWizardUI();
      var verifyInput = document.getElementById('totpVerifyCode');
      if (verifyInput) {
        setTimeout(function() { verifyInput.focus(); }, 100);
      }
    } else if (this.currentStep === 3) {
      this.verifySetupCode();
    } else if (this.currentStep === 4) {
      this.closeSetupWizard();
      this.loadStatus();
    }
  },
  
  prevStep: function() {
    if (this.currentStep > 1 && this.currentStep < 4) {
      this.currentStep--;
      this.updateWizardUI();
    }
  },
  
  initiateSetup: function() {
    var self = this;
    console.log('Initiating TOTP setup...');
    
    // Get username from app state
    var username = window.APP_STATE ? window.APP_STATE.me : '';
    
    apiPost('/api/totp/setup', {username: username}).then(function(res) {
      console.log('Setup response:', res);
      if (res.ok) {
        self.sessionId = res.session_id;
        self.secret = res.secret;
        self.qrUri = res.qr_uri;
        self.displayQRCode(res.qr_uri);
        self.displaySecret(res.secret);
      } else {
        showToast(res.error || 'Failed to initiate 2FA setup', 'error');
        self.closeSetupWizard();
      }
    }).catch(function(err) {
      console.error('Setup error:', err);
      showToast('Failed to connect to server', 'error');
      self.closeSetupWizard();
    });
  },
  
  displayQRCode: function(qrUri) {
    var qrContainer = document.getElementById('qrContainer');
    if (!qrContainer) return;
    
    // Use external QR code API
    var img = document.createElement('img');
    img.src = 'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=' + encodeURIComponent(qrUri);
    img.alt = 'QR Code';
    img.style.width = '180px';
    img.style.height = '180px';
    qrContainer.innerHTML = '';
    qrContainer.appendChild(img);
  },
  
  displaySecret: function(secret) {
    var secretCode = document.getElementById('totpSecretCode');
    if (secretCode) {
      secretCode.textContent = secret;
    }
  },
  
  copySecret: function() {
    var self = this;
    if (this.secret) {
      navigator.clipboard.writeText(this.secret).then(function() {
        showToast('Secret copied to clipboard', 'success');
      }).catch(function() {
        showToast('Failed to copy', 'error');
      });
    }
  },
  
  verifySetupCode: function() {
    var self = this;
    var verifyInput = document.getElementById('totpVerifyCode');
    var verifyError = document.getElementById('verifyError');
    var verifyErrorText = document.getElementById('verifyErrorText');
    
    if (!verifyInput) return;
    
    var code = verifyInput.value.trim();
    if (code.length !== 6) {
      if (verifyError) verifyError.classList.remove('hidden');
      if (verifyErrorText) verifyErrorText.textContent = 'Please enter a 6-digit code';
      return;
    }
    
    if (verifyError) verifyError.classList.add('hidden');
    
    console.log('Verifying setup code...');
    apiPost('/api/totp/verify-setup', {
      code: code,
      session_id: this.sessionId
    }).then(function(res) {
      console.log('Verify response:', res);
      if (res.ok) {
        self.backupCodes = res.backup_codes || [];
        self.currentStep = 4;
        self.updateWizardUI();
        self.displayBackupCodes(self.backupCodes);
        showToast('Two-factor authentication enabled!', 'success');
      } else {
        if (verifyError) verifyError.classList.remove('hidden');
        if (verifyErrorText) verifyErrorText.textContent = res.error || 'Invalid code. Please try again.';
        verifyInput.value = '';
        verifyInput.focus();
      }
    }).catch(function(err) {
      console.error('Verify error:', err);
      if (verifyError) verifyError.classList.remove('hidden');
      if (verifyErrorText) verifyErrorText.textContent = 'Connection error. Please try again.';
    });
  },
  
  displayBackupCodes: function(codes) {
    var grid = document.getElementById('backupCodesGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    codes.forEach(function(code) {
      var div = document.createElement('div');
      div.className = 'backup-code';
      div.textContent = code;
      grid.appendChild(div);
    });
  },
  
  copyBackupCodes: function() {
    if (this.backupCodes.length > 0) {
      var text = 'Secure Messenger Backup Codes\n============================\n\n' +
                 this.backupCodes.join('\n') + '\n\nEach code can only be used once.';
      navigator.clipboard.writeText(text).then(function() {
        showToast('Backup codes copied to clipboard', 'success');
      }).catch(function() {
        showToast('Failed to copy', 'error');
      });
    }
  },
  
  downloadBackupCodes: function() {
    if (this.backupCodes.length > 0) {
      var text = 'Secure Messenger Backup Codes\n============================\n\n' +
                 'Generated: ' + new Date().toLocaleString() + '\n\n' +
                 this.backupCodes.join('\n') +
                 '\n\nIMPORTANT: Each code can only be used once.\nStore these codes in a safe place.';
      
      var blob = new Blob([text], { type: 'text/plain' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'secure-messenger-backup-codes.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('Backup codes downloaded', 'success');
    }
  },

  // ============ Disable Modal ============
  
  openDisableModal: function() {
    var modal = document.getElementById('totpDisableModal');
    var input = document.getElementById('disableTotpCode');
    var error = document.getElementById('disableError');
    
    if (modal) modal.classList.remove('hidden');
    if (input) {
      input.value = '';
      setTimeout(function() { input.focus(); }, 100);
    }
    if (error) error.classList.add('hidden');
  },
  
  closeDisableModal: function() {
    var modal = document.getElementById('totpDisableModal');
    if (modal) modal.classList.add('hidden');
  },
  
  confirmDisable: function() {
    var self = this;
    var input = document.getElementById('disableTotpCode');
    var error = document.getElementById('disableError');
    var errorText = document.getElementById('disableErrorText');
    
    if (!input) return;
    
    var code = input.value.trim();
    if (code.length !== 6) {
      if (error) error.classList.remove('hidden');
      if (errorText) errorText.textContent = 'Please enter a 6-digit code';
      return;
    }
    
    if (error) error.classList.add('hidden');
    
    var username = window.APP_STATE ? window.APP_STATE.me : '';
    apiPost('/api/totp/disable', { username: username, code: code }).then(function(res) {
      if (res.ok) {
        self.closeDisableModal();
        self.loadStatus();
        showToast('Two-factor authentication disabled', 'success');
      } else {
        if (error) error.classList.remove('hidden');
        if (errorText) errorText.textContent = res.error || 'Invalid code. Please try again.';
        input.value = '';
        input.focus();
      }
    }).catch(function() {
      if (error) error.classList.remove('hidden');
      if (errorText) errorText.textContent = 'Connection error. Please try again.';
    });
  },
  
  // ============ Regenerate Modal ============
  
  openRegenerateModal: function() {
    var modal = document.getElementById('totpRegenerateModal');
    var input = document.getElementById('regenerateTotpCode');
    var error = document.getElementById('regenerateError');
    var verifyStep = document.getElementById('regenerateVerifyStep');
    var codesStep = document.getElementById('regenerateCodesStep');
    var confirmBtn = document.getElementById('totpRegenerateConfirm');
    var doneBtn = document.getElementById('totpRegenerateDone');
    var cancelBtn = document.getElementById('totpRegenerateCancel');
    
    if (modal) modal.classList.remove('hidden');
    if (input) {
      input.value = '';
      setTimeout(function() { input.focus(); }, 100);
    }
    if (error) error.classList.add('hidden');
    if (verifyStep) verifyStep.classList.remove('hidden');
    if (codesStep) codesStep.classList.add('hidden');
    if (confirmBtn) confirmBtn.classList.remove('hidden');
    if (doneBtn) doneBtn.classList.add('hidden');
    if (cancelBtn) cancelBtn.classList.remove('hidden');
  },
  
  closeRegenerateModal: function() {
    var modal = document.getElementById('totpRegenerateModal');
    if (modal) modal.classList.add('hidden');
    this.loadStatus();
  },
  
  confirmRegenerate: function() {
    var self = this;
    var input = document.getElementById('regenerateTotpCode');
    var error = document.getElementById('regenerateError');
    var errorText = document.getElementById('regenerateErrorText');
    
    if (!input) return;
    
    var code = input.value.trim();
    if (code.length !== 6) {
      if (error) error.classList.remove('hidden');
      if (errorText) errorText.textContent = 'Please enter a 6-digit code';
      return;
    }
    
    if (error) error.classList.add('hidden');
    
    var username = window.APP_STATE ? window.APP_STATE.me : '';
    apiPost('/api/totp/regenerate-backup', { username: username, code: code }).then(function(res) {
      if (res.ok) {
        self.newBackupCodes = res.backup_codes || [];
        self.showNewBackupCodes();
        showToast('New backup codes generated!', 'success');
      } else {
        if (error) error.classList.remove('hidden');
        if (errorText) errorText.textContent = res.error || 'Invalid code. Please try again.';
        input.value = '';
        input.focus();
      }
    }).catch(function() {
      if (error) error.classList.remove('hidden');
      if (errorText) errorText.textContent = 'Connection error. Please try again.';
    });
  },
  
  showNewBackupCodes: function() {
    var verifyStep = document.getElementById('regenerateVerifyStep');
    var codesStep = document.getElementById('regenerateCodesStep');
    var confirmBtn = document.getElementById('totpRegenerateConfirm');
    var doneBtn = document.getElementById('totpRegenerateDone');
    var cancelBtn = document.getElementById('totpRegenerateCancel');
    var grid = document.getElementById('newBackupCodesGrid');
    
    if (verifyStep) verifyStep.classList.add('hidden');
    if (codesStep) codesStep.classList.remove('hidden');
    if (confirmBtn) confirmBtn.classList.add('hidden');
    if (doneBtn) doneBtn.classList.remove('hidden');
    if (cancelBtn) cancelBtn.classList.add('hidden');
    
    if (grid && this.newBackupCodes) {
      grid.innerHTML = '';
      var self = this;
      this.newBackupCodes.forEach(function(code) {
        var div = document.createElement('div');
        div.className = 'backup-code';
        div.textContent = code;
        grid.appendChild(div);
      });
    }
  },
  
  copyNewBackupCodes: function() {
    if (this.newBackupCodes && this.newBackupCodes.length > 0) {
      var text = 'Secure Messenger Backup Codes\n============================\n\n' +
                 this.newBackupCodes.join('\n') + '\n\nEach code can only be used once.';
      navigator.clipboard.writeText(text).then(function() {
        showToast('Backup codes copied to clipboard', 'success');
      }).catch(function() {
        showToast('Failed to copy', 'error');
      });
    }
  },
  
  downloadNewBackupCodes: function() {
    if (this.newBackupCodes && this.newBackupCodes.length > 0) {
      var text = 'Secure Messenger Backup Codes\n============================\n\n' +
                 'Generated: ' + new Date().toLocaleString() + '\n\n' +
                 this.newBackupCodes.join('\n') +
                 '\n\nIMPORTANT: Each code can only be used once.\nStore these codes in a safe place.';
      
      var blob = new Blob([text], { type: 'text/plain' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'secure-messenger-backup-codes.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('Backup codes downloaded', 'success');
    }
  }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM loaded, initializing TOTPManager');
  TOTPManager.init();
});

// Also hook into SettingsPanel.open to load status
(function() {
  var checkSettingsPanel = setInterval(function() {
    if (typeof SettingsPanel !== 'undefined' && SettingsPanel.open) {
      var originalOpen = SettingsPanel.open;
      SettingsPanel.open = function() {
        originalOpen.call(this);
        console.log('Settings panel opened, loading TOTP status');
        TOTPManager.loadStatus();
      };
      clearInterval(checkSettingsPanel);
      console.log('SettingsPanel.open hooked');
    }
  }, 100);
  
  // Stop checking after 10 seconds
  setTimeout(function() {
    clearInterval(checkSettingsPanel);
  }, 10000);
})();
