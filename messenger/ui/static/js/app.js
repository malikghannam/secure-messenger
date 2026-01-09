/**
 * Secure Messenger - Modern Chat UI
 * WhatsApp Web / Signal Desktop Style
 * Fixed: No polling, WebSocket only, notifications for all messages
 */

/* ============================================
   STATE MANAGEMENT
   ============================================ */
var AppState = {
  me: null,
  contacts: [],
  messages: {},
  renderedIds: {},
  unreadCounts: {},
  ui: {
    currentPeer: null,
    connectionStatus: 'disconnected',
    isSending: false,
    isAtBottom: true
  }
};

var StateManager = {
  addContact: function(username) {
    if (AppState.contacts.indexOf(username) === -1 && username !== AppState.me) {
      AppState.contacts.push(username);
      AppState.contacts.sort();
      return true;
    }
    return false;
  },
  
  setContacts: function(contacts) {
    AppState.contacts = contacts.filter(function(u) { return u !== AppState.me; }).sort();
  },
  
  createMessageId: function(msg) {
    return (msg.ts || '') + '-' + (msg.text || '').substring(0, 20) + '-' + (msg.dir || '');
  },
  
  isMessageRendered: function(peer, msgId) {
    if (!AppState.renderedIds[peer]) {
      AppState.renderedIds[peer] = {};
    }
    return AppState.renderedIds[peer][msgId] === true;
  },
  
  markMessageRendered: function(peer, msgId) {
    if (!AppState.renderedIds[peer]) {
      AppState.renderedIds[peer] = {};
    }
    AppState.renderedIds[peer][msgId] = true;
  },
  
  clearPeerMessages: function(peer) {
    AppState.messages[peer] = [];
    AppState.renderedIds[peer] = {};
  },
  
  addMessage: function(peer, message) {
    if (!AppState.messages[peer]) {
      AppState.messages[peer] = [];
    }
    var msgId = message.id || this.createMessageId(message);
    message.id = msgId;
    if (this.isMessageRendered(peer, msgId)) {
      return false;
    }
    AppState.messages[peer].push(message);
    return true;
  },
  
  updateMessageStatus: function(messageId, status) {
    for (var peer in AppState.messages) {
      var msgs = AppState.messages[peer];
      for (var i = 0; i < msgs.length; i++) {
        if (msgs[i].id === messageId) {
          msgs[i].status = status;
          return true;
        }
      }
    }
    return false;
  },
  
  setCurrentPeer: function(peer) {
    AppState.ui.currentPeer = peer;
    this.clearUnread(peer);
  },
  
  incrementUnread: function(peer) {
    AppState.unreadCounts[peer] = (AppState.unreadCounts[peer] || 0) + 1;
  },
  
  clearUnread: function(peer) {
    AppState.unreadCounts[peer] = 0;
  },
  
  getUnread: function(peer) {
    return AppState.unreadCounts[peer] || 0;
  }
};

/* ============================================
   DOM REFERENCES
   ============================================ */
var DOM = {
  app: null,
  contactList: null,
  messageList: null,
  messageInput: null,
  sendButton: null,
  searchInput: null,
  connectionStatus: null,
  peerName: null,
  peerAvatar: null,
  peerStatus: null,
  toastContainer: null,
  chatEmpty: null,
  scrollToBottom: null,
  contactEmpty: null
};

function initDOMReferences() {
  DOM.app = document.getElementById('app');
  DOM.contactList = document.getElementById('contactList');
  DOM.messageList = document.getElementById('messageList');
  DOM.messageInput = document.getElementById('messageInput');
  DOM.sendButton = document.getElementById('sendButton');
  DOM.searchInput = document.getElementById('searchInput');
  DOM.connectionStatus = document.getElementById('connectionStatus');
  DOM.peerName = document.getElementById('peerName');
  DOM.peerAvatar = document.getElementById('peerAvatar');
  DOM.peerStatus = document.getElementById('peerStatus');
  DOM.toastContainer = document.getElementById('toastContainer');
  DOM.chatEmpty = document.getElementById('chatEmpty');
  DOM.scrollToBottom = document.getElementById('scrollToBottom');
  DOM.contactEmpty = document.getElementById('contactEmpty');
}

/* ============================================
   UTILITY FUNCTIONS
   ============================================ */
function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function formatTimestamp(ts) {
  try {
    var date = new Date(ts);
    var now = new Date();
    var diffMs = now - date;
    var diffMins = Math.floor(diffMs / 60000);
    var diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return diffMins + 'm';
    if (diffHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch (e) {
    return '';
  }
}

function debounce(fn, delay) {
  var timeout;
  return function() {
    var args = arguments;
    var self = this;
    clearTimeout(timeout);
    timeout = setTimeout(function() { fn.apply(self, args); }, delay);
  };
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

/* ============================================
   API FUNCTIONS
   ============================================ */
function apiGet(url) {
  return fetch(url, { credentials: 'same-origin' })
    .then(function(response) { return response.text(); })
    .then(function(text) {
      try { return JSON.parse(text); }
      catch (e) { return { ok: false, error: 'invalid_json' }; }
    })
    .catch(function(error) {
      console.error('API GET error:', url, error);
      return { ok: false, error: 'network' };
    });
}

function apiPost(url, body) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body)
  })
    .then(function(response) { return response.text(); })
    .then(function(text) {
      try { return JSON.parse(text); }
      catch (e) { return { ok: false, error: 'invalid_json' }; }
    })
    .catch(function(error) {
      console.error('API POST error:', url, error);
      return { ok: false, error: 'network' };
    });
}

/* ============================================
   RENDER FUNCTIONS
   ============================================ */
function renderContact(username) {
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'contact-item';
  btn.dataset.peer = username;
  btn.setAttribute('aria-label', 'Chat with ' + username);
  
  var initial = username.charAt(0).toUpperCase();
  var unreadCount = StateManager.getUnread(username);
  var hiddenClass = unreadCount > 0 ? '' : 'hidden';
  
  btn.innerHTML = '<div class="contact-avatar" aria-hidden="true">' + initial + '</div>' +
    '<div class="contact-details">' +
    '<div class="contact-name">' + escapeHtml(username) + '</div>' +
    '<div class="contact-preview"></div>' +
    '</div>' +
    '<div class="contact-meta">' +
    '<div class="contact-time"></div>' +
    '<div class="unread-badge ' + hiddenClass + '" data-badge="' + username + '">' + unreadCount + '</div>' +
    '</div>';
  
  return btn;
}

function appendContact(username) {
  if (!DOM.contactList) return;
  
  var existing = DOM.contactList.querySelector('[data-peer="' + username + '"]');
  if (existing) return;
  
  var contactEl = renderContact(username);
  var contacts = DOM.contactList.querySelectorAll('.contact-item');
  var inserted = false;
  
  for (var i = 0; i < contacts.length; i++) {
    if (contacts[i].dataset.peer > username) {
      DOM.contactList.insertBefore(contactEl, contacts[i]);
      inserted = true;
      break;
    }
  }
  
  if (!inserted) {
    var emptyState = DOM.contactList.querySelector('.contact-empty');
    if (emptyState) {
      DOM.contactList.insertBefore(contactEl, emptyState);
    } else {
      DOM.contactList.appendChild(contactEl);
    }
  }
  
  if (DOM.contactEmpty) {
    DOM.contactEmpty.classList.add('hidden');
  }
}

function updateContactBadge(peer, count) {
  var badge = document.querySelector('[data-badge="' + peer + '"]');
  if (badge) {
    badge.textContent = count;
    badge.classList.toggle('hidden', count === 0);
  }
}

function setActiveContact(peer) {
  var contacts = DOM.contactList ? DOM.contactList.querySelectorAll('.contact-item') : [];
  for (var i = 0; i < contacts.length; i++) {
    contacts[i].classList.toggle('active', contacts[i].dataset.peer === peer);
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'sending': return '⏳';
    case 'sent': return '✓';
    case 'delivered': return '✓✓';
    case 'failed': return '⚠️';
    default: return '✓';
  }
}

function renderMessage(message) {
  var div = document.createElement('div');
  var dirClass = message.dir === 'out' ? 'outgoing' : 'incoming';
  div.className = 'message ' + dirClass;
  if (message.status === 'sending') {
    div.classList.add('optimistic');
  }
  div.dataset.messageId = message.id;
  
  var statusIcon = getStatusIcon(message.status);
  var timeStr = formatTimestamp(message.ts);
  var statusHtml = message.dir === 'out' ? '<span class="message-status ' + (message.status || 'sent') + '">' + statusIcon + '</span>' : '';
  
  // Check if this is a file message
  var messageContent = '';
  if (message.text && message.text.startsWith('[FILE:') && message.text.endsWith(']')) {
    try {
      var fileJson = message.text.substring(6, message.text.length - 1);
      var fileData = JSON.parse(fileJson);
      messageContent = renderFileMessage(fileData, message.dir === 'out');
    } catch (e) {
      console.error('Failed to parse file message:', e);
      messageContent = '<div class="message-text">[ملف تالف]</div>';
    }
  } else {
    messageContent = '<div class="message-text">' + escapeHtml(message.text) + '</div>';
  }
  
  div.innerHTML = '<div class="message-bubble">' +
    messageContent +
    '<div class="message-meta">' +
    '<span class="message-time">' + timeStr + '</span>' +
    statusHtml +
    '</div>' +
    '</div>';
  
  return div;
}

/* ============================================
   FILE POLICY TRACKING SYSTEM (Simplified: view_once + time_limited only)
   ============================================ */
var FilePolicyTracker = {
  STORAGE_KEY: 'secure_file_policies',
  
  generateFileId: function(fileData) {
    var str = fileData.filename + '_' + fileData.file_size + '_' + (fileData.data ? fileData.data.substring(0, 100) : '');
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
      var char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return 'file_' + Math.abs(hash).toString(36);
  },
  
  getTrackedFiles: function() {
    try {
      return JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '{}');
    } catch (e) {
      return {};
    }
  },
  
  saveTrackedFiles: function(data) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.error('Failed to save file tracking data');
    }
  },
  
  isFileBlocked: function(fileId) {
    var tracked = this.getTrackedFiles();
    return tracked[fileId] && tracked[fileId].blocked === true;
  },
  
  // Block file after time_limited expires
  blockFileAfterTimer: function(fileId) {
    var tracked = this.getTrackedFiles();
    if (!tracked[fileId]) {
      tracked[fileId] = {};
    }
    tracked[fileId].blocked = true;
    tracked[fileId].blockedReason = 'انتهت مدة العرض المحددة';
    this.saveTrackedFiles(tracked);
  },
  
  recordView: function(fileId, policies) {
    var tracked = this.getTrackedFiles();
    if (!tracked[fileId]) {
      tracked[fileId] = { viewCount: 0, firstViewed: new Date().toISOString() };
    }
    tracked[fileId].viewCount = (tracked[fileId].viewCount || 0) + 1;
    tracked[fileId].lastViewed = new Date().toISOString();
    
    // Block after view_once
    var hasViewOnce = policies && policies.some(function(p) { return p.type === 'view_once'; });
    if (hasViewOnce) {
      tracked[fileId].blocked = true;
      tracked[fileId].blockedReason = 'تم عرض هذا الملف مسبقاً (عرض مرة واحدة)';
    }
    
    this.saveTrackedFiles(tracked);
    return tracked[fileId];
  },
  
  checkPolicies: function(fileId, policies) {
    var result = { canView: true, reason: null };
    var tracked = this.getTrackedFiles();
    
    if (tracked[fileId] && tracked[fileId].blocked) {
      result.canView = false;
      result.reason = tracked[fileId].blockedReason || 'تم حظر هذا الملف';
      return result;
    }
    
    return result;
  }
};

function renderFileMessage(fileData, isOutgoing) {
  var hasPolicies = fileData.policies && fileData.policies.length > 0;
  var fileId = FilePolicyTracker.generateFileId(fileData);
  
  if (!window.fileDataStore) window.fileDataStore = {};
  window.fileDataStore[fileId] = fileData;
  
  var policyStatus = FilePolicyTracker.checkPolicies(fileId, fileData.policies);
  var isBlocked = !policyStatus.canView;
  
  // Check if file type is viewable
  var isViewable = fileData.file_type && (
    fileData.file_type.startsWith('image/') ||
    fileData.file_type.startsWith('video/') ||
    fileData.file_type === 'application/pdf' ||
    fileData.file_type === 'text/plain' ||
    (fileData.filename && fileData.filename.endsWith('.txt'))
  );
  
  var thumbnail = '';
  if (fileData.file_type && fileData.file_type.startsWith('image/') && fileData.data) {
    if (isBlocked) {
      thumbnail = '<div style="position:relative;background:#333;padding:30px;border-radius:8px;text-align:center;"><div style="color:#ff6b6b;font-size:24px;">🚫</div><div style="color:#999;font-size:11px;margin-top:8px;">' + escapeHtml(policyStatus.reason || 'محظور') + '</div></div>';
    } else if (hasPolicies) {
      thumbnail = '<div style="position:relative;"><img src="data:' + fileData.file_type + ';base64,' + fileData.data + '" alt="Preview" style="max-width:200px;max-height:200px;border-radius:8px;filter:blur(10px);"><div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.7);color:white;padding:8px 16px;border-radius:20px;font-size:12px;">🔒 اضغط للعرض الآمن</div></div>';
    } else {
      // No policies - clickable to view larger
      thumbnail = '<img src="data:' + fileData.file_type + ';base64,' + fileData.data + '" alt="Preview" style="max-width:200px;max-height:200px;border-radius:8px;cursor:pointer;" onclick="openImageViewer(\'' + fileId + '\')">';
    }
  } else if (fileData.file_type === 'application/pdf') {
    // PDF icon with click handler
    var pdfIcon = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#e74c3c" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><text x="7" y="17" font-size="6" fill="#e74c3c" stroke="none">PDF</text></svg>';
    if (isBlocked) {
      thumbnail = '<div style="position:relative;background:#333;padding:30px;border-radius:8px;text-align:center;"><div style="color:#ff6b6b;font-size:24px;">🚫</div><div style="color:#999;font-size:11px;margin-top:8px;">' + escapeHtml(policyStatus.reason || 'محظور') + '</div></div>';
    } else if (hasPolicies) {
      thumbnail = '<div style="position:relative;background:#f8f9fa;padding:20px;border-radius:8px;text-align:center;">' + pdfIcon + '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.7);color:white;padding:8px 16px;border-radius:20px;font-size:12px;">🔒 اضغط للعرض الآمن</div></div>';
    } else {
      thumbnail = '<div class="file-icon" style="padding:10px;background:#f8f9fa;border-radius:8px;cursor:pointer;" onclick="openImageViewer(\'' + fileId + '\')">' + pdfIcon + '</div>';
    }
  } else if (fileData.file_type === 'text/plain' || (fileData.filename && fileData.filename.endsWith('.txt'))) {
    // Text file icon
    var txtIcon = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="8" y1="13" x2="16" y2="13"></line><line x1="8" y1="17" x2="14" y2="17"></line></svg>';
    if (isBlocked) {
      thumbnail = '<div style="position:relative;background:#333;padding:30px;border-radius:8px;text-align:center;"><div style="color:#ff6b6b;font-size:24px;">🚫</div><div style="color:#999;font-size:11px;margin-top:8px;">' + escapeHtml(policyStatus.reason || 'محظور') + '</div></div>';
    } else if (hasPolicies) {
      thumbnail = '<div style="position:relative;background:#f8f9fa;padding:20px;border-radius:8px;text-align:center;">' + txtIcon + '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.7);color:white;padding:8px 16px;border-radius:20px;font-size:12px;">🔒 اضغط للعرض الآمن</div></div>';
    } else {
      thumbnail = '<div class="file-icon" style="padding:10px;background:#f8f9fa;border-radius:8px;cursor:pointer;" onclick="openImageViewer(\'' + fileId + '\')">' + txtIcon + '</div>';
    }
  } else {
    var icon = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
    thumbnail = '<div class="file-icon" style="padding:10px;">' + icon + '</div>';
  }
  
  var policyBadges = '';
  if (hasPolicies) {
    fileData.policies.forEach(function(p) {
      if (p.type === 'view_once') {
        policyBadges += '<span class="policy-badge" title="عرض مرة واحدة" style="margin-left:4px;">👁️</span>';
      } else if (p.type === 'time_limited') {
        policyBadges += '<span class="policy-badge" title="محدود الوقت (' + (p.duration_seconds || 30) + ' ثانية)" style="margin-left:4px;">⏱️</span>';
      }
    });
  }
  
  var fileSize = formatFileSize(fileData.file_size || 0);
  var clickHandler = (hasPolicies && !isBlocked) ? 'onclick="openSecureFile(\'' + fileId + '\')"' : '';
  var cursorStyle = (hasPolicies && !isBlocked) ? 'cursor:pointer;' : '';
  
  return '<div class="message-file" style="display:flex;flex-direction:column;gap:8px;' + cursorStyle + '" ' + clickHandler + '>' +
    '<div class="file-thumbnail" style="position:relative;">' + thumbnail + '</div>' +
    '<div class="file-details" style="display:flex;flex-direction:column;">' +
    '<span class="file-name" style="font-weight:500;word-break:break-all;">' + escapeHtml(fileData.filename) + '</span>' +
    '<span class="file-size" style="font-size:12px;color:var(--text-muted);">' + fileSize + '</span>' +
    (policyBadges ? '<div class="policy-badges" style="margin-top:4px;">' + policyBadges + '</div>' : '') +
    '</div>' +
    '</div>';
}

// Simple file viewer for files without policies
function openImageViewer(fileId) {
  var fileData = window.fileDataStore ? window.fileDataStore[fileId] : null;
  if (!fileData) return;
  
  var modal = document.createElement('div');
  modal.id = 'imageViewerModal';
  modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);z-index:10000;display:flex;align-items:center;justify-content:center;';
  
  var content = '';
  if (fileData.file_type && fileData.file_type.startsWith('image/')) {
    content = '<img src="data:' + fileData.file_type + ';base64,' + fileData.data + '" style="max-width:95vw;max-height:95vh;border-radius:8px;" onclick="event.stopPropagation();">';
  } else if (fileData.file_type && fileData.file_type.startsWith('video/')) {
    content = '<video src="data:' + fileData.file_type + ';base64,' + fileData.data + '" controls style="max-width:95vw;max-height:95vh;" onclick="event.stopPropagation();"></video>';
  } else if (fileData.file_type === 'application/pdf') {
    content = '<iframe src="data:application/pdf;base64,' + fileData.data + '" style="width:90vw;height:90vh;border:none;border-radius:8px;background:white;" onclick="event.stopPropagation();"></iframe>';
  } else if (fileData.file_type === 'text/plain' || fileData.filename.endsWith('.txt')) {
    try {
      var textContent = atob(fileData.data);
      content = '<div style="background:white;padding:20px;border-radius:8px;max-width:90vw;max-height:85vh;overflow:auto;text-align:left;direction:ltr;" onclick="event.stopPropagation();"><pre style="margin:0;white-space:pre-wrap;word-wrap:break-word;font-family:monospace;font-size:14px;color:#333;">' + escapeHtml(textContent) + '</pre></div>';
    } catch (e) {
      content = '<div style="background:white;padding:40px;border-radius:8px;text-align:center;"><p style="color:#e74c3c;">فشل في قراءة الملف النصي</p></div>';
    }
  } else {
    content = '<div style="background:white;padding:40px;border-radius:8px;text-align:center;"><svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg><p style="margin-top:20px;color:#333;">' + escapeHtml(fileData.filename) + '</p></div>';
  }
  
  modal.innerHTML = '<button style="position:absolute;top:20px;right:20px;background:rgba(255,255,255,0.2);border:none;color:white;width:40px;height:40px;border-radius:50%;cursor:pointer;font-size:20px;z-index:10001;" onclick="document.getElementById(\'imageViewerModal\').remove()">✕</button>' + content;
  document.body.appendChild(modal);
  
  // Close on background click
  modal.onclick = function(e) {
    if (e.target === modal) modal.remove();
  };
  
  document.addEventListener('keydown', function closeOnEsc(e) {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', closeOnEsc);
    }
  });
}

// Secure file viewer with policy enforcement
function openSecureFile(fileId) {
  var fileData = window.fileDataStore ? window.fileDataStore[fileId] : null;
  if (!fileData) {
    showToast('لم يتم العثور على الملف', 'error');
    return;
  }
  
  var policyStatus = FilePolicyTracker.checkPolicies(fileId, fileData.policies);
  if (!policyStatus.canView) {
    showToast(policyStatus.reason, 'error');
    return;
  }
  
  showSecureFileModal(fileId, fileData);
}

function showSecureFileModal(fileId, fileData) {
  var policies = fileData.policies || [];
  var hasViewOnce = policies.some(function(p) { return p.type === 'view_once'; });
  var timeLimitedPolicy = policies.find(function(p) { return p.type === 'time_limited'; });
  
  // Warning for view_once
  if (hasViewOnce) {
    if (!confirm('⚠️ تحذير: هذا الملف للعرض مرة واحدة فقط!\n\nبعد إغلاق هذه النافذة، لن تتمكن من عرض الملف مرة أخرى.\n\nهل تريد المتابعة؟')) {
      return;
    }
  }
  
  // Warning for time_limited
  if (timeLimitedPolicy) {
    if (!confirm('⚠️ تحذير: هذا الملف محدود الوقت!\n\nلديك ' + (timeLimitedPolicy.duration_seconds || 30) + ' ثانية لعرض الملف.\nبعد انتهاء الوقت، سيتم حظر الملف نهائياً.\n\nهل تريد المتابعة؟')) {
      return;
    }
  }
  
  // Record view (blocks view_once immediately)
  FilePolicyTracker.recordView(fileId, policies);
  
  // Create modal
  var modal = document.createElement('div');
  modal.id = 'secureFileModal';
  modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.95);z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;';
  
  // Policy badges
  var policyInfo = '';
  if (hasViewOnce) policyInfo += '<span style="background:#e74c3c;color:white;padding:5px 15px;border-radius:15px;margin:0 5px;">👁️ عرض مرة واحدة</span>';
  if (timeLimitedPolicy) policyInfo += '<span style="background:#f39c12;color:white;padding:5px 15px;border-radius:15px;margin:0 5px;">⏱️ محدود الوقت</span>';
  
  // Timer display
  var timerHtml = '';
  if (timeLimitedPolicy) {
    timerHtml = '<div id="secureFileTimer" style="position:absolute;top:20px;right:20px;background:#e74c3c;color:white;padding:15px 25px;border-radius:30px;font-size:24px;font-weight:bold;">⏱️ ' + (timeLimitedPolicy.duration_seconds || 30) + '</div>';
  }
  
  // Content
  var content = '';
  if (fileData.file_type && fileData.file_type.startsWith('image/')) {
    content = '<img src="data:' + fileData.file_type + ';base64,' + fileData.data + '" style="max-width:90vw;max-height:70vh;border-radius:8px;" draggable="false" oncontextmenu="return false;">';
  } else if (fileData.file_type && fileData.file_type.startsWith('video/')) {
    content = '<video src="data:' + fileData.file_type + ';base64,' + fileData.data + '" controls controlsList="nodownload" style="max-width:90vw;max-height:70vh;"></video>';
  } else if (fileData.file_type === 'application/pdf') {
    // PDF viewer using iframe
    content = '<iframe src="data:application/pdf;base64,' + fileData.data + '" style="width:90vw;height:80vh;border:none;border-radius:8px;background:white;"></iframe>';
  } else if (fileData.file_type === 'text/plain' || fileData.filename.endsWith('.txt')) {
    // Text file viewer
    try {
      var textContent = atob(fileData.data);
      content = '<div style="background:white;padding:20px;border-radius:8px;max-width:90vw;max-height:70vh;overflow:auto;text-align:left;direction:ltr;"><pre style="margin:0;white-space:pre-wrap;word-wrap:break-word;font-family:monospace;font-size:14px;color:#333;">' + escapeHtml(textContent) + '</pre></div>';
    } catch (e) {
      content = '<div style="background:white;padding:40px;border-radius:8px;text-align:center;"><p style="color:#e74c3c;">فشل في قراءة الملف النصي</p></div>';
    }
  } else {
    content = '<div style="background:white;padding:40px;border-radius:8px;text-align:center;"><svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg><p style="margin-top:20px;color:#333;">' + escapeHtml(fileData.filename) + '</p><p style="color:#999;font-size:12px;">لا يمكن عرض هذا النوع من الملفات مباشرة</p></div>';
  }
  
  modal.innerHTML = '<button onclick="closeSecureFileModal(\'' + fileId + '\')" style="position:absolute;top:20px;left:20px;background:rgba(255,255,255,0.2);border:none;color:white;width:40px;height:40px;border-radius:50%;cursor:pointer;font-size:20px;">✕</button>' +
    timerHtml +
    '<div style="margin-bottom:20px;">' + policyInfo + '</div>' +
    content +
    '<div style="color:white;margin-top:20px;font-size:14px;">' + escapeHtml(fileData.filename) + '</div>';
  
  document.body.appendChild(modal);
  modal.addEventListener('contextmenu', function(e) { e.preventDefault(); });
  
  // Timer for time_limited - BLOCKS file after expiry
  if (timeLimitedPolicy) {
    var remaining = timeLimitedPolicy.duration_seconds || 30;
    var timerEl = document.getElementById('secureFileTimer');
    var timerInterval = setInterval(function() {
      remaining--;
      if (timerEl) {
        timerEl.textContent = '⏱️ ' + remaining;
        if (remaining <= 10) {
          timerEl.style.background = '#c0392b';
          timerEl.style.animation = 'pulse 0.5s infinite';
        }
      }
      if (remaining <= 0) {
        clearInterval(timerInterval);
        // BLOCK the file permanently
        FilePolicyTracker.blockFileAfterTimer(fileId);
        closeSecureFileModal(fileId);
        showToast('انتهى وقت العرض - تم حظر الملف', 'warning');
      }
    }, 1000);
    modal.dataset.timerInterval = timerInterval;
  }
  
  document.addEventListener('keydown', handleSecureModalEscape);
}

// Close secure file modal and cleanup
function closeSecureFileModal(fileId) {
  var modal = document.getElementById('secureFileModal');
  if (!modal) return;
  
  // Clear timer if exists
  if (modal.dataset.timerInterval) {
    clearInterval(parseInt(modal.dataset.timerInterval));
  }
  
  // Remove escape key listener
  document.removeEventListener('keydown', handleSecureModalEscape);
  
  // Remove modal
  modal.remove();
  
  // Refresh message list to show blocked status
  if (AppState.ui.currentPeer) {
    clearMessageList();
    StateManager.clearPeerMessages(AppState.ui.currentPeer);
    loadHistory(AppState.ui.currentPeer);
  }
}

// Handle Escape key to close secure modal
function handleSecureModalEscape(e) {
  if (e.key === 'Escape') {
    var modal = document.getElementById('secureFileModal');
    if (modal) {
      // Get fileId from modal if needed
      var closeBtn = modal.querySelector('button');
      if (closeBtn && closeBtn.onclick) {
        // Extract fileId from onclick
        var match = closeBtn.getAttribute('onclick');
        if (match) {
          var fileIdMatch = match.match(/closeSecureFileModal\('([^']+)'\)/);
          if (fileIdMatch) {
            closeSecureFileModal(fileIdMatch[1]);
            return;
          }
        }
      }
      // Fallback: just close without fileId
      closeSecureFileModal(null);
    }
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  var k = 1024;
  var sizes = ['B', 'KB', 'MB', 'GB'];
  var i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function appendMessage(message) {
  var peer = AppState.ui.currentPeer;
  if (!peer || !DOM.messageList) return false;
  
  var msgId = message.id || StateManager.createMessageId(message);
  message.id = msgId;
  
  if (StateManager.isMessageRendered(peer, msgId)) {
    return false;
  }
  
  if (DOM.chatEmpty) {
    DOM.chatEmpty.classList.add('hidden');
  }
  
  var messageEl = renderMessage(message);
  DOM.messageList.appendChild(messageEl);
  StateManager.markMessageRendered(peer, msgId);
  StateManager.addMessage(peer, message);
  
  if (AppState.ui.isAtBottom) {
    scrollToBottom(true);
  }
  
  return true;
}

function updateMessageStatusUI(messageId, status) {
  var messageEl = DOM.messageList ? DOM.messageList.querySelector('[data-message-id="' + messageId + '"]') : null;
  if (messageEl) {
    var statusEl = messageEl.querySelector('.message-status');
    if (statusEl) {
      statusEl.className = 'message-status ' + status;
      statusEl.textContent = getStatusIcon(status);
    }
    messageEl.classList.remove('optimistic');
  }
}

function clearMessageList() {
  if (DOM.messageList) {
    var emptyState = DOM.chatEmpty;
    DOM.messageList.innerHTML = '';
    if (emptyState) {
      DOM.messageList.appendChild(emptyState);
    }
  }
}

/* ============================================
   UI UPDATE FUNCTIONS
   ============================================ */
function updateConnectionStatus(status) {
  AppState.ui.connectionStatus = status;
  
  if (DOM.connectionStatus) {
    DOM.connectionStatus.className = 'connection-status ' + status;
    var textEl = DOM.connectionStatus.querySelector('.connection-text');
    if (textEl) {
      var statusText = {
        'connected': 'Connected',
        'connecting': 'Connecting...',
        'reconnecting': 'Reconnecting...',
        'disconnected': 'Disconnected',
        'error': 'Connection Error'
      };
      textEl.textContent = statusText[status] || 'Unknown';
    }
  }
}

function updatePeerInfo(peer) {
  if (DOM.peerName) {
    DOM.peerName.textContent = peer || 'Select a contact';
  }
  if (DOM.peerAvatar) {
    DOM.peerAvatar.textContent = peer ? peer.charAt(0).toUpperCase() : '?';
  }
  if (DOM.peerStatus) {
    DOM.peerStatus.textContent = peer ? 'End-to-end encrypted' : 'Choose someone to start chatting';
  }
}

function scrollToBottom(smooth) {
  if (DOM.messageList) {
    DOM.messageList.scrollTo({
      top: DOM.messageList.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto'
    });
  }
}

/* ============================================
   TOAST NOTIFICATIONS
   ============================================ */
function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration !== undefined ? duration : 4000;
  
  if (!DOM.toastContainer) return;
  
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  
  var icons = {
    success: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>',
    error: '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>',
    warning: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
    info: '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'
  };
  
  toast.innerHTML = '<svg class="toast-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
    (icons[type] || icons.info) +
    '</svg>' +
    '<div class="toast-content"><span class="toast-message">' + escapeHtml(message) + '</span></div>' +
    '<button class="toast-dismiss" aria-label="Dismiss">' +
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
    '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>' +
    '</svg>' +
    '</button>';
  
  var dismissBtn = toast.querySelector('.toast-dismiss');
  dismissBtn.addEventListener('click', function() { dismissToast(toast); });
  
  DOM.toastContainer.appendChild(toast);
  
  if (duration > 0) {
    setTimeout(function() { dismissToast(toast); }, duration);
  }
  
  var toasts = DOM.toastContainer.querySelectorAll('.toast:not(.hiding)');
  if (toasts.length > 3) {
    dismissToast(toasts[0]);
  }
}

function dismissToast(toast) {
  if (!toast || toast.classList.contains('hiding')) return;
  toast.classList.add('hiding');
  setTimeout(function() { toast.remove(); }, 300);
}

/* ============================================
   CONTACT MANAGEMENT
   ============================================ */
function loadContacts() {
  return apiGet('/api/users').then(function(res) {
    if (res.ok && res.users) {
      StateManager.setContacts(res.users);
      res.users.forEach(function(username) {
        if (username !== AppState.me) {
          appendContact(username);
        }
      });
    }
  });
}

function filterContacts(query) {
  var contacts = DOM.contactList ? DOM.contactList.querySelectorAll('.contact-item') : [];
  var lowerQuery = query.toLowerCase().trim();
  
  for (var i = 0; i < contacts.length; i++) {
    var nameEl = contacts[i].querySelector('.contact-name');
    var name = nameEl ? nameEl.textContent.toLowerCase() : '';
    var matches = lowerQuery === '' || name.indexOf(lowerQuery) !== -1;
    contacts[i].style.display = matches ? 'flex' : 'none';
  }
}

function selectPeer(peer) {
  if (AppState.ui.currentPeer === peer) return;
  
  StateManager.setCurrentPeer(peer);
  setActiveContact(peer);
  updatePeerInfo(peer);
  updateContactBadge(peer, 0);
  
  clearMessageList();
  StateManager.clearPeerMessages(peer);
  loadHistory(peer);
  
  if (DOM.messageInput) {
    DOM.messageInput.focus();
  }
}

/* ============================================
   MESSAGE MANAGEMENT
   ============================================ */
function loadHistory(peer) {
  if (!peer) return Promise.resolve();
  
  return apiGet('/api/history/' + encodeURIComponent(peer)).then(function(res) {
    if (res.ok && res.messages && res.messages.length > 0) {
      res.messages.forEach(function(msg) {
        appendMessage(msg);
      });
      scrollToBottom(false);
    } else {
      if (DOM.chatEmpty) {
        DOM.chatEmpty.classList.remove('hidden');
      }
    }
  });
}

function sendMessage() {
  var peer = AppState.ui.currentPeer;
  var text = DOM.messageInput ? DOM.messageInput.value.trim() : '';
  
  if (!peer || !text || AppState.ui.isSending) return;
  
  AppState.ui.isSending = true;
  updateSendButton();
  
  var optimisticMsg = {
    id: generateId(),
    text: text,
    dir: 'out',
    ts: new Date().toISOString(),
    status: 'sending'
  };
  
  appendMessage(optimisticMsg);
  DOM.messageInput.value = '';
  updateSendButton();
  autoResizeInput();
  
  apiPost('/api/send', { to: peer, text: text }).then(function(res) {
    if (res.ok) {
      StateManager.updateMessageStatus(optimisticMsg.id, 'sent');
      updateMessageStatusUI(optimisticMsg.id, 'sent');
    } else {
      StateManager.updateMessageStatus(optimisticMsg.id, 'failed');
      updateMessageStatusUI(optimisticMsg.id, 'failed');
      showToast('Failed to send message', 'error');
    }
    
    AppState.ui.isSending = false;
    updateSendButton();
    if (DOM.messageInput) {
      DOM.messageInput.focus();
    }
  });
}

/* ============================================
   INPUT HANDLING
   ============================================ */
function updateSendButton() {
  if (DOM.sendButton) {
    var hasText = DOM.messageInput && DOM.messageInput.value.trim().length > 0;
    var canSend = hasText && !AppState.ui.isSending && AppState.ui.currentPeer;
    DOM.sendButton.disabled = !canSend;
  }
}

function autoResizeInput() {
  if (DOM.messageInput) {
    DOM.messageInput.style.height = 'auto';
    var maxHeight = 120;
    DOM.messageInput.style.height = Math.min(DOM.messageInput.scrollHeight, maxHeight) + 'px';
  }
}

function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function checkScrollPosition() {
  if (DOM.messageList) {
    var scrollTop = DOM.messageList.scrollTop;
    var scrollHeight = DOM.messageList.scrollHeight;
    var clientHeight = DOM.messageList.clientHeight;
    var isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    AppState.ui.isAtBottom = isAtBottom;
    
    if (DOM.scrollToBottom) {
      DOM.scrollToBottom.classList.toggle('visible', !isAtBottom);
    }
  }
}

/* ============================================
   WEBSOCKET HANDLING (NO POLLING!)
   ============================================ */
var socket = null;
var wsToken = null;

function initSocket() {
  updateConnectionStatus('connecting');
  
  return apiPost('/api/ws-token', {}).then(function(tokenRes) {
    if (!tokenRes.ok) {
      console.error('Failed to get WS token');
      updateConnectionStatus('error');
      showToast('Connection failed. Please refresh.', 'error');
      return;
    }
    
    wsToken = tokenRes.token;
    var relayWs = DOM.app ? (DOM.app.dataset.relayWs || 'ws://127.0.0.1:5000') : 'ws://127.0.0.1:5000';
    var relayHttp = relayWs.replace('ws://', 'http://').replace('wss://', 'https://');
    
    socket = io(relayHttp, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      maxReconnectionAttempts: Infinity
    });
    
    socket.on('connect', function() {
      console.log('Socket connected');
      updateConnectionStatus('connecting');
      socket.emit('auth', { token: wsToken });
    });
    
    socket.on('authed', function(res) {
      if (res && res.ok) {
        console.log('Socket authenticated');
        updateConnectionStatus('connected');
        pullInbox();
      } else {
        console.error('Socket auth failed');
        updateConnectionStatus('error');
      }
    });
    
    socket.on('disconnect', function(reason) {
      console.log('Socket disconnected:', reason);
      updateConnectionStatus('disconnected');
    });
    
    socket.on('reconnect', function() {
      console.log('Socket reconnected');
      updateConnectionStatus('connecting');
      apiPost('/api/ws-token', {}).then(function(newTokenRes) {
        if (newTokenRes.ok) {
          wsToken = newTokenRes.token;
          socket.emit('auth', { token: wsToken });
        }
      });
    });
    
    socket.on('reconnect_attempt', function() {
      updateConnectionStatus('reconnecting');
    });
    
    socket.on('reconnect_failed', function() {
      updateConnectionStatus('error');
      showToast('Connection lost. Please refresh the page.', 'error');
    });
    
    socket.on('msg', function(data) {
      console.log('New message received via socket from:', data.from);
      handleNewMessage(data);
    });
    
    socket.on('user_registered', function(data) {
      if (data && data.username && data.username !== AppState.me) {
        console.log('New user registered:', data.username);
        if (StateManager.addContact(data.username)) {
          appendContact(data.username);
          showToast(data.username + ' joined', 'info');
        }
      }
    });
  });
}

function handleNewMessage(data) {
  var sender = data.from;
  console.log('Processing message from:', sender);
  
  apiGet('/api/inbox').then(function(res) {
    if (!res.ok) return;
    
    var currentPeer = AppState.ui.currentPeer;
    
    if (currentPeer === sender) {
      apiGet('/api/history/' + encodeURIComponent(sender)).then(function(historyRes) {
        if (historyRes.ok && historyRes.messages) {
          historyRes.messages.forEach(function(msg) {
            if (msg.dir === 'out') return;
            var added = appendMessage(msg);
            if (added && !document.hasFocus()) {
              NotificationManager.showNotification(sender, msg.text, null);
            }
          });
        }
      });
    } else {
      StateManager.incrementUnread(sender);
      updateContactBadge(sender, StateManager.getUnread(sender));
      
      apiGet('/api/history/' + encodeURIComponent(sender)).then(function(historyRes) {
        if (historyRes.ok && historyRes.messages && historyRes.messages.length > 0) {
          var latestMsg = historyRes.messages[historyRes.messages.length - 1];
          if (latestMsg.dir === 'in') {
            NotificationManager.showNotification(sender, latestMsg.text, null);
          }
        }
      });
    }
  });
}

function pullInbox() {
  return apiGet('/api/inbox').then(function(res) {
    if (!res.ok) return;
    var currentPeer = AppState.ui.currentPeer;
    if (currentPeer) {
      apiGet('/api/history/' + encodeURIComponent(currentPeer)).then(function(historyRes) {
        if (historyRes.ok && historyRes.messages) {
          historyRes.messages.forEach(function(msg) {
            if (msg.dir === 'out') return;
            appendMessage(msg);
          });
        }
      });
    }
  });
}

/* ============================================
   PROFILE MANAGER
   ============================================ */
var ProfileManager = {
  profile: null,
  cache: {},
  cacheTTL: 5 * 60 * 1000,
  
  loadProfile: function() {
    var self = this;
    return apiGet('/api/profile').then(function(res) {
      if (res.ok && res.profile) {
        self.profile = res.profile;
        self.updateProfileUI();
        return self.profile;
      }
      return null;
    });
  },
  
  updateProfileUI: function() {
    if (!this.profile) return;
    var userAvatar = document.querySelector('.user-avatar');
    var userName = document.querySelector('.user-name');
    
    if (userAvatar) {
      if (this.profile.avatarUrl) {
        userAvatar.innerHTML = '<img src="' + this.profile.avatarUrl + '" alt="Avatar" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
      } else {
        var initial = (this.profile.displayName && this.profile.displayName.charAt(0)) || (this.profile.username && this.profile.username.charAt(0)) || '?';
        userAvatar.textContent = initial.toUpperCase();
      }
    }
    if (userName) {
      userName.textContent = this.profile.displayName || this.profile.username;
    }
  },
  
  updateDisplayName: function(name) {
    var self = this;
    return apiPost('/api/profile', { displayName: name }).then(function(res) {
      if (res.ok) {
        self.profile.displayName = name;
        self.updateProfileUI();
        showToast('Display name updated', 'success');
        return true;
      }
      showToast(res.error || 'Failed to update name', 'error');
      return false;
    });
  },
  
  uploadAvatar: function(file) {
    var self = this;
    var formData = new FormData();
    formData.append('avatar', file);
    return fetch('/api/avatar', {
      method: 'POST',
      credentials: 'same-origin',
      body: formData
    }).then(function(response) {
      return response.json();
    }).then(function(res) {
      if (res.ok) {
        self.profile.avatarUrl = res.avatarUrl + '?t=' + Date.now();
        self.updateProfileUI();
        showToast('Avatar uploaded', 'success');
        return true;
      }
      showToast(res.error || 'Failed to upload avatar', 'error');
      return false;
    }).catch(function(e) {
      showToast('Failed to upload avatar', 'error');
      return false;
    });
  },
  
  deleteAvatar: function() {
    var self = this;
    return fetch('/api/avatar', {
      method: 'DELETE',
      credentials: 'same-origin'
    }).then(function(response) {
      return response.json();
    }).then(function(res) {
      if (res.ok) {
        self.profile.avatarUrl = null;
        self.updateProfileUI();
        showToast('Avatar deleted', 'success');
        return true;
      }
      return false;
    }).catch(function(e) {
      return false;
    });
  }
};

/* ============================================
   NOTIFICATION MANAGER
   ============================================ */
var NotificationManager = {
  permission: 'default',
  enabled: true,
  soundEnabled: true,
  
  init: function() {
    this.loadSettings();
    if ('Notification' in window) {
      this.permission = Notification.permission;
      if (this.permission === 'default') {
        this.requestPermission();
      }
    }
  },
  
  requestPermission: function() {
    var self = this;
    if (!('Notification' in window)) {
      showToast('Notifications not supported', 'warning');
      return Promise.resolve(false);
    }
    if (Notification.permission === 'granted') {
      self.permission = 'granted';
      return Promise.resolve(true);
    }
    if (Notification.permission !== 'denied') {
      return Notification.requestPermission().then(function(permission) {
        self.permission = permission;
        if (permission === 'granted') {
          showToast('Notifications enabled', 'success');
        }
        return permission === 'granted';
      });
    }
    return Promise.resolve(false);
  },
  
  showNotification: function(sender, message, avatarUrl) {
    if (!this.enabled) {
      this.showInAppToast(sender, message);
      return;
    }
    if (this.permission !== 'granted') {
      this.showInAppToast(sender, message);
      return;
    }
    var truncatedMsg = message.length > 50 ? message.substring(0, 50) + '...' : message;
    try {
      var notification = new Notification(sender, {
        body: truncatedMsg,
        icon: avatarUrl || '/static/img/default-avatar.png',
        tag: 'msg-' + sender,
        renotify: true
      });
      notification.onclick = function() {
        window.focus();
        selectPeer(sender);
        notification.close();
      };
      if (this.soundEnabled) {
        this.playSound();
      }
    } catch (e) {
      this.showInAppToast(sender, message);
    }
  },
  
  showInAppToast: function(sender, message) {
    var truncatedMsg = message.length > 50 ? message.substring(0, 50) + '...' : message;
    showToast(sender + ': ' + truncatedMsg, 'info');
  },
  
  playSound: function() {
    try {
      var AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      var audioContext = new AudioContextClass();
      var oscillator = audioContext.createOscillator();
      var gainNode = audioContext.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      gainNode.gain.value = 0.1;
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.1);
    } catch (e) {}
  },
  
  loadSettings: function() {
    try {
      var settings = JSON.parse(localStorage.getItem('messenger_settings') || '{}');
      if (settings.notifications) {
        this.enabled = settings.notifications.enabled !== false;
        this.soundEnabled = settings.notifications.sound !== false;
      }
    } catch (e) {}
  },
  
  saveSettings: function() {
    try {
      var settings = JSON.parse(localStorage.getItem('messenger_settings') || '{}');
      settings.notifications = { enabled: this.enabled, sound: this.soundEnabled };
      localStorage.setItem('messenger_settings', JSON.stringify(settings));
    } catch (e) {}
  },
  
  setEnabled: function(enabled) {
    this.enabled = enabled;
    this.saveSettings();
  },
  
  setSoundEnabled: function(enabled) {
    this.soundEnabled = enabled;
    this.saveSettings();
  }
};

/* ============================================
   SETTINGS PANEL
   ============================================ */
var SettingsPanel = {
  isOpen: false,
  originalProfile: null,
  
  open: function() {
    this.isOpen = true;
    this.originalProfile = ProfileManager.profile ? Object.assign({}, ProfileManager.profile) : null;
    var modal = document.getElementById('settingsModal');
    if (modal) {
      modal.classList.remove('hidden');
      this.populateForm();
    }
  },
  
  close: function() {
    this.isOpen = false;
    var modal = document.getElementById('settingsModal');
    if (modal) {
      modal.classList.add('hidden');
    }
  },
  
  populateForm: function() {
    var displayNameInput = document.getElementById('settingsDisplayName');
    var avatarPreview = document.getElementById('settingsAvatarPreview');
    var notificationsToggle = document.getElementById('settingsNotifications');
    var soundToggle = document.getElementById('settingsSound');
    
    if (displayNameInput && ProfileManager.profile) {
      displayNameInput.value = ProfileManager.profile.displayName || '';
    }
    if (avatarPreview && ProfileManager.profile) {
      if (ProfileManager.profile.avatarUrl) {
        avatarPreview.innerHTML = '<img src="' + ProfileManager.profile.avatarUrl + '" alt="Avatar">';
      } else {
        var initial = (ProfileManager.profile.displayName && ProfileManager.profile.displayName.charAt(0)) || (ProfileManager.profile.username && ProfileManager.profile.username.charAt(0)) || '?';
        avatarPreview.innerHTML = '<span class="avatar-initial">' + initial.toUpperCase() + '</span>';
      }
    }
    if (notificationsToggle) {
      notificationsToggle.checked = NotificationManager.enabled;
    }
    if (soundToggle) {
      soundToggle.checked = NotificationManager.soundEnabled;
    }
  },
  
  save: function() {
    var self = this;
    var displayNameInput = document.getElementById('settingsDisplayName');
    var notificationsToggle = document.getElementById('settingsNotifications');
    var soundToggle = document.getElementById('settingsSound');
    var promise = Promise.resolve();
    
    if (displayNameInput) {
      var newName = displayNameInput.value.trim();
      var oldName = self.originalProfile ? self.originalProfile.displayName : '';
      if (newName && newName !== oldName) {
        promise = promise.then(function() {
          return ProfileManager.updateDisplayName(newName);
        });
      }
    }
    if (notificationsToggle) {
      NotificationManager.setEnabled(notificationsToggle.checked);
      if (notificationsToggle.checked && NotificationManager.permission !== 'granted') {
        promise = promise.then(function() {
          return NotificationManager.requestPermission();
        });
      }
    }
    if (soundToggle) {
      NotificationManager.setSoundEnabled(soundToggle.checked);
    }
    promise.then(function() {
      self.close();
    });
  },
  
  cancel: function() {
    this.close();
  },
  
  handleAvatarUpload: function(file) {
    var self = this;
    if (!file) return;
    var validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (validTypes.indexOf(file.type) === -1) {
      showToast('Please upload a JPEG, PNG, or WebP image', 'error');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      showToast('Image must be under 2MB', 'error');
      return;
    }
    var avatarPreview = document.getElementById('settingsAvatarPreview');
    if (avatarPreview) {
      var reader = new FileReader();
      reader.onload = function(e) {
        avatarPreview.innerHTML = '<img src="' + e.target.result + '" alt="Avatar preview">';
      };
      reader.readAsDataURL(file);
    }
    ProfileManager.uploadAvatar(file).then(function() {
      self.populateForm();
    });
  },
  
  deleteAvatar: function() {
    var self = this;
    ProfileManager.deleteAvatar().then(function() {
      self.populateForm();
    });
  }
};

/* ============================================
   SETTINGS PANEL INIT
   ============================================ */
function initSettingsPanel() {
  var settingsBtn = document.getElementById('settingsBtn');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', function() { SettingsPanel.open(); });
  }
  var settingsClose = document.getElementById('settingsClose');
  if (settingsClose) {
    settingsClose.addEventListener('click', function() { SettingsPanel.close(); });
  }
  var settingsCancel = document.getElementById('settingsCancel');
  if (settingsCancel) {
    settingsCancel.addEventListener('click', function() { SettingsPanel.cancel(); });
  }
  var settingsSave = document.getElementById('settingsSave');
  if (settingsSave) {
    settingsSave.addEventListener('click', function() { SettingsPanel.save(); });
  }
  var avatarInput = document.getElementById('settingsAvatarInput');
  if (avatarInput) {
    avatarInput.addEventListener('change', function(e) {
      if (e.target.files && e.target.files[0]) {
        SettingsPanel.handleAvatarUpload(e.target.files[0]);
      }
    });
  }
  var deleteAvatarBtn = document.getElementById('settingsDeleteAvatar');
  if (deleteAvatarBtn) {
    deleteAvatarBtn.addEventListener('click', function() { SettingsPanel.deleteAvatar(); });
  }
  var settingsModal = document.getElementById('settingsModal');
  if (settingsModal) {
    settingsModal.addEventListener('click', function(e) {
      if (e.target.id === 'settingsModal') {
        SettingsPanel.close();
      }
    });
  }
}

/* ============================================
   INITIALIZATION (NO POLLING!)
   ============================================ */
function init() {
  console.log('Initializing Secure Messenger...');
  initDOMReferences();
  
  apiGet('/api/me').then(function(meRes) {
    if (!meRes.ok) {
      console.error('Not authenticated');
      return;
    }
    AppState.me = meRes.username;
    console.log('Logged in as:', AppState.me);
    
    ProfileManager.loadProfile();
    NotificationManager.init();
    
    loadContacts().then(function() {
      setupEventListeners();
      initSettingsPanel();
      initSocket();
      // NO startPolling() - WebSocket only!
      console.log('Initialization complete (WebSocket mode)');
    });
  });
}

function setupEventListeners() {
  if (DOM.sendButton) {
    DOM.sendButton.addEventListener('click', sendMessage);
  }
  if (DOM.messageInput) {
    DOM.messageInput.addEventListener('input', function() {
      updateSendButton();
      autoResizeInput();
    });
    DOM.messageInput.addEventListener('keydown', handleInputKeydown);
  }
  if (DOM.searchInput) {
    var debouncedFilter = debounce(function(e) { filterContacts(e.target.value); }, 300);
    DOM.searchInput.addEventListener('input', debouncedFilter);
  }
  if (DOM.messageList) {
    DOM.messageList.addEventListener('scroll', checkScrollPosition);
  }
  if (DOM.scrollToBottom) {
    DOM.scrollToBottom.addEventListener('click', function() { scrollToBottom(true); });
  }
  if (DOM.contactList) {
    DOM.contactList.addEventListener('click', function(e) {
      var contactItem = e.target.closest('.contact-item');
      if (contactItem) {
        selectPeer(contactItem.dataset.peer);
      }
    });
  }
  var mobileMenuBtn = document.getElementById('mobileMenuBtn');
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', function() {
      var sidebar = document.getElementById('sidebar');
      if (sidebar) {
        sidebar.classList.toggle('open');
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', init);