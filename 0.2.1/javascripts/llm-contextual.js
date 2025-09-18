/**
 * GitBook-style Contextual LLM Tools for injx Documentation
 * Provides contextual menu when selecting text or hovering over sections
 */

(function() {
  'use strict';

  class LLMContextualTools {
    constructor() {
      this.selectedText = '';
      this.contextMenu = null;
      this.sectionButtons = new Map();
      this.init();
    }

    init() {
      console.log('Initializing LLM Contextual Tools...');
      
      // Create the contextual menu
      this.createContextMenu();
      
      // Add section hover buttons
      this.addSectionButtons();
      
      // Add header button like GitBook
      this.addHeaderButton();
      
      // Listen for text selection
      this.setupTextSelection();
      
      // Setup keyboard shortcuts
      this.setupKeyboardShortcuts();
      
      console.log('LLM Contextual Tools initialized');
    }

    createContextMenu() {
      // Remove any existing menu
      const existing = document.getElementById('llm-context-menu');
      if (existing) existing.remove();

      // Create menu element
      const menu = document.createElement('div');
      menu.id = 'llm-context-menu';
      menu.className = 'llm-context-menu';
      menu.style.cssText = `
        position: absolute;
        background: var(--md-default-bg-color);
        border: 1px solid var(--md-default-fg-color--lightest);
        border-radius: 8px;
        padding: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        display: none;
        min-width: 200px;
      `;

      menu.innerHTML = `
        <button class="llm-menu-item" data-action="copy-selection-md">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          Copy as Markdown
        </button>
        <button class="llm-menu-item" data-action="copy-selection-text">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          Copy as Text
        </button>
        <div class="llm-menu-divider"></div>
        <button class="llm-menu-item" data-action="send-chatgpt">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          Ask ChatGPT
        </button>
        <button class="llm-menu-item" data-action="send-claude">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M8 14s1.5 2 4 2 4-2 4-2"></path>
          </svg>
          Ask Claude
        </button>
      `;

      document.body.appendChild(menu);
      this.contextMenu = menu;

      // Add styles
      this.addContextMenuStyles();

      // Setup menu item clicks
      menu.querySelectorAll('.llm-menu-item').forEach(item => {
        item.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.handleMenuAction(item.dataset.action);
          this.hideContextMenu();
        });
      });

      // Hide menu when clicking outside
      document.addEventListener('click', () => this.hideContextMenu());
    }

    addContextMenuStyles() {
      const style = document.createElement('style');
      style.textContent = `
        .llm-context-menu {
          font-family: var(--md-text-font-family);
        }
        
        .llm-menu-item {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 100%;
          padding: 8px 12px;
          background: none;
          border: none;
          color: var(--md-default-fg-color);
          font-size: 14px;
          cursor: pointer;
          text-align: left;
          transition: background-color 0.2s;
          border-radius: 4px;
        }
        
        .llm-menu-item:hover {
          background-color: var(--md-default-fg-color--lightest);
        }
        
        .llm-menu-item svg {
          flex-shrink: 0;
          opacity: 0.7;
        }
        
        .llm-menu-divider {
          height: 1px;
          background: var(--md-default-fg-color--lightest);
          margin: 4px 0;
        }
        
        .llm-section-button {
          position: absolute;
          right: 0;
          top: 50%;
          transform: translateY(-50%);
          opacity: 0;
          transition: opacity 0.2s;
          background: var(--md-primary-fg-color);
          color: white;
          border: none;
          border-radius: 4px;
          padding: 6px 10px;
          font-size: 12px;
          cursor: pointer;
          z-index: 100;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        
        .llm-section-wrapper {
          position: relative;
        }
        
        .llm-section-wrapper:hover .llm-section-button {
          opacity: 1;
        }
        
        .llm-header-button {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: transparent;
          border: 1px solid var(--md-default-fg-color--lighter);
          border-radius: 4px;
          color: var(--md-default-fg-color);
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s;
          margin-left: 8px;
        }
        
        .llm-header-button:hover {
          background: var(--md-default-fg-color--lightest);
          border-color: var(--md-default-fg-color--light);
        }
        
        /* Highlight effect when text is selected */
        ::selection {
          background-color: var(--md-accent-fg-color--transparent);
        }
      `;
      document.head.appendChild(style);
    }

    addSectionButtons() {
      // Add hover buttons to major content sections
      const sections = document.querySelectorAll('.md-content h1, .md-content h2, .md-content h3, .md-content pre');
      
      sections.forEach((section, index) => {
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'llm-section-wrapper';
        
        // Wrap the section
        section.parentNode.insertBefore(wrapper, section);
        wrapper.appendChild(section);
        
        // Add button
        const button = document.createElement('button');
        button.className = 'llm-section-button';
        button.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          Copy
        `;
        
        button.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.copySectionContent(section);
        });
        
        wrapper.appendChild(button);
        this.sectionButtons.set(section, button);
      });
    }

    addHeaderButton() {
      // Add button in the header area like GitBook
      const headerNav = document.querySelector('.md-header__nav') || document.querySelector('.md-header');
      if (!headerNav) return;

      const button = document.createElement('button');
      button.className = 'llm-header-button';
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="10" rx="2" ry="2"></rect>
          <circle cx="12" cy="5" r="2"></circle>
          <path d="M12 7v4"></path>
        </svg>
        AI Tools
      `;
      
      button.addEventListener('click', (e) => {
        e.preventDefault();
        this.showPageMenu(e);
      });

      // Find a good place to insert it
      const searchBar = headerNav.querySelector('.md-search');
      if (searchBar) {
        searchBar.parentNode.insertBefore(button, searchBar.nextSibling);
      } else {
        headerNav.appendChild(button);
      }
    }

    setupTextSelection() {
      // Listen for text selection
      document.addEventListener('mouseup', (e) => {
        const selection = window.getSelection();
        const text = selection.toString().trim();
        
        if (text.length > 0) {
          this.selectedText = text;
          this.showContextMenuAtSelection(selection);
        } else {
          this.hideContextMenu();
        }
      });
    }

    setupKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl + Shift + C: Copy as Markdown
        if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'C') {
          e.preventDefault();
          const selection = window.getSelection().toString();
          if (selection) {
            this.copyAsMarkdown(selection);
          }
        }
      });
    }

    showContextMenuAtSelection(selection) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      
      this.contextMenu.style.display = 'block';
      this.contextMenu.style.left = `${rect.left + (rect.width / 2) - 100}px`;
      this.contextMenu.style.top = `${rect.bottom + window.scrollY + 5}px`;
    }

    showPageMenu(event) {
      // Show menu with page-level options
      this.contextMenu.style.display = 'block';
      this.contextMenu.style.left = `${event.clientX}px`;
      this.contextMenu.style.top = `${event.clientY + 10}px`;
    }

    hideContextMenu() {
      if (this.contextMenu) {
        this.contextMenu.style.display = 'none';
      }
    }

    copySectionContent(section) {
      let content = '';
      
      if (section.tagName.startsWith('H')) {
        // For headers, copy the header and following content until next header
        content = section.textContent + '\n\n';
        let next = section.parentElement.nextElementSibling;
        while (next && !next.querySelector('h1, h2, h3, h4, h5, h6')) {
          content += next.textContent + '\n\n';
          next = next.nextElementSibling;
        }
      } else if (section.tagName === 'PRE') {
        // For code blocks, copy the code
        content = '```\n' + section.textContent + '\n```';
      } else {
        content = section.textContent;
      }
      
      this.copyToClipboard(content);
      this.showNotification('Section copied!');
    }

    handleMenuAction(action) {
      const text = this.selectedText || this.getPageContent();
      
      switch(action) {
        case 'copy-selection-md':
          this.copyAsMarkdown(text);
          break;
        case 'copy-selection-text':
          this.copyAsPlainText(text);
          break;
        case 'send-chatgpt':
          this.sendToChatGPT(text);
          break;
        case 'send-claude':
          this.sendToClaude(text);
          break;
      }
    }

    getPageContent() {
      const content = document.querySelector('.md-content__inner');
      return content ? content.textContent : '';
    }

    copyAsMarkdown(text) {
      // Simple markdown conversion (enhance as needed)
      const markdown = text;
      this.copyToClipboard(markdown);
      this.showNotification('Copied as Markdown!');
    }

    copyAsPlainText(text) {
      this.copyToClipboard(text);
      this.showNotification('Copied as plain text!');
    }

    sendToChatGPT(text) {
      const prompt = `I'm reading this documentation:\n\n${text}\n\nCan you help me understand it?`;
      this.copyToClipboard(prompt);
      window.open('https://chat.openai.com/', '_blank');
      this.showNotification('Content copied! Paste in ChatGPT.');
    }

    sendToClaude(text) {
      const prompt = `I'm reading this documentation:\n\n${text}\n\nCan you help me understand it?`;
      this.copyToClipboard(prompt);
      window.open('https://claude.ai/new', '_blank');
      this.showNotification('Content copied! Paste in Claude.');
    }

    copyToClipboard(text) {
      navigator.clipboard.writeText(text).catch(err => {
        console.error('Failed to copy:', err);
        this.showNotification('Failed to copy', 'error');
      });
    }

    showNotification(message, type = 'success') {
      const notification = document.createElement('div');
      notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : '#f44336'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        z-index: 10001;
        animation: slideIn 0.3s ease-out;
      `;
      notification.textContent = message;
      document.body.appendChild(notification);
      
      setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
      }, 2000);
    }
  }

  // Initialize when DOM is ready
  function init() {
    new LLMContextualTools();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 100);
  }
})();