/**
 * LLM Tools Widget for injx Documentation
 * Provides easy access to LLM-friendly documentation formats
 */

(function() {
  'use strict';

  class LLMToolsWidget {
    constructor() {
      this.widget = document.getElementById('llm-tools-widget');
      this.trigger = document.getElementById('llm-tools-trigger');
      this.menu = document.getElementById('llm-tools-menu');
      
      if (!this.widget || !this.trigger || !this.menu) {
        console.error('LLM Tools widget elements not found:', {
          widget: !!this.widget,
          trigger: !!this.trigger,
          menu: !!this.menu
        });
        return;
      }
      
      // Mark as initialized
      this.widget.classList.add('initialized');
      
      this.isMenuOpen = false;
      this.initializeEventListeners();
      
      // Ensure widget is visible
      this.widget.style.display = 'block';
      this.widget.style.visibility = 'visible';
      this.widget.style.opacity = '1';
      console.log('Widget should be visible now', this.widget);
    }
    
    initializeEventListeners() {
      // Toggle menu on trigger click
      this.trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleMenu();
      });
      
      // Close menu when clicking outside
      document.addEventListener('click', (e) => {
        if (!this.widget.contains(e.target) && this.isMenuOpen) {
          this.closeMenu();
        }
      });
      
      // Handle menu button clicks
      this.menu.querySelectorAll('button[data-action]').forEach(button => {
        button.addEventListener('click', (e) => {
          e.stopPropagation();
          this.handleAction(button.dataset.action);
        });
      });
      
      // Close menu on escape key
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isMenuOpen) {
          this.closeMenu();
        }
      });
    }
    
    toggleMenu() {
      if (this.isMenuOpen) {
        this.closeMenu();
      } else {
        this.openMenu();
      }
    }
    
    openMenu() {
      this.menu.classList.add('show');
      this.isMenuOpen = true;
      this.trigger.setAttribute('aria-expanded', 'true');
    }
    
    closeMenu() {
      this.menu.classList.remove('show');
      this.isMenuOpen = false;
      this.trigger.setAttribute('aria-expanded', 'false');
    }
    
    handleAction(action) {
      switch(action) {
        case 'copy-markdown':
          this.copyAsMarkdown();
          break;
        case 'copy-text':
          this.copyAsText();
          break;
        case 'open-chatgpt':
          this.openInChatGPT();
          break;
        case 'open-claude':
          this.openInClaude();
          break;
        case 'download-full':
          this.downloadFullDocs();
          break;
        default:
          console.warn('Unknown action:', action);
      }
      
      // Close menu after action
      this.closeMenu();
    }
    
    async copyAsMarkdown() {
      try {
        const markdown = await this.getPageMarkdown();
        await navigator.clipboard.writeText(markdown);
        this.showNotification('Copied as Markdown!');
      } catch (error) {
        console.error('Failed to copy markdown:', error);
        this.showNotification('Failed to copy', 'error');
      }
    }
    
    async copyAsText() {
      try {
        const text = await this.getPageText();
        await navigator.clipboard.writeText(text);
        this.showNotification('Copied as plain text!');
      } catch (error) {
        console.error('Failed to copy text:', error);
        this.showNotification('Failed to copy', 'error');
      }
    }
    
    async getPageMarkdown() {
      // Get the main content area
      const content = document.querySelector('.md-content__inner') || document.querySelector('.md-content');
      if (!content) {
        throw new Error('Content not found');
      }
      
      // Clone the content to avoid modifying the original
      const clone = content.cloneNode(true);
      
      // Remove navigation elements, ads, etc.
      const elementsToRemove = [
        '.md-source-file',
        '.md-content__button',
        '.admonition-title',
        'style',
        'script'
      ];
      
      elementsToRemove.forEach(selector => {
        clone.querySelectorAll(selector).forEach(el => el.remove());
      });
      
      // Convert HTML to markdown-like format
      let markdown = '# ' + (document.title || 'Documentation') + '\n\n';
      
      // Process headings
      clone.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
        const level = parseInt(heading.tagName.substring(1));
        const prefix = '#'.repeat(level);
        markdown += '\n' + prefix + ' ' + heading.textContent.trim() + '\n\n';
      });
      
      // Process paragraphs
      clone.querySelectorAll('p').forEach(p => {
        markdown += p.textContent.trim() + '\n\n';
      });
      
      // Process code blocks
      clone.querySelectorAll('pre code').forEach(code => {
        const language = code.className.match(/language-(\w+)/)?.[1] || '';
        markdown += '```' + language + '\n' + code.textContent + '\n```\n\n';
      });
      
      // Process lists
      clone.querySelectorAll('ul, ol').forEach(list => {
        list.querySelectorAll('li').forEach((li, index) => {
          const prefix = list.tagName === 'OL' ? `${index + 1}.` : '-';
          markdown += prefix + ' ' + li.textContent.trim() + '\n';
        });
        markdown += '\n';
      });
      
      return markdown.trim();
    }
    
    async getPageText() {
      // Get the main content area
      const content = document.querySelector('.md-content__inner') || document.querySelector('.md-content');
      if (!content) {
        throw new Error('Content not found');
      }
      
      // Get text content, preserving some structure
      let text = document.title + '\n\n';
      text += content.innerText || content.textContent;
      
      // Clean up excessive whitespace
      text = text.replace(/\n{3,}/g, '\n\n').trim();
      
      return text;
    }
    
    openInChatGPT() {
      this.openInLLM('chatgpt');
    }
    
    openInClaude() {
      this.openInLLM('claude');
    }
    
    async openInLLM(service) {
      try {
        // Get page content
        const content = await this.getPageText();
        const title = document.title;
        const url = window.location.href;
        
        // Prepare the prompt
        const prompt = `I'm reading the injx documentation page "${title}" (${url}). Here's the content:\n\n${content}\n\nCan you help me understand this documentation?`;
        
        // Truncate if too long (URL length limits)
        const maxLength = 4000;
        const truncatedPrompt = prompt.length > maxLength 
          ? prompt.substring(0, maxLength) + '...[truncated]'
          : prompt;
        
        // Generate the URL based on service
        let llmUrl;
        if (service === 'chatgpt') {
          // ChatGPT doesn't have a direct URL parameter for prompts
          // We'll copy to clipboard and open ChatGPT
          await navigator.clipboard.writeText(truncatedPrompt);
          llmUrl = 'https://chat.openai.com/';
          this.showNotification('Content copied! Paste it in ChatGPT.');
        } else if (service === 'claude') {
          // Claude also doesn't have direct URL parameters
          // We'll copy to clipboard and open Claude
          await navigator.clipboard.writeText(truncatedPrompt);
          llmUrl = 'https://claude.ai/new';
          this.showNotification('Content copied! Paste it in Claude.');
        }
        
        // Open in new tab
        window.open(llmUrl, '_blank');
        
      } catch (error) {
        console.error(`Failed to open in ${service}:`, error);
        this.showNotification('Failed to prepare content', 'error');
      }
    }
    
    downloadFullDocs() {
      // Check if llms-full.txt exists
      const llmsFullUrl = new URL('/llms-full.txt', window.location.origin).href;
      
      // Create a temporary link and click it
      const link = document.createElement('a');
      link.href = llmsFullUrl;
      link.download = 'injx-docs-full.txt';
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      this.showNotification('Downloading complete documentation...');
    }
    
    showNotification(message, type = 'success') {
      // Remove any existing notification
      const existingNotification = document.querySelector('.llm-notification');
      if (existingNotification) {
        existingNotification.remove();
      }
      
      // Create notification element
      const notification = document.createElement('div');
      notification.className = `llm-notification llm-notification-${type}`;
      notification.textContent = message;
      notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : '#f44336'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        font-size: 14px;
      `;
      
      document.body.appendChild(notification);
      
      // Auto-remove after 3 seconds
      setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
      }, 3000);
    }
  }
  
  // Add animations to page
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    
    @keyframes slideOut {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(100%);
        opacity: 0;
      }
    }
  `;
  document.head.appendChild(style);
  
  // Initialize widget when DOM is ready
  function initWidget() {
    console.log('Initializing LLM Tools Widget...');
    const widget = new LLMToolsWidget();
    console.log('LLM Tools Widget initialized');
    return widget;
  }
  
  // Try multiple initialization methods to ensure it works
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWidget);
  } else {
    // DOM is already loaded
    setTimeout(initWidget, 100); // Small delay to ensure MkDocs is ready
  }
  
  // Also try on window load as fallback
  window.addEventListener('load', () => {
    if (!document.querySelector('.llm-tools-widget.initialized')) {
      initWidget();
    }
  });
})();