(async function () {
  const authorSel   = document.getElementById('author_id');
  const categorySel = document.getElementById('category_id');
  const form        = document.getElementById('generateForm');
  const submitBtn   = document.getElementById('submitBtn');
  const btnText     = submitBtn.querySelector('.btn-text');
  const btnLoader   = submitBtn.querySelector('.btn-loader');
  const resultBox   = document.getElementById('result');
  const editSection = document.getElementById('editSection');
  const saveBtn     = document.getElementById('saveBtn');
  const aiEditBtn   = document.getElementById('aiEditBtn');
  const searchImagesBtn = document.getElementById('searchImagesBtn');
  const imageGallery = document.getElementById('imageGallery');
  const imageGrid = document.getElementById('imageGrid');
  const imageQuery = document.getElementById('imageQuery');
  const generateBannerBtn = document.getElementById('generateBannerBtn');
  const bannerFields = document.getElementById('bannerFields');
  const autoLinkBtn = document.getElementById('autoLinkBtn');
  const importLinksBtn = document.getElementById('importLinksBtn');
  const autoLinkResults = document.getElementById('autoLinkResults');
  const autoLinkArtists = document.getElementById('autoLinkArtists');
  const autoLinkShows = document.getElementById('autoLinkShows');
  const autoLinkServices = document.getElementById('autoLinkServices');
  const autoLinkSummary = document.getElementById('autoLinkSummary');
  
  let currentFeaturedImage = null;
  let selectedImageUrl = null;
  let currentBanner = null;

  function setLoading(btn, loading) {
    if (loading) {
      btn.disabled = true;
      const text = btn.querySelector('.btn-text');
      const loader = btn.querySelector('.btn-loader');
      if (text) text.style.display = 'none';
      if (loader) loader.style.display = 'inline-flex';
    } else {
      btn.disabled = false;
      const text = btn.querySelector('.btn-text');
      const loader = btn.querySelector('.btn-loader');
      if (text) text.style.display = 'inline';
      if (loader) loader.style.display = 'none';
    }
  }

  function fillSelect(selectEl, items, placeholder = 'Select…') {
    selectEl.innerHTML = '';
    const opt0 = document.createElement('option');
    opt0.value = '';
    opt0.textContent = placeholder;
    selectEl.appendChild(opt0);

    items.forEach(({ id, name }) => {
      const opt = document.createElement('option');
      opt.value = id || '';
      opt.textContent = name || 'Untitled';
      selectEl.appendChild(opt);
    });
  }

  async function fetchJSON(url) {
    const r = await fetch(url);
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); }
    catch { throw new Error(`${url} returned non-JSON: ${text}`);  }
    if (!r.ok || data.ok === false) {
      throw new Error(data.error || `${url} failed with ${r.status}`);
    }
    return data;
  }

  async function loadLookups() {
    try {
      const [{ authors }, { categories }] = await Promise.all([
        fetchJSON('/api/authors'),
        fetchJSON('/api/categories'),
      ]);
      fillSelect(authorSel, authors || [], 'No author (optional)');
      fillSelect(categorySel, categories || [], 'No category (optional)');
    } catch (err) {
      authorSel.innerHTML = `<option value="">Failed to load authors</option>`;
      categorySel.innerHTML = `<option value="">Failed to load categories</option>`;
      console.error(err);
    }
  }

  await loadLookups();

  // Initialize Quill Rich Text Editor
  let quill = null;
  let syncInProgress = false; // Prevent infinite loop during sync
  
  function initializeRichTextEditor() {
    if (quill) return; // Already initialized
    
    quill = new Quill('#richTextEditor', {
      theme: 'snow',
      modules: {
        toolbar: [
          [{ 'header': [5, false] }],
          ['bold', 'italic', 'underline'],
          ['link'],
          [{ 'list': 'ordered'}, { 'list': 'bullet' }],
          ['clean']
        ]
      },
      placeholder: 'Edit your content visually here...'
    });
    
    const bodyTextarea = document.getElementById('edit_body');
    
    // Sync: HTML textarea → Quill
    bodyTextarea.addEventListener('input', () => {
      if (syncInProgress) return;
      syncInProgress = true;
      
      try {
        const html = bodyTextarea.value;
        // Set Quill content from HTML
        quill.root.innerHTML = html;
      } finally {
        syncInProgress = false;
      }
    });
    
    // Sync: Quill → HTML textarea
    quill.on('text-change', () => {
      if (syncInProgress) return;
      syncInProgress = true;
      
      try {
        const html = quill.root.innerHTML;
        bodyTextarea.value = html;
      } finally {
        syncInProgress = false;
      }
    });
    
    // Initial sync: Load current HTML into Quill
    if (bodyTextarea.value) {
      quill.root.innerHTML = bodyTextarea.value;
    }
  }

  // Handle generate form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    setLoading(submitBtn, true);
    resultBox.style.display = 'none';
    editSection.style.display = 'none';

    const formData = new FormData(form);
    const payload = {
      prompt: formData.get('prompt'),
      featured_image_url: formData.get('featured_image_url') || null,
    };

    try {
      const response = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok && data.ok) {
        showGeneratedContent(data.content);
      } else {
        showError(data.error || 'An error occurred');
      }
    } catch (error) {
      showError(error.message || 'Network error occurred');
    } finally {
      setLoading(submitBtn, false);
    }
  });

  function showGeneratedContent(content) {
    currentFeaturedImage = content.featured_image;
    
    resultBox.className = 'result success';
    resultBox.innerHTML = `
      <h2>✅ Content Generated!</h2>
      <p style="color: var(--text-secondary); margin-top: 0.5rem;">
        Review and edit the content below, then click "Create Webflow Draft" to save.
      </p>
    `;
    resultBox.style.display = 'block';
    
    // Populate edit fields
    document.getElementById('edit_title').value = content.title || '';
    document.getElementById('edit_subtitle').value = content.subtitle || '';
    document.getElementById('edit_body').value = content.body || '';
    
    // Show edit section
    editSection.style.display = 'block';
    
    // Initialize rich text editor and sync with HTML
    initializeRichTextEditor();
    
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Handle Create Webflow Draft button
  saveBtn.addEventListener('click', async () => {
    setLoading(saveBtn, true);
    const formData = new FormData(form);
    // Track last created draft id between runs
    const currentItemIdEl = document.getElementById('currentItemId');
    const previousItemId = currentItemIdEl ? (currentItemIdEl.textContent || '').trim() : '';
    
    try {
      const payload = {
        title: document.getElementById('edit_title').value,
        subtitle: document.getElementById('edit_subtitle').value,
        body: document.getElementById('edit_body').value,
        author_id: formData.get('author_id') || null,
        category_id: formData.get('category_id') || null,
        featured_image: currentFeaturedImage,
        publish: formData.get('publish') === 'on',
        publish_date: formData.get('publish_date') ? new Date(formData.get('publish_date')).toISOString() : null,
        previous_item_id: previousItemId || null
      };
      
      // Add banner data if available
      if (currentBanner) {
        payload.banner_title = currentBanner.title;
        payload.banner_description = currentBanner.description;
        payload.banner_image = currentBanner.image;
        payload.banner_link = currentBanner.link;
        // Capitalize the category before sending to Webflow
        if (currentBanner.category) {
          payload.banner_category = currentBanner.category.charAt(0).toUpperCase() + currentBanner.category.slice(1);
        }
      }
      
      const response = await fetch('/create-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      if (response.ok && data.ok) {
        showDraftCreated(data.item, data.previewLink);
      } else {
        throw new Error(data.error || 'Failed to create draft');
      }
    } catch (error) {
      document.getElementById('editResult').innerHTML = `
        <div style="padding: 1rem; background: rgba(239, 68, 68, 0.1); border-left: 4px solid #EF4444; border-radius: 6px; color: #EF4444;">
          ❌ ${error.message}
        </div>
      `;
    } finally {
      setLoading(saveBtn, false);
    }
  });

  function showDraftCreated(item, previewLink) {
    const fieldData = item.fieldData || {};
    const isDraft = item.isDraft;

    resultBox.className = 'result success';
    resultBox.innerHTML = `
      <h2>✅ Draft Created Successfully!</h2>
      
      <div class="result-content">
        <div class="result-item">
          <strong>Status</strong>
          <span id="draftStatus">${isDraft ? '📝 Draft' : '✅ Published'}</span>
        </div>
        
        <div class="result-item">
          <strong>Item ID</strong>
          <span style="font-family: monospace; font-size: 0.875rem;" id="currentItemId">${item.id}</span>
        </div>
        
        <div class="result-item">
          <strong>Reading Time</strong>
          <span>${fieldData['reading-time-in-minutes'] || 0} min</span>
        </div>
      </div>
      
      <div class="button-group" style="margin-top: 0.75rem;">
        ${previewLink ? `
          <a href="${previewLink}" target="_blank" rel="noopener" class="btn btn-secondary">
            🔍 Preview Draft
          </a>
        ` : ''}
        <button type="button" class="btn btn-primary" id="publishDraftBtn">
          🚀 Publish Draft
        </button>
      </div>
    `;

    resultBox.style.display = 'block';
    // Keep edit section open for further edits
    editSection.style.display = 'block';
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Attach publish handler
    const publishBtn = document.getElementById('publishDraftBtn');
    if (publishBtn) {
      publishBtn.addEventListener('click', async () => {
        const currentIdEl = document.getElementById('currentItemId');
        const itemId = currentIdEl ? currentIdEl.textContent : item.id;
        if (!itemId) {
          alert('No draft to publish.');
          return;
        }
        setLoading(publishBtn, true);
        try {
          const resp = await fetch('/publish-draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId })
          });
          const data = await resp.json();
          if (!resp.ok || !data.ok) {
            throw new Error(data.error || 'Failed to publish draft');
          }
          const statusEl = document.getElementById('draftStatus');
          if (statusEl) statusEl.textContent = '✅ Published';
        } catch (e) {
          alert(e.message || 'Publish failed');
        } finally {
          setLoading(publishBtn, false);
        }
      });
    }
  }

  // Handle AI Edit button
  aiEditBtn.addEventListener('click', async () => {
    const editPrompt = document.getElementById('ai_edit_prompt').value.trim();
    
    if (!editPrompt) {
      alert('Please enter an edit instruction');
      return;
    }
    
    setLoading(aiEditBtn, true);
    
    try {
      const response = await fetch('/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: document.getElementById('edit_title').value,
          subtitle: document.getElementById('edit_subtitle').value,
          body: document.getElementById('edit_body').value,
          edit_prompt: editPrompt
        })
      });
      
      const data = await response.json();
      
      if (response.ok && data.ok) {
        // Update fields with edited content
        document.getElementById('edit_title').value = data.title;
        document.getElementById('edit_subtitle').value = data.subtitle;
        document.getElementById('edit_body').value = data.body;
        document.getElementById('ai_edit_prompt').value = '';
        
        // Sync the rich text editor with updated HTML
        if (quill) {
          syncInProgress = true;
          quill.root.innerHTML = data.body;
          syncInProgress = false;
        }
        
        // Show success message
        document.getElementById('editResult').innerHTML = `
          <div style="padding: 1rem; background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10B981; border-radius: 6px; color: #10B981;">
            ✅ ${escapeHtml(data.changes)}
          </div>
        `;
        
        setTimeout(() => {
          document.getElementById('editResult').innerHTML = '';
        }, 5000);
      } else {
        throw new Error(data.error || 'Edit failed');
      }
    } catch (error) {
      document.getElementById('editResult').innerHTML = `
        <div style="padding: 1rem; background: rgba(239, 68, 68, 0.1); border-left: 4px solid #EF4444; border-radius: 6px; color: #EF4444;">
          ❌ ${escapeHtml(error.message)}
        </div>
      `;
    } finally {
      setLoading(aiEditBtn, false);
    }
  });

  function showError(errorMessage) {
    resultBox.className = 'result error';
    resultBox.innerHTML = `
      <h2>❌ Error</h2>
      <div class="error-message">
        ${escapeHtml(errorMessage)}
      </div>
      <p style="margin-top: 1rem; color: var(--text-secondary);">
        Please check your configuration and try again.
      </p>
    `;
    resultBox.style.display = 'block';
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Image search handler
  searchImagesBtn.addEventListener('click', async () => {
    const title = document.getElementById('edit_title').value;
    const body = document.getElementById('edit_body').value;
    
    if (!title) {
      alert('Please generate content first');
      return;
    }
    
    setLoading(searchImagesBtn, true);
    imageGallery.style.display = 'none';
    
    try {
      const response = await fetch('/search-images', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body })
      });
      
      const data = await response.json();
      
      if (response.ok && data.ok) {
        displayImageResults(data.query, data.images);
      } else {
        throw new Error(data.error || 'Image search failed');
      }
    } catch (error) {
      alert('Failed to search images: ' + error.message);
    } finally {
      setLoading(searchImagesBtn, false);
    }
  });

  function displayImageResults(query, images) {
    imageQuery.textContent = query;
    imageGrid.innerHTML = '';
    
    if (!images || images.length === 0) {
      imageGrid.innerHTML = '<p style="color: #6B7280;">No images found. Try a different search.</p>';
      imageGallery.style.display = 'block';
      return;
    }
    
    images.forEach(img => {
      const card = document.createElement('div');
      card.style.cssText = `
        cursor: pointer;
        border: 3px solid transparent;
        border-radius: 8px;
        overflow: hidden;
        transition: all 0.2s;
        background: white;
      `;
      
      card.innerHTML = `
        <img 
          src="${img.thumb}" 
          alt="${escapeHtml(img.alt)}"
          style="width: 100%; height: 150px; object-fit: cover; display: block;"
        >
        <div style="padding: 0.5rem; font-size: 0.75rem; color: #6B7280;">
          Photo by <a href="${img.photographer_url}" target="_blank" rel="noopener" style="color: #4F46E5;">${escapeHtml(img.photographer)}</a>
        </div>
      `;
      
      card.addEventListener('click', () => {
        // Remove selection from all cards
        document.querySelectorAll('#imageGrid > div').forEach(c => {
          c.style.border = '3px solid transparent';
        });
        
        // Select this card
        card.style.border = '3px solid #4F46E5';
        selectedImageUrl = img.url;
        
        // Update the featured image URL input if it exists
        const featuredImageInput = document.getElementById('featured_image_url');
        if (featuredImageInput) {
          featuredImageInput.value = img.url;
        }
        
        // Store for draft creation
        currentFeaturedImage = {
          url: img.url,
          alt: img.alt
        };
        
        console.log('Selected image:', currentFeaturedImage);
      });
      
      card.addEventListener('mouseenter', () => {
        if (card.style.borderColor !== 'rgb(79, 70, 229)') {
          card.style.border = '3px solid #E5E7EB';
        }
      });
      
      card.addEventListener('mouseleave', () => {
        if (card.style.borderColor !== 'rgb(79, 70, 229)') {
          card.style.border = '3px solid transparent';
        }
      });
      
      imageGrid.appendChild(card);
    });
    
    imageGallery.style.display = 'block';
  }

  // Banner generation handler
  generateBannerBtn.addEventListener('click', async () => {
    const title = document.getElementById('edit_title').value;
    const body = document.getElementById('edit_body').value;
    
    if (!title || !body) {
      alert('Please generate content first');
      return;
    }
    
    setLoading(generateBannerBtn, true);
    
    try {
      const response = await fetch('/generate-banner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body })
      });
      
      const data = await response.json();
      
      if (response.ok && data.ok) {
        displayBanner(data.banner);
      } else {
        throw new Error(data.error || 'Banner generation failed');
      }
    } catch (error) {
      alert('Failed to generate banner: ' + error.message);
    } finally {
      setLoading(generateBannerBtn, false);
    }
  });

  function displayBanner(banner) {
    // Store banner data
    currentBanner = banner;
    
    // Populate fields
    document.getElementById('banner_title').value = banner.title || '';
    document.getElementById('banner_description').value = banner.description || '';
    document.getElementById('banner_link').value = banner.link || '';
    
    // Show image preview
    const imagePreview = document.getElementById('banner_image_preview');
    if (banner.image) {
      imagePreview.innerHTML = `
        <img 
          src="${banner.image}" 
          alt="${escapeHtml(banner.title)}"
          style="max-width: 200px; border-radius: 8px; border: 1px solid var(--border);"
        >
      `;
    } else {
      imagePreview.innerHTML = '<p style="color: #6B7280; font-size: 0.875rem;">No image available</p>';
    }
    
    // Show banner fields
    bannerFields.style.display = 'block';
    
    console.log('Banner generated:', banner);
  }

  // Auto-link detection handler
  let lastAutoLinkMatches = null;
  if (autoLinkBtn) {
    autoLinkBtn.addEventListener('click', async () => {
      const title = document.getElementById('edit_title').value;
      const body = document.getElementById('edit_body').value;
      if (!title && !body) {
        alert('Please generate content first');
        return;
      }
      setLoading(autoLinkBtn, true);
      autoLinkResults.style.display = 'none';
      autoLinkArtists.innerHTML = '';
      autoLinkShows.innerHTML = '';
      autoLinkServices.innerHTML = '';
      if (autoLinkSummary) autoLinkSummary.innerHTML = '';
      try {
        const resp = await fetch('/auto-link', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, body })
        });
        const data = await resp.json();
        if (!resp.ok || !data.ok) {
          throw new Error(data.error || 'Auto-link detection failed');
        }
        const matches = data.matches || {};
        lastAutoLinkMatches = matches;
        const artists = matches.artists || [];
        const shows = matches.shows || [];
        const services = matches.services || [];
        const matchedCategories = matches.matched_categories || [];
        
        const parts = [];
        if (artists.length) {
          autoLinkArtists.innerHTML = `
            <div style="margin-bottom: 0.5rem; font-weight: 600;">Artists</div>
            <ul style="margin: 0; padding-left: 1rem;">
              ${artists.map(a => `<li><a href="${a.url}" target="_blank" rel="noopener">${escapeHtml(a.title || a.url)}</a></li>`).join('')}
            </ul>
          `;
          parts.push('artists');
        } else {
          autoLinkArtists.innerHTML = '';
        }
        
        if (shows.length) {
          autoLinkShows.innerHTML = `
            <div style="margin: 0.75rem 0 0.5rem; font-weight: 600;">Shows</div>
            <ul style="margin: 0; padding-left: 1rem;">
              ${shows.map(s => `<li><a href="${s.url}" target="_blank" rel="noopener">${escapeHtml(s.title || s.url)}</a></li>`).join('')}
            </ul>
          `;
          parts.push('shows');
        } else {
          autoLinkShows.innerHTML = '';
        }
        
        if (services.length) {
          const catBadge = matchedCategories.length
            ? `<div style="margin-bottom: 0.25rem; color: #6B7280; font-size: 0.85rem;">Matched intents: ${matchedCategories.map(c => c[0].toUpperCase() + c.slice(1)).join(', ')}</div>`
            : '';
          autoLinkServices.innerHTML = `
            <div style="margin: 0.75rem 0 0.25rem; font-weight: 600;">Services</div>
            ${catBadge}
            <ul style="margin: 0; padding-left: 1rem;">
              ${services.map(sv => `<li><a href="${sv.url}" target="_blank" rel="noopener">${escapeHtml(sv.title || sv.url)}</a></li>`).join('')}
            </ul>
          `;
          parts.push('services');
        } else {
          autoLinkServices.innerHTML = '';
        }
        
        if (parts.length === 0) {
          autoLinkArtists.innerHTML = `
            <div style="color: #6B7280;">No artist, show, or service matches found in your content.</div>
          `;
        }
        
        autoLinkResults.style.display = 'block';
        autoLinkResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (err) {
        alert(err.message || 'Auto-link detection failed');
      } finally {
        setLoading(autoLinkBtn, false);
      }
    });
  }

  // Helpers for link insertion
  function isInsideProhibited(node) {
    let n = node;
    while (n) {
      if (n.nodeType === 1) {
        const tag = n.tagName;
        if (tag === 'A' || tag === 'SUP' || tag === 'CODE' || tag === 'PRE' || tag === 'SCRIPT' || tag === 'STYLE') return true;
      }
      n = n.parentNode;
    }
    return false;
  }

  function buildServiceKeywordMap(serviceUrl, categories) {
    // Minimal sensible keyword set per intent
    const map = [];
    const catSet = new Set(categories || []);
    if (catSet.has('group')) {
      ['group tickets', 'group tix', 'group sales', 'group rate', 'groups'].forEach(k => map.push({ text: k, url: serviceUrl }));
    }
    if (catSet.has('vip')) {
      ['vip', 'vip tix', 'vip package', 'premium seat', 'concierge'].forEach(k => map.push({ text: k, url: serviceUrl }));
    }
    if (catSet.has('corporate')) {
      ['corporate', 'team building', 'company outing', 'client event', 'retreat'].forEach(k => map.push({ text: k, url: serviceUrl }));
    }
    if (catSet.has('educational')) {
      ['educational', 'education', 'student', 'master class', 'workshop', 'student matinee'].forEach(k => map.push({ text: k, url: serviceUrl }));
    }
    if (catSet.has('holiday')) {
      ['holiday', 'christmas', 'hanukkah', 'valentine', 'gift'].forEach(k => map.push({ text: k, url: serviceUrl }));
    }
    return map;
  }

  function applyLinksToHtml(html, entries, maxPerEntry = 1) {
    const container = document.createElement('div');
    container.innerHTML = html || '';
    const appliedCount = new Map(); // text->count
    const summary = [];

    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (isInsideProhibited(node.parentNode)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });

    function tryApplyInTextNode(textNode, entry) {
      const limit = appliedCount.get(entry.text) || 0;
      if (limit >= maxPerEntry) return false;
      const lower = textNode.data.toLowerCase();
      const target = entry.text.toLowerCase();
      let idx = lower.indexOf(target);
      if (idx < 0) return false;
      // Check word boundaries for single-word anchors
      const isMultiWord = /\s/.test(entry.text.trim());
      if (!isMultiWord) {
        const before = idx === 0 ? '' : lower[idx - 1];
        const after = idx + target.length < lower.length ? lower[idx + target.length] : '';
        const isBoundary = (ch) => !(/[a-z0-9]/.test(ch || ''));
        if (!(isBoundary(before) && isBoundary(after))) {
          return false;
        }
      }
      const original = textNode.data.slice(idx, idx + entry.text.length);
      const a = document.createElement('a');
      a.href = entry.url;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = original;
      const beforeText = document.createTextNode(textNode.data.slice(0, idx));
      const afterText = document.createTextNode(textNode.data.slice(idx + entry.text.length));
      const parent = textNode.parentNode;
      parent.insertBefore(beforeText, textNode);
      parent.insertBefore(a, textNode);
      parent.insertBefore(afterText, textNode);
      parent.removeChild(textNode);
      appliedCount.set(entry.text, limit + 1);
      // Record summary only once per entry
      if (!summary.find(s => s.text === entry.text && s.url === entry.url)) {
        summary.push({ text: entry.text, url: entry.url });
      }
      return true;
    }

    // Iterate over text nodes and apply entries
    let node;
    const activeEntries = entries.slice(); // copy
    while ((node = walker.nextNode())) {
      for (let i = 0; i < activeEntries.length; i++) {
        tryApplyInTextNode(node, activeEntries[i]);
      }
    }

    return { html: container.innerHTML, summary };
  }

  // Import links with AI via /edit, using a composed prompt and JSON diff application
  if (importLinksBtn) {
    importLinksBtn.addEventListener('click', async () => {
      const title = document.getElementById('edit_title').value;
      const subtitle = document.getElementById('edit_subtitle').value || '';
      const bodyEl = document.getElementById('edit_body');
      const oldBody = bodyEl.value || '';
      if (!lastAutoLinkMatches) {
        alert('Please click "Find Matches" first.');
        return;
      }
      const matches = lastAutoLinkMatches || {};
      const artists = matches.artists || [];
      const shows = matches.shows || [];
      const services = matches.services || [];

      const candidates = [];
      artists.forEach(a => { if (a.title && a.url) candidates.push({ type: 'Artist', title: a.title, url: a.url }); });
      shows.forEach(s => { if (s.title && s.url) candidates.push({ type: 'Show', title: s.title, url: s.url }); });
      services.forEach(sv => { if (sv.title && sv.url) candidates.push({ type: 'Service', title: sv.title, url: sv.url }); });
      if (!candidates.length) {
        alert('No link candidates available.');
        return;
      }

      const linksList = candidates.map(c => `- [${c.type}] ${c.title} -> ${c.url}`).join('\\n');
      const editPrompt = `
Embed hyperlinks into the HTML body where they fit naturally, using ONLY existing words/phrases as anchor text.
- Anchor text should be the relevant word sequence already present (e.g., artist/show names, or service phrases like "group tickets" or "VIP").
- Do NOT add a "Sources" section or any new sections.
- Preserve all existing HTML, including <sup><a href='...'>[n]</a></sup> citations.
- If a link does not fit naturally, skip it.
- Make minimal edits beyond wrapping anchor tags.
Links to consider:
${linksList}
Return JSON diff as previously specified (title, subtitle or 'NO CHANGE', and body_changes with precise find/replace).
      `.trim();

      setLoading(importLinksBtn, true);
      if (autoLinkSummary) autoLinkSummary.innerHTML = '';
      try {
        const resp = await fetch('/edit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title,
            subtitle,
            body: oldBody,
            edit_prompt: editPrompt
          })
        });
        const data = await resp.json();
        if (!resp.ok || !data.ok) {
          throw new Error(data.error || 'AI link insertion failed');
        }
        const newBody = data.body || oldBody;
        bodyEl.value = newBody;
        if (quill) {
          syncInProgress = true;
          quill.root.innerHTML = newBody;
          syncInProgress = false;
        }

        // Summarize newly inserted links by comparing anchors before vs after, filtered to our candidate URLs
        function extractAnchors(html) {
          const frag = document.createElement('div');
          frag.innerHTML = html || '';
          const out = [];
          frag.querySelectorAll('a[href]').forEach(a => {
            out.push({ href: a.getAttribute('href') || '', text: (a.textContent || '').trim() });
          });
          return out;
        }
        const before = extractAnchors(oldBody);
        const after = extractAnchors(newBody);
        const candidateUrls = new Set(candidates.map(c => c.url));
        const beforeSet = new Set(before.filter(a => candidateUrls.has(a.href)).map(a => a.href + '|' + a.text));
        const added = after.filter(a => candidateUrls.has(a.href) && !beforeSet.has(a.href + '|' + a.text));

        if (autoLinkSummary) {
          if (added.length) {
            autoLinkSummary.innerHTML = `
              <div style="margin-top: 0.5rem;">
                <div style="font-weight:600; margin-bottom: 0.25rem;">Inserted Links:</div>
                <ul style="margin:0; padding-left: 1rem;">
                  ${added.map(s => `<li>${escapeHtml(s.text)} -> <a href="${s.href}" target="_blank" rel="noopener">${s.href}</a></li>`).join('')}
                </ul>
              </div>
            `;
          } else {
            autoLinkSummary.innerHTML = `<div style="color:#6B7280;">No new links were inserted.</div>`;
          }
          autoLinkResults.style.display = 'block';
          autoLinkResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      } catch (e) {
        alert(e.message || 'Failed to insert links');
      } finally {
        setLoading(importLinksBtn, false);
      }
    });
  }
})();
