// KINO-GEIST AI Studio - Main Application Logic

class KinoGeistStudio {
    constructor() {
        // The project state will be loaded from the server.
        this.project = null;

        // Wait for the DOM to be fully loaded before initializing
        document.addEventListener('DOMContentLoaded', () => this.init());
    }

    async init() {
        console.log('Initializing KINO-GEIST AI Studio...');
        this.setupNavigation();
        await this.loadProject(); // Load data from the server
        this.renderAll();
        this.setupEventListeners();
        console.log('Studio Initialized.');
    }

    //----------------------------------------------------------------
    // DATA HANDLING (Load & Save)
    //----------------------------------------------------------------

    async loadProject() {
        try {
            const response = await fetch('/api/project');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.project = await response.json();
            this.showNotification('Project loaded successfully!', 'success');
        } catch (error) {
            console.error('Failed to load project:', error);
            this.showNotification('Error loading project data. Please start the server.', 'error');
            // Load a default structure if the server fails, so the app doesn't break
            this.project = this.getFallbackProjectData();
        }
    }

    async saveProject() {
        if (!this.project) return;
        try {
            // Before saving, update the story treatment from the editor
            const editor = document.getElementById('story-editor');
            if (editor) {
                this.project.story.treatment = editor.innerHTML;
            }

            const response = await fetch('/api/project', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.project),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.showNotification('Project saved!', 'success');
        } catch (error) {
            console.error('Failed to save project:', error);
            this.showNotification('Error saving project.', 'error');
        }
    }

    //----------------------------------------------------------------
    // RENDER SYSTEM - Populates the UI from the project state
    //----------------------------------------------------------------
    renderAll() {
        if (!this.project) return;
        this.renderWriter();
        this.renderStoryBible();
        this.renderVisualDNA();
        this.renderShotLab();
        this.renderAssetNexus();
        this.renderScreeningRoom();
    }

    renderWriter() {
        const editor = document.getElementById('story-editor');
        if (editor) editor.innerHTML = this.project.story.treatment;
    }

    renderStoryBible() {
        this.renderBibleSection('characters', 'characters-grid-content', this.project.storyBible.characters, this.createCharacterCard);
        this.renderBibleSection('locations', 'locations-grid-content', this.project.storyBible.locations, this.createLocationCard);
        this.renderBibleSection('props', 'props-grid-content', this.project.storyBible.props, this.createPropCard);
        
        const themesContainer = document.getElementById('themes-content-area');
        if(themesContainer) {
            themesContainer.innerHTML = this.project.storyBible.themes.map(theme => `
                <div class="card" data-theme-id="${theme.id}">
                    <div class="card-header">
                        <h3>${theme.title}</h3>
                        <button class="btn btn--xs btn--outline delete-card-btn" onclick="window.kinoGeistApp.confirmDeleteTheme(${theme.id})" title="Delete theme">
                            ×
                        </button>
                    </div>
                    <div class="card-content">
                        <p>${theme.description}</p>
                    </div>
                </div>
            `).join('');
        }
        
        // Show empty state message if no content
        this.showEmptyStatesIfNeeded();
    }
    
    showEmptyStatesIfNeeded() {
        const sections = [
            { container: 'characters-grid-content', data: this.project.storyBible.characters, message: 'No characters yet. Use "Auto-Populate" to extract from your script or add manually.' },
            { container: 'locations-grid-content', data: this.project.storyBible.locations, message: 'No locations yet. Use "Auto-Populate" to extract from your script or add manually.' },
            { container: 'props-grid-content', data: this.project.storyBible.props, message: 'No props yet. Use "Auto-Populate" to extract from your script or add manually.' },
            { container: 'themes-content-area', data: this.project.storyBible.themes, message: 'No themes yet. Use "Auto-Populate" to extract from your script or add manually.' }
        ];
        
        sections.forEach(section => {
            const container = document.getElementById(section.container);
            if (container && section.data.length === 0) {
                container.innerHTML = `<p class="empty-state">${section.message}</p>`;
            }
        });
    }
    
    renderBibleSection(tabName, containerId, data, cardCreator) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = data.map(cardCreator).join('');
        }
    }

    createCharacterCard(char) {
        const linkedBackstory = this.autoLinkContent(char.backstory || 'No backstory available');
        return `
            <div class="card character-card" data-character-id="${char.id}">
                <div class="card-header">
                    <h3>${char.name}</h3>
                    <div class="card-header-actions">
                        <button class="btn btn--xs btn--primary" onclick="window.kinoGeistApp.navigateToCharacterDNA(${char.id})" title="Go to Visual DNA Kit">
                            DNA Kit
                        </button>
                        <button class="btn btn--xs btn--outline delete-card-btn" onclick="window.kinoGeistApp.confirmDeleteCharacter(${char.id})" title="Delete character">
                            ×
                        </button>
                    </div>
                </div>
                <div class="card-content">
                    <p><strong>Role:</strong> ${char.role}</p>
                    <p><strong>Occupation:</strong> ${char.occupation || 'Not specified'}</p>
                    <p>${linkedBackstory}</p>
                    <div class="character-traits">
                        ${(char.traits || []).map(trait => `<span class="trait-tag">${trait}</span>`).join('')}
                    </div>
                </div>
            </div>`;
    }

    createLocationCard(loc) {
        const linkedDescription = this.autoLinkContent(loc.description);
        return `
            <div class="card location-card" data-location-id="${loc.id}">
                <div class="card-header">
                    <h3>${loc.name}</h3>
                    <div class="card-header-actions">
                        <button class="btn btn--xs btn--primary" onclick="window.kinoGeistApp.navigateToLocationDNA(${loc.id})" title="Go to Visual DNA Kit">
                            DNA Kit
                        </button>
                        <button class="btn btn--xs btn--outline delete-card-btn" onclick="window.kinoGeistApp.confirmDeleteLocation(${loc.id})" title="Delete location">
                            ×
                        </button>
                    </div>
                </div>
                <div class="card-content"><p>${linkedDescription}</p></div>
            </div>`;
    }

    createPropCard(prop) {
        return `
            <div class="card prop-card" data-prop-id="${prop.id}">
                <div class="card-header">
                    <h3>${prop.name}</h3>
                    <button class="btn btn--xs btn--outline delete-card-btn" onclick="window.kinoGeistApp.confirmDeleteProp(${prop.id})" title="Delete prop">
                        ×
                    </button>
                </div>
                <div class="card-content"><p>${prop.description}</p></div>
            </div>`;
    }

    renderVisualDNA() {
        const globalStyle = this.project.visualDNA.globalStyle;
        document.getElementById('color-palette').value = globalStyle.palette || '';
        document.getElementById('lighting-style').value = globalStyle.lighting || '';
        document.getElementById('cinematic-influences').value = globalStyle.influences || '';

        const charKitsContainer = document.getElementById('character-dna-kits');
        if(charKitsContainer) {
            charKitsContainer.innerHTML = this.project.visualDNA.characterKits.map(kit => `
                <div class="dna-kit" data-kit-type="character" data-kit-id="${kit.charId}">
                    <h4>${kit.name}</h4>
                    <div class="anchor-image-container">
                        ${kit.anchorImage ? 
                            `<img src="${kit.anchorImage}" alt="${kit.name} reference" class="anchor-image-preview">
                             <div class="image-actions">
                                <button class="btn btn--sm btn--outline" onclick="window.kinoGeistApp.uploadAnchorImage('character', ${kit.charId})">Change Image</button>
                                <button class="btn btn--sm btn--outline" onclick="window.kinoGeistApp.removeAnchorImage('character', ${kit.charId})">Remove</button>
                             </div>` :
                            `<div class="anchor-image-placeholder" onclick="window.kinoGeistApp.uploadAnchorImage('character', ${kit.charId})">
                                Click to upload anchor image
                             </div>`
                        }
                    </div>
                    <div class="lexicon-editor">
                        <label>Prompt Lexicon</label>
                        <textarea class="form-control lexicon-textarea" data-kit-type="character" data-kit-id="${kit.charId}">${kit.promptLexicon || ''}</textarea>
                    </div>
                    <div class="kit-actions">
                        <button class="btn btn--sm btn--primary save-kit-btn" data-kit-type="character" data-kit-id="${kit.charId}">Save Kit</button>
                    </div>
                </div>
            `).join('');
        }
        
        const locKitsContainer = document.getElementById('location-dna-kits');
        if(locKitsContainer) {
            locKitsContainer.innerHTML = this.project.visualDNA.locationKits.map(kit => `
                <div class="dna-kit" data-kit-type="location" data-kit-id="${kit.locId}">
                    <h4>${kit.name}</h4>
                    <div class="anchor-image-container">
                        ${kit.anchorImage ? 
                            `<img src="${kit.anchorImage}" alt="${kit.name} reference" class="anchor-image-preview">
                             <div class="image-actions">
                                <button class="btn btn--sm btn--outline" onclick="window.kinoGeistApp.uploadAnchorImage('location', ${kit.locId})">Change Image</button>
                                <button class="btn btn--sm btn--outline" onclick="window.kinoGeistApp.removeAnchorImage('location', ${kit.locId})">Remove</button>
                             </div>` :
                            `<div class="anchor-image-placeholder" onclick="window.kinoGeistApp.uploadAnchorImage('location', ${kit.locId})">
                                Click to upload anchor image
                             </div>`
                        }
                    </div>
                    <div class="lexicon-editor">
                        <label>Prompt Lexicon</label>
                        <textarea class="form-control lexicon-textarea" data-kit-type="location" data-kit-id="${kit.locId}">${kit.promptLexicon || ''}</textarea>
                    </div>
                    <div class="kit-actions">
                        <button class="btn btn--sm btn--primary save-kit-btn" data-kit-type="location" data-kit-id="${kit.locId}">Save Kit</button>
                    </div>
                </div>
            `).join('');
        }
        
        // Add event listeners for save buttons
        this.setupVisualDNAEventListeners();
    }

    renderShotLab() {
        const scenesContainer = document.getElementById('scenes-list-content');
        if(scenesContainer) {
            scenesContainer.innerHTML = this.project.shotLab.scenes.map(scene => `
                <div class="scene-item" data-scene-id="${scene.id}">
                    <div class="scene-content">
                        <h4>${scene.title}</h4>
                        <p>${scene.description}</p>
                    </div>
                    <div class="scene-item-actions">
                        <button class="btn btn--xs btn--outline" onclick="window.kinoGeistApp.openSceneEditor(${scene.id})" title="Edit scene">✎</button>
                        <button class="btn btn--xs btn--outline delete-card-btn" onclick="window.kinoGeistApp.confirmDeleteScene(${scene.id})" title="Delete scene">×</button>
                    </div>
                </div>
            `).join('');
        }
        
        // Clear scene details initially
        const sceneInfoContainer = document.getElementById('scene-info-content');
        const shotsListContainer = document.getElementById('shots-list-content');
        if (sceneInfoContainer) {
            sceneInfoContainer.innerHTML = '<p class="placeholder-text">Select a scene to view details and manage shots</p>';
        }
        if (shotsListContainer) {
            shotsListContainer.innerHTML = '';
        }
        
        // Disable buttons initially
        document.getElementById('ai-breakdown-btn').disabled = true;
        document.getElementById('add-shot-btn').disabled = true;
        
        // Add active class to first scene if exists
        const firstScene = scenesContainer ? scenesContainer.querySelector('.scene-item') : null;
        if(firstScene) {
            firstScene.classList.add('active');
            this.selectScene(firstScene.dataset.sceneId);
        }
    }

    selectScene(sceneId) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return;

        // Update scene info panel with auto-linked content
        const sceneInfoContainer = document.getElementById('scene-info-content');
        if (sceneInfoContainer) {
            const linkedDescription = this.autoLinkContent(scene.description);
            sceneInfoContainer.innerHTML = `
                <h4>${scene.title}</h4>
                <p>${linkedDescription}</p>
            `;
        }

        // Enable buttons
        document.getElementById('ai-breakdown-btn').disabled = false;
        document.getElementById('add-shot-btn').disabled = false;

        // Display context suggestions
        const suggestions = this.getContextSuggestions(sceneId);
        this.displayContextSuggestions(suggestions);

        // Render shots list
        this.renderShotsList(sceneId);
        
        // Render storyboard for scene
        this.renderStoryboardForScene(sceneId);
        
        // Store current scene
        this.currentSelectedScene = sceneId;
    }

    renderShotsList(sceneId) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return;

        const shotsListContainer = document.getElementById('shots-list-content');
        if (shotsListContainer) {
            shotsListContainer.innerHTML = scene.shots.map(shot => `
                <div class="shot-item" data-shot-id="${shot.id}">
                    <div class="shot-info">
                        <h5>${shot.type}</h5>
                        <p>${shot.description}</p>
                    </div>
                    <div class="shot-actions">
                        <button class="btn btn--xs btn--outline" onclick="window.kinoGeistApp.editShot(${sceneId}, ${shot.id})">Edit</button>
                        <button class="btn btn--xs btn--outline" onclick="window.kinoGeistApp.deleteShot(${sceneId}, ${shot.id})">Delete</button>
                    </div>
                </div>
            `).join('');
        }
    }

    renderStoryboardForScene(sceneId) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return;

        const storyboardContainer = document.getElementById('storyboard-grid-content');
        if(storyboardContainer) {
            storyboardContainer.innerHTML = scene.shots.map(shot => `
                <div class="storyboard-frame" data-shot-id="${shot.id}">
                    <div class="frame-placeholder">
                        ${shot.image ? `<img src="${shot.image}" alt="shot image">` : 'Upload Image'}
                    </div>
                    <div class="frame-details">
                        <input type="text" class="form-control" value="${shot.type}: ${shot.description}">
                    </div>
                    <button class="frame-workbench-btn" data-shot-id="${shot.id}" data-scene-id="${sceneId}">
                        Workbench
                    </button>
                </div>
            `).join('');
            
            // Add event listeners for workbench buttons
            storyboardContainer.querySelectorAll('.frame-workbench-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openPromptWorkbench(btn.dataset.shotId, btn.dataset.sceneId);
                });
            });
        }
    }

    //----------------------------------------------------------------
    // COMPREHENSIVE ASSET NEXUS MANAGEMENT
    //----------------------------------------------------------------
    renderAssetNexus() {
        const assets = this.project.assets || [];
        this.renderAssetStats(assets);
        this.renderAssetGrid(assets);
    }

    renderAssetStats(assets) {
        const statsContainer = document.getElementById('asset-stats');
        if (!statsContainer) return;

        const stats = {
            total: assets.length,
            approved: assets.filter(a => a.status === 'approved').length,
            pending: assets.filter(a => a.status === 'pending').length,
            images: assets.filter(a => a.assetType === 'image').length,
            videos: assets.filter(a => a.assetType === 'video').length,
            audio: assets.filter(a => a.assetType === 'audio').length
        };

        statsContainer.innerHTML = `
            <div class="asset-stat">
                <div class="asset-stat-number">${stats.total}</div>
                <div class="asset-stat-label">Total Assets</div>
            </div>
            <div class="asset-stat">
                <div class="asset-stat-number">${stats.approved}</div>
                <div class="asset-stat-label">Approved</div>
            </div>
            <div class="asset-stat">
                <div class="asset-stat-number">${stats.pending}</div>
                <div class="asset-stat-label">Pending</div>
            </div>
            <div class="asset-stat">
                <div class="asset-stat-number">${stats.images}</div>
                <div class="asset-stat-label">Images</div>
            </div>
            <div class="asset-stat">
                <div class="asset-stat-number">${stats.videos}</div>
                <div class="asset-stat-label">Videos</div>
            </div>
            <div class="asset-stat">
                <div class="asset-stat-number">${stats.audio}</div>
                <div class="asset-stat-label">Audio</div>
            </div>
        `;
    }

    renderAssetGrid(assets) {
        const gridContainer = document.getElementById('asset-grid-content');
        if (!gridContainer) return;

        if (assets.length === 0) {
            gridContainer.innerHTML = `
                <div class="asset-empty-state">
                    <h3>No Assets Yet</h3>
                    <p>Upload your first visual asset or document to get started.</p>
                    <div style="display: flex; gap: var(--space-12); justify-content: center; margin-top: var(--space-16);">
                        <button class="btn btn--primary" onclick="window.kinoGeistApp.openAssetUploadModal('visual')">
                            Upload Visual Asset
                        </button>
                        <button class="btn btn--outline" onclick="window.kinoGeistApp.openAssetUploadModal('text')">
                            Upload Document
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        // Group assets by parent ID for version stacks
        const assetGroups = this.groupAssetsByVersion(assets);
        gridContainer.innerHTML = assetGroups.map(group => this.createAssetGroup(group)).join('');

        // Add event listeners
        this.setupAssetEventListeners();
    }

    groupAssetsByVersion(assets) {
        const groups = [];
        const processed = new Set();

        assets.forEach(asset => {
            if (processed.has(asset.id)) return;

            if (asset.parentId === null) {
                // This is a parent asset, find all its versions
                const versions = assets.filter(a => a.parentId === asset.id || a.id === asset.id);
                versions.sort((a, b) => b.version - a.version); // Latest first
                groups.push(versions);
                versions.forEach(v => processed.add(v.id));
            } else if (!processed.has(asset.id)) {
                // This is an orphaned version, treat as standalone
                groups.push([asset]);
                processed.add(asset.id);
            }
        });

        return groups;
    }

    createAssetGroup(versions) {
        const latest = versions[0]; // Latest version
        const hasMultipleVersions = versions.length > 1;
        
        return `
            <div class="asset-card ${latest.status}" data-asset-id="${latest.id}">
                ${this.createAssetPreview(latest)}
                <div class="asset-card__status ${latest.status}">${latest.status}</div>
                
                <div class="asset-card__header">
                    <h4 class="asset-card__title">${latest.name}</h4>
                    <span class="asset-card__type">${latest.assetType}</span>
                </div>
                
                <div class="asset-card__body">
                    ${hasMultipleVersions ? `<div class="version-indicator">v${latest.version} (${versions.length} versions)</div>` : ''}
                    
                    ${latest.aiAnalysis ? `
                        <div class="asset-card__ai-analysis">
                            <strong>AI Analysis:</strong><br>
                            ${this.truncateText(latest.aiAnalysis, 150)}
                        </div>
                    ` : ''}
                    
                    ${latest.content ? `
                        <div class="asset-card__content">${this.truncateText(latest.content, 200)}</div>
                    ` : ''}
                    
                    <div class="asset-card__tags">
                        ${(latest.tags || []).map(tag => `<span class="asset-tag">${tag}</span>`).join('')}
                    </div>
                    
                    <div class="asset-card__meta">
                        <span>Category: ${latest.category}</span>
                        <span>${this.formatFileSize(latest.size)}</span>
                    </div>
                    
                    <div class="asset-card__meta">
                        <span>Uploaded: ${new Date(latest.uploadDate).toLocaleDateString()}</span>
                    </div>
                </div>
                
                <div class="asset-card__actions">
                    <button class="btn btn--sm btn--outline asset-view-btn" data-asset-id="${latest.id}">
                        View Details
                    </button>
                    ${latest.status === 'pending' ? `
                        <button class="btn btn--sm btn--approve asset-approve-btn" data-asset-id="${latest.id}">
                            Approve
                        </button>
                        <button class="btn btn--sm btn--reject asset-reject-btn" data-asset-id="${latest.id}">
                            Reject
                        </button>
                    ` : ''}
                    ${['image', 'video'].includes(latest.assetType) ? `
                        <button class="btn btn--sm btn--link asset-link-btn" data-asset-id="${latest.id}">
                            Link to Shot
                        </button>
                    ` : ''}
                    ${latest.assetType === 'text' ? `
                        <button class="btn btn--sm btn--outline asset-use-btn" data-asset-id="${latest.id}">
                            Use in Writer's Room
                        </button>
                    ` : ''}
                    <button class="btn btn--sm btn--outline asset-version-btn" data-asset-id="${latest.id}">
                        Add Version
                    </button>
                    <button class="btn btn--sm btn--outline delete-card-btn asset-delete-btn" data-asset-id="${latest.id}">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }

    createAssetPreview(asset) {
        switch (asset.assetType) {
            case 'image':
                return `
                    <div class="asset-card__preview">
                        <img src="${asset.thumbnail || `/assets/${asset.fileName}`}" alt="${asset.name}" loading="lazy">
                    </div>
                `;
            case 'video':
                return `
                    <div class="asset-card__preview">
                        <video muted>
                            <source src="/assets/${asset.fileName}" type="video/mp4">
                        </video>
                    </div>
                `;
            case 'audio':
                return `
                    <div class="asset-card__preview">
                        <div class="file-icon">🎵</div>
                    </div>
                `;
            case 'text':
            default:
                return `
                    <div class="asset-card__preview">
                        <div class="file-icon">📄</div>
                    </div>
                `;
        }
    }

    setupAssetEventListeners() {
        const gridContainer = document.getElementById('asset-grid-content');
        if (!gridContainer) return;

        // View asset details
        gridContainer.querySelectorAll('.asset-view-btn').forEach(btn => {
            btn.addEventListener('click', () => this.viewAssetDetails(btn.dataset.assetId));
        });

        // Approve/Reject actions
        gridContainer.querySelectorAll('.asset-approve-btn').forEach(btn => {
            btn.addEventListener('click', () => this.updateAssetStatus(btn.dataset.assetId, 'approved'));
        });

        gridContainer.querySelectorAll('.asset-reject-btn').forEach(btn => {
            btn.addEventListener('click', () => this.updateAssetStatus(btn.dataset.assetId, 'rejected'));
        });

        // Link to shot
        gridContainer.querySelectorAll('.asset-link-btn').forEach(btn => {
            btn.addEventListener('click', () => this.linkAssetToShot(btn.dataset.assetId));
        });

        // Use in Writer's Room
        gridContainer.querySelectorAll('.asset-use-btn').forEach(btn => {
            btn.addEventListener('click', () => this.useAssetInWriter(btn.dataset.assetId));
        });

        // Add version
        gridContainer.querySelectorAll('.asset-version-btn').forEach(btn => {
            btn.addEventListener('click', () => this.addAssetVersion(btn.dataset.assetId));
        });

        // Delete asset
        gridContainer.querySelectorAll('.asset-delete-btn').forEach(btn => {
            btn.addEventListener('click', () => this.confirmDeleteAsset(btn.dataset.assetId));
        });
    }

    //----------------------------------------------------------------
    // ASSET UPLOAD AND MODAL MANAGEMENT
    //----------------------------------------------------------------
    openAssetUploadModal(type = 'visual') {
        const modal = document.getElementById('asset-upload-modal');
        const uploadZone = document.getElementById('asset-upload-zone');
        const metadataForm = document.getElementById('asset-metadata-form');
        const aiAnalysisSection = document.getElementById('ai-analysis-section');
        
        if (!modal) return;

        // Reset modal state
        metadataForm.style.display = 'none';
        aiAnalysisSection.style.display = 'none';
        document.getElementById('confirm-asset-upload').disabled = true;
        
        // Configure upload zone based on type
        const acceptTypes = type === 'visual' ? 'image/*,video/*,audio/*' : '.txt,.md,.pdf';
        this.currentUploadType = type;
        this.selectedFile = null;

        // Setup drag and drop
        uploadZone.onclick = () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = acceptTypes;
            input.onchange = (e) => this.handleFileSelection(e.target.files[0]);
            input.click();
        };

        uploadZone.ondragover = (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        };

        uploadZone.ondragleave = () => {
            uploadZone.classList.remove('dragover');
        };

        uploadZone.ondrop = (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelection(e.dataTransfer.files[0]);
            }
        };

        // Setup modal close events
        document.getElementById('asset-modal-close-btn').onclick = () => modal.classList.add('hidden');
        document.getElementById('cancel-asset-upload').onclick = () => modal.classList.add('hidden');
        document.getElementById('confirm-asset-upload').onclick = () => this.uploadSelectedAsset();

        modal.classList.remove('hidden');
    }

    async handleFileSelection(file) {
        if (!file) return;

        this.selectedFile = file;
        const metadataForm = document.getElementById('asset-metadata-form');
        const aiAnalysisSection = document.getElementById('ai-analysis-section');
        
        // Show metadata form
        metadataForm.style.display = 'block';
        
        // Set default category based on file type
        const fileExtension = file.name.split('.').pop().toLowerCase();
        const assetType = this.getAssetTypeFromExtension(fileExtension);
        const categorySelect = document.getElementById('asset-category-input');
        
        if (assetType === 'image') {
            categorySelect.value = 'storyboard';
        } else if (assetType === 'text') {
            categorySelect.value = 'document';
        }

        // For images, show AI analysis
        if (assetType === 'image' && file.size < 10 * 1024 * 1024) { // Limit to 10MB for analysis
            aiAnalysisSection.style.display = 'block';
            document.getElementById('ai-analysis-content').innerHTML = 'Analyzing image with AI...';
            
            try {
                const analysis = await this.analyzeImageWithAI(file);
                if (analysis) {
                    document.getElementById('ai-analysis-content').innerHTML = analysis.description;
                    this.showSuggestedTags(analysis.tags);
                }
            } catch (error) {
                console.error('AI analysis failed:', error);
                document.getElementById('ai-analysis-content').innerHTML = 'AI analysis unavailable';
            }
        }

        document.getElementById('confirm-asset-upload').disabled = false;
    }

    getAssetTypeFromExtension(extension) {
        const imageTypes = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
        const videoTypes = ['mp4', 'mov', 'avi', 'mkv', 'webm'];
        const audioTypes = ['wav', 'mp3', 'm4a', 'aac', 'ogg'];
        const textTypes = ['txt', 'md', 'pdf'];

        if (imageTypes.includes(extension)) return 'image';
        if (videoTypes.includes(extension)) return 'video';
        if (audioTypes.includes(extension)) return 'audio';
        if (textTypes.includes(extension)) return 'text';
        return 'document';
    }

    async analyzeImageWithAI(file) {
        // This is a mock implementation - in practice you'd send to your backend
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    description: "A dramatic scene with moody lighting and strong composition. The image features cinematic framing with deep shadows and atmospheric elements that would work well for storyboard reference.",
                    tags: ["dramatic lighting", "moody", "cinematic", "shadows", "atmospheric"]
                });
            }, 2000);
        });
    }

    showSuggestedTags(tags) {
        const suggestedTagsContainer = document.getElementById('suggested-tags');
        suggestedTagsContainer.innerHTML = tags.map(tag => 
            `<span class="suggested-tag" onclick="window.kinoGeistApp.addTagToInput('${tag}')">${tag}</span>`
        ).join('');
    }

    addTagToInput(tag) {
        const tagsInput = document.getElementById('asset-tags-input');
        const currentTags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t);
        if (!currentTags.includes(tag)) {
            currentTags.push(tag);
            tagsInput.value = currentTags.join(', ');
        }
    }

    async uploadSelectedAsset() {
        if (!this.selectedFile) return;

        const category = document.getElementById('asset-category-input').value;
        const tags = document.getElementById('asset-tags-input').value;
        
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        formData.append('category', category);
        formData.append('tags', tags);

        try {
            this.showNotification('Uploading asset...', 'info');
            
            const response = await fetch('/api/upload/asset', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                await this.loadProject(); // Refresh project data
                this.renderAssetNexus(); // Re-render assets
                this.showNotification(`Asset "${result.asset.name}" uploaded successfully!`, 'success');
                document.getElementById('asset-upload-modal').classList.add('hidden');
            } else {
                this.showNotification('Error uploading asset: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Asset upload error:', error);
            this.showNotification('Error uploading asset. Please try again.', 'error');
        }
    }

    async useAssetInWriter(assetId) {
        const asset = (this.project.assets || []).find(a => a.id === assetId);
        if (!asset) return;

        // Navigate to Writer's Room
        this.navigateToSection('story-writer');

        // Insert content at cursor or append to end
        const editor = document.getElementById('story-editor');
        if (editor) {
            const htmlContent = asset.content.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
            
            if (this.lastSelection) {
                // Insert at last cursor position
                this.lastSelection.deleteContents();
                const div = document.createElement('div');
                div.innerHTML = `<p>${htmlContent}</p>`;
                this.lastSelection.insertNode(div.firstChild);
            } else {
                // Append to end
                editor.innerHTML += `<p>${htmlContent}</p>`;
            }

            // Update project and save
            this.project.story.treatment = editor.innerHTML;
            await this.saveProject();
            this.showNotification(`Content from "${asset.name}" added to Writer's Room`, 'success');
        }
    }

    async confirmDeleteAsset(assetId) {
        const asset = (this.project.assets || []).find(a => a.id === assetId);
        if (!asset) return;

        const confirmed = await this.showConfirmationDialog(
            'Delete Asset',
            `Are you sure you want to delete "${asset.name}"? This action cannot be undone.`
        );

        if (confirmed) {
            this.project.assets = this.project.assets.filter(a => a.id !== assetId);
            await this.saveProject();
            this.renderAssetNexus();
            this.showNotification('Asset deleted successfully', 'success');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    truncateText(text, length) {
        if (!text) return '';
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    }

    //----------------------------------------------------------------
    // SCREENING ROOM TIMELINE MANAGEMENT
    //----------------------------------------------------------------
    
    renderScreeningRoom() {
        this.renderTimelineFrames();
        this.renderShotLibrary();
        this.updateTimelineInfo();
    }
    
    renderTimelineFrames() {
        const timelineFrames = document.getElementById('timeline-frames');
        if (!timelineFrames) return;
        
        const timeline = this.project.screeningRoom?.timeline || [];
        
        if (timeline.length === 0) {
            timelineFrames.innerHTML = `
                <div class="timeline-empty-state">
                    <p>Timeline is empty. Use "Populate from Shot Lab" to automatically add approved storyboard images, or drag shots from scenes below.</p>
                </div>
            `;
            return;
        }
        
        timelineFrames.innerHTML = timeline.map((frame, index) => `
            <div class="timeline-frame-item" data-frame-index="${index}" data-shot-id="${frame.shotId}" data-scene-id="${frame.sceneId}">
                <div class="timeline-frame-image">
                    ${frame.image ? `<img src="${frame.image}" alt="Frame ${index + 1}" style="width: 120px; height: 80px; object-fit: cover;">` : 'No Image'}
                </div>
                <div class="timeline-frame-info">
                    <div class="timeline-frame-title">${frame.shotType}</div>
                    <div class="timeline-frame-duration">
                        <input type="number" value="${frame.duration}" min="0.5" max="10" step="0.5" class="frame-duration-input" data-frame-index="${index}">s
                    </div>
                </div>
                <div class="timeline-frame-controls">
                    <button class="btn btn--xs" onclick="window.kinoGeistApp.moveFrameUp(${index})" title="Move left">◀</button>
                    <button class="btn btn--xs" onclick="window.kinoGeistApp.moveFrameDown(${index})" title="Move right">▶</button>
                    <button class="btn btn--xs btn--reject" onclick="window.kinoGeistApp.removeFromTimeline(${index})" title="Remove">×</button>
                </div>
            </div>
        `).join('');
        
        // Add event listeners for duration changes
        timelineFrames.querySelectorAll('.frame-duration-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const frameIndex = parseInt(e.target.dataset.frameIndex);
                this.updateFrameDuration(frameIndex, parseFloat(e.target.value));
            });
        });
        
        // Add drag and drop functionality
        this.setupTimelineDragAndDrop();
    }
    
    renderShotLibrary() {
        const shotLibraryContent = document.getElementById('shot-library-content');
        if (!shotLibraryContent) return;
        
        const scenes = this.project.shotLab?.scenes || [];
        
        if (scenes.length === 0) {
            shotLibraryContent.innerHTML = '<p style="color: var(--c-gray); text-align: center;">No scenes available. Create scenes in Shot Lab first.</p>';
            return;
        }
        
        shotLibraryContent.innerHTML = scenes.map(scene => `
            <div class="shot-library-scene">
                <div class="shot-library-scene-title" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'flex' : 'none'">
                    ${scene.title} (${scene.shots.length} shots)
                </div>
                <div class="shot-library-shots" style="display: flex;">
                    ${scene.shots.map(shot => `
                        <div class="shot-library-shot" draggable="true" data-shot-id="${shot.id}" data-scene-id="${scene.id}" data-shot-type="${shot.type}" data-shot-description="${shot.description}" data-shot-image="${shot.image || ''}">
                            <div class="shot-library-shot-type">${shot.type}</div>
                            <div class="shot-library-shot-desc">${shot.description.substring(0, 40)}${shot.description.length > 40 ? '...' : ''}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
        
        // Setup drag and drop for shot library items
        this.setupShotLibraryDragAndDrop();
    }
    
    populateTimelineFromShotLab() {
        const scenes = this.project.shotLab?.scenes || [];
        const defaultDuration = parseFloat(document.getElementById('default-frame-duration')?.value || '3');
        
        // Clear existing timeline
        this.project.screeningRoom.timeline = [];
        
        // Add all shots from all scenes to timeline
        scenes.forEach(scene => {
            scene.shots.forEach(shot => {
                this.project.screeningRoom.timeline.push({
                    shotId: shot.id,
                    sceneId: scene.id,
                    shotType: shot.type,
                    description: shot.description,
                    image: shot.image,
                    duration: defaultDuration
                });
            });
        });
        
        this.saveProject();
        this.renderTimelineFrames();
        this.updateTimelineInfo();
        this.showNotification(`Added ${this.project.screeningRoom.timeline.length} shots to timeline!`, 'success');
    }
    
    clearTimeline() {
        if (!confirm('Are you sure you want to clear the entire timeline? This cannot be undone.')) return;
        
        this.project.screeningRoom.timeline = [];
        this.saveProject();
        this.renderTimelineFrames();
        this.updateTimelineInfo();
        this.showNotification('Timeline cleared', 'info');
    }
    
    addShotToTimeline(shotData) {
        const defaultDuration = parseFloat(document.getElementById('default-frame-duration')?.value || '3');
        
        const frame = {
            shotId: shotData.shotId,
            sceneId: shotData.sceneId,
            shotType: shotData.shotType,
            description: shotData.description,
            image: shotData.image,
            duration: defaultDuration
        };
        
        this.project.screeningRoom.timeline.push(frame);
        this.saveProject();
        this.renderTimelineFrames();
        this.updateTimelineInfo();
        this.showNotification(`Added "${shotData.shotType}" to timeline`, 'success');
    }
    
    removeFromTimeline(frameIndex) {
        if (!confirm('Remove this shot from the timeline?')) return;
        
        this.project.screeningRoom.timeline.splice(frameIndex, 1);
        this.saveProject();
        this.renderTimelineFrames();
        this.updateTimelineInfo();
        this.showNotification('Shot removed from timeline', 'info');
    }
    
    moveFrameUp(frameIndex) {
        if (frameIndex === 0) return;
        
        const timeline = this.project.screeningRoom.timeline;
        [timeline[frameIndex], timeline[frameIndex - 1]] = [timeline[frameIndex - 1], timeline[frameIndex]];
        
        this.saveProject();
        this.renderTimelineFrames();
        this.showNotification('Shot moved', 'info');
    }
    
    moveFrameDown(frameIndex) {
        const timeline = this.project.screeningRoom.timeline;
        if (frameIndex === timeline.length - 1) return;
        
        [timeline[frameIndex], timeline[frameIndex + 1]] = [timeline[frameIndex + 1], timeline[frameIndex]];
        
        this.saveProject();
        this.renderTimelineFrames();
        this.showNotification('Shot moved', 'info');
    }
    
    updateFrameDuration(frameIndex, duration) {
        this.project.screeningRoom.timeline[frameIndex].duration = duration;
        this.saveProject();
        this.updateTimelineInfo();
    }
    
    updateTimelineInfo() {
        const timeline = this.project.screeningRoom.timeline || [];
        const totalFrames = timeline.length;
        const totalDuration = timeline.reduce((sum, frame) => sum + frame.duration, 0);
        
        document.getElementById('total-frames').textContent = totalFrames;
        document.getElementById('total-time').textContent = this.formatTime(totalDuration);
        
        // Update current frame display (for now, just show first frame)
        document.getElementById('current-frame').textContent = totalFrames > 0 ? '1' : '0';
        document.getElementById('current-time').textContent = '00:00';
    }
    
    setupTimelineDragAndDrop() {
        const timelineFrames = document.getElementById('timeline-frames');
        if (!timelineFrames) return;
        
        timelineFrames.addEventListener('dragover', (e) => {
            e.preventDefault();
            timelineFrames.classList.add('drag-over');
        });
        
        timelineFrames.addEventListener('dragleave', (e) => {
            if (!timelineFrames.contains(e.relatedTarget)) {
                timelineFrames.classList.remove('drag-over');
            }
        });
        
        timelineFrames.addEventListener('drop', (e) => {
            e.preventDefault();
            timelineFrames.classList.remove('drag-over');
            
            const shotData = e.dataTransfer.getData('application/json');
            if (shotData) {
                this.addShotToTimeline(JSON.parse(shotData));
            }
        });
    }
    
    setupShotLibraryDragAndDrop() {
        const shotItems = document.querySelectorAll('.shot-library-shot');
        
        shotItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                const shotData = {
                    shotId: item.dataset.shotId,
                    sceneId: item.dataset.sceneId,
                    shotType: item.dataset.shotType,
                    description: item.dataset.shotDescription,
                    image: item.dataset.shotImage
                };
                
                e.dataTransfer.setData('application/json', JSON.stringify(shotData));
                item.style.opacity = '0.5';
            });
            
            item.addEventListener('dragend', () => {
                item.style.opacity = '1';
            });
        });
    }
    
    // Basic timeline playback (simulation)
    startTimelinePlayback() {
        const timeline = this.project.screeningRoom.timeline || [];
        if (timeline.length === 0) {
            this.showNotification('Timeline is empty', 'error');
            return;
        }
        
        const playPauseBtn = document.getElementById('play-pause-btn');
        
        if (this.isPlaying) {
            // Pause
            this.stopTimelinePlayback();
            return;
        }
        
        // Start playback
        this.isPlaying = true;
        this.currentFrameIndex = 0;
        playPauseBtn.textContent = '⏸';
        
        this.playNextFrame();
    }
    
    playNextFrame() {
        if (!this.isPlaying) return;
        
        const timeline = this.project.screeningRoom.timeline || [];
        if (this.currentFrameIndex >= timeline.length) {
            this.stopTimelinePlayback();
            return;
        }
        
        const currentFrame = timeline[this.currentFrameIndex];
        const frameElement = document.querySelector(`[data-frame-index="${this.currentFrameIndex}"]`);
        
        // Highlight current frame
        document.querySelectorAll('.timeline-frame-item').forEach(el => el.classList.remove('active'));
        frameElement?.classList.add('active');
        
        // Update time display
        const elapsedTime = timeline.slice(0, this.currentFrameIndex).reduce((sum, frame) => sum + frame.duration, 0);
        document.getElementById('current-time').textContent = this.formatTime(elapsedTime);
        document.getElementById('current-frame').textContent = (this.currentFrameIndex + 1).toString();
        
        // Schedule next frame
        this.playbackTimeout = setTimeout(() => {
            this.currentFrameIndex++;
            this.playNextFrame();
        }, currentFrame.duration * 1000);
    }
    
    stopTimelinePlayback() {
        this.isPlaying = false;
        this.currentFrameIndex = 0;
        
        if (this.playbackTimeout) {
            clearTimeout(this.playbackTimeout);
            this.playbackTimeout = null;
        }
        
        const playPauseBtn = document.getElementById('play-pause-btn');
        playPauseBtn.textContent = '▶';
        
        // Reset highlighting
        document.querySelectorAll('.timeline-frame-item').forEach(el => el.classList.remove('active'));
        document.getElementById('current-time').textContent = '00:00';
        document.getElementById('current-frame').textContent = '0';
    }
    
    previousFrame() {
        const timeline = this.project.screeningRoom.timeline || [];
        if (timeline.length === 0) return;
        
        this.currentFrameIndex = Math.max(0, (this.currentFrameIndex || 0) - 1);
        this.showFrame(this.currentFrameIndex);
    }
    
    nextFrame() {
        const timeline = this.project.screeningRoom.timeline || [];
        if (timeline.length === 0) return;
        
        this.currentFrameIndex = Math.min(timeline.length - 1, (this.currentFrameIndex || 0) + 1);
        this.showFrame(this.currentFrameIndex);
    }
    
    showFrame(frameIndex) {
        document.querySelectorAll('.timeline-frame-item').forEach(el => el.classList.remove('active'));
        const frameElement = document.querySelector(`[data-frame-index="${frameIndex}"]`);
        frameElement?.classList.add('active');
        
        document.getElementById('current-frame').textContent = (frameIndex + 1).toString();
        
        const timeline = this.project.screeningRoom.timeline || [];
        const elapsedTime = timeline.slice(0, frameIndex).reduce((sum, frame) => sum + frame.duration, 0);
        document.getElementById('current-time').textContent = this.formatTime(elapsedTime);
    }
    
    exportAnimatic() {
        const timeline = this.project.screeningRoom.timeline || [];
        if (timeline.length === 0) {
            this.showNotification('Timeline is empty - nothing to export', 'error');
            return;
        }
        
        // For now, create a simple export object
        const animaticData = {
            project: this.project.title,
            totalFrames: timeline.length,
            totalDuration: timeline.reduce((sum, frame) => sum + frame.duration, 0),
            frames: timeline.map((frame, index) => ({
                frameNumber: index + 1,
                shotType: frame.shotType,
                description: frame.description,
                duration: frame.duration,
                sceneId: frame.sceneId,
                shotId: frame.shotId
            }))
        };
        
        // Download as JSON for now
        const blob = new Blob([JSON.stringify(animaticData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.project.title}_animatic.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Animatic exported successfully!', 'success');
    }
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    //----------------------------------------------------------------
    // ENHANCED CROSS-MODULE LINKING SYSTEM
    //----------------------------------------------------------------
    
    // Universal search across all modules
    performUniversalSearch(searchTerm) {
        if (!searchTerm || searchTerm.length < 2) return [];
        
        const results = [];
        const term = searchTerm.toLowerCase();
        
        // Search Story Bible
        this.project.storyBible.characters.forEach(char => {
            if (char.name.toLowerCase().includes(term) || char.role?.toLowerCase().includes(term) || char.backstory?.toLowerCase().includes(term)) {
                results.push({
                    type: 'character',
                    title: char.name,
                    subtitle: char.role || 'Character',
                    content: char.backstory || char.description || '',
                    module: 'story-bible',
                    action: () => this.navigateToCharacter(char.id)
                });
            }
        });
        
        this.project.storyBible.locations.forEach(loc => {
            if (loc.name.toLowerCase().includes(term) || loc.description?.toLowerCase().includes(term)) {
                results.push({
                    type: 'location',
                    title: loc.name,
                    subtitle: 'Location',
                    content: loc.description || '',
                    module: 'story-bible',
                    action: () => this.navigateToLocation(loc.id)
                });
            }
        });
        
        // Search Shot Lab scenes
        this.project.shotLab.scenes.forEach(scene => {
            if (scene.title.toLowerCase().includes(term) || scene.description?.toLowerCase().includes(term)) {
                results.push({
                    type: 'scene',
                    title: scene.title,
                    subtitle: `Scene (${scene.shots.length} shots)`,
                    content: scene.description || '',
                    module: 'shot-lab',
                    action: () => this.navigateToScene(scene.id)
                });
            }
        });
        
        // Search Assets
        if (this.project.assets) {
            this.project.assets.forEach(asset => {
                if (asset.name.toLowerCase().includes(term) || asset.content?.toLowerCase().includes(term)) {
                    results.push({
                        type: 'asset',
                        title: asset.name,
                        subtitle: `${asset.assetType} Asset`,
                        content: asset.content ? this.truncateText(asset.content, 100) : '',
                        module: 'asset-nexus',
                        action: () => this.navigateToAsset(asset.id)
                    });
                }
            });
        }
        
        // Search Visual DNA
        this.project.visualDNA.characterKits.forEach(kit => {
            if (kit.name.toLowerCase().includes(term) || kit.promptLexicon?.toLowerCase().includes(term)) {
                results.push({
                    type: 'dna-kit',
                    title: `${kit.name} DNA Kit`,
                    subtitle: 'Character Visual DNA',
                    content: kit.promptLexicon || '',
                    module: 'visual-dna',
                    action: () => this.navigateToCharacterDNA(kit.charId)
                });
            }
        });
        
        this.project.visualDNA.locationKits.forEach(kit => {
            if (kit.name.toLowerCase().includes(term) || kit.promptLexicon?.toLowerCase().includes(term)) {
                results.push({
                    type: 'dna-kit',
                    title: `${kit.name} DNA Kit`,
                    subtitle: 'Location Visual DNA',
                    content: kit.promptLexicon || '',
                    module: 'visual-dna',
                    action: () => this.navigateToLocationDNA(kit.locId)
                });
            }
        });
        
        return results.slice(0, 20); // Limit to 20 results
    }
    
    // Navigation helpers for search results
    navigateToCharacter(charId) {
        this.navigateToSection('story-bible');
        // Switch to characters tab
        document.querySelector('[data-tab="characters"]')?.click();
        // Highlight the character card
        setTimeout(() => {
            const charCard = document.querySelector(`[data-character-id="${charId}"]`);
            if (charCard) {
                charCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                charCard.classList.add('highlight-item');
                setTimeout(() => charCard.classList.remove('highlight-item'), 2000);
            }
        }, 100);
    }
    
    navigateToLocation(locId) {
        this.navigateToSection('story-bible');
        document.querySelector('[data-tab="locations"]')?.click();
        setTimeout(() => {
            const locCard = document.querySelector(`[data-location-id="${locId}"]`);
            if (locCard) {
                locCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                locCard.classList.add('highlight-item');
                setTimeout(() => locCard.classList.remove('highlight-item'), 2000);
            }
        }, 100);
    }
    
    navigateToScene(sceneId) {
        this.navigateToSection('shot-lab');
        setTimeout(() => {
            const sceneItem = document.querySelector(`[data-scene-id="${sceneId}"]`);
            if (sceneItem) {
                sceneItem.click(); // Select the scene
                sceneItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                sceneItem.classList.add('highlight-item');
                setTimeout(() => sceneItem.classList.remove('highlight-item'), 2000);
            }
        }, 100);
    }
    
    navigateToAsset(assetId) {
        this.navigateToSection('asset-nexus');
        setTimeout(() => {
            const assetCard = document.querySelector(`[data-asset-id="${assetId}"]`);
            if (assetCard) {
                assetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                assetCard.classList.add('highlight-item');
                setTimeout(() => assetCard.classList.remove('highlight-item'), 2000);
            }
        }, 100);
    }
    
    navigateToCharacterDNA(charId) {
        this.navigateToSection('visual-dna');
        setTimeout(() => {
            const dnaKit = document.querySelector(`[data-kit-type="character"][data-kit-id="${charId}"]`);
            if (dnaKit) {
                dnaKit.scrollIntoView({ behavior: 'smooth', block: 'center' });
                dnaKit.classList.add('highlight-item');
                setTimeout(() => dnaKit.classList.remove('highlight-item'), 2000);
            }
        }, 100);
    }
    
    navigateToLocationDNA(locId) {
        this.navigateToSection('visual-dna');
        setTimeout(() => {
            const dnaKit = document.querySelector(`[data-kit-type="location"][data-kit-id="${locId}"]`);
            if (dnaKit) {
                dnaKit.scrollIntoView({ behavior: 'smooth', block: 'center' });
                dnaKit.classList.add('highlight-item');
                setTimeout(() => dnaKit.classList.remove('highlight-item'), 2000);
            }
        }, 100);
    }
    
    // Auto-detect and link character/location mentions in text
    autoLinkContent(text) {
        if (!text) return text;
        
        let linkedText = text;
        
        // Link character names
        this.project.storyBible.characters.forEach(char => {
            const regex = new RegExp(`\\b${char.name}\\b`, 'gi');
            linkedText = linkedText.replace(regex, `<span class="auto-link character-link" data-character-id="${char.id}" onclick="window.kinoGeistApp.navigateToCharacter(${char.id})">${char.name}</span>`);
        });
        
        // Link location names
        this.project.storyBible.locations.forEach(loc => {
            const regex = new RegExp(`\\b${loc.name}\\b`, 'gi');
            linkedText = linkedText.replace(regex, `<span class="auto-link location-link" data-location-id="${loc.id}" onclick="window.kinoGeistApp.navigateToLocation(${loc.id})">${loc.name}</span>`);
        });
        
        return linkedText;
    }
    
    // Get context-aware suggestions based on current scene
    getContextSuggestions(sceneId) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return { characters: [], locations: [], assets: [], keywords: [] };
        
        const suggestions = {
            characters: [],
            locations: [],
            assets: [],
            keywords: []
        };
        
        const sceneText = `${scene.title} ${scene.description}`.toLowerCase();
        
        // Suggest relevant characters
        this.project.storyBible.characters.forEach(char => {
            if (sceneText.includes(char.name.toLowerCase())) {
                suggestions.characters.push(char);
            }
        });
        
        // Suggest relevant locations
        this.project.storyBible.locations.forEach(loc => {
            if (sceneText.includes(loc.name.toLowerCase())) {
                suggestions.locations.push(loc);
            }
        });
        
        // Suggest relevant assets
        if (this.project.assets) {
            this.project.assets.forEach(asset => {
                if (asset.tags && asset.tags.some(tag => sceneText.includes(tag.toLowerCase()))) {
                    suggestions.assets.push(asset);
                }
            });
        }
        
        // Gather relevant Visual DNA keywords
        suggestions.characters.forEach(char => {
            const kit = this.project.visualDNA.characterKits.find(k => k.charId === char.id);
            if (kit && kit.promptLexicon) {
                suggestions.keywords.push(...kit.promptLexicon.split(',').map(k => k.trim()));
            }
        });
        
        suggestions.locations.forEach(loc => {
            const kit = this.project.visualDNA.locationKits.find(k => k.locId === loc.id);
            if (kit && kit.promptLexicon) {
                suggestions.keywords.push(...kit.promptLexicon.split(',').map(k => k.trim()));
            }
        });
        
        return suggestions;
    }
    
    // Enhanced scene selection with context display
    selectSceneWithContext(sceneId) {
        // Call the original scene selection
        this.selectScene(sceneId);
        
        // Add context suggestions
        const suggestions = this.getContextSuggestions(sceneId);
        this.displayContextSuggestions(suggestions);
    }
    
    displayContextSuggestions(suggestions) {
        const contextPanel = document.getElementById('scene-context-suggestions');
        if (!contextPanel) return;
        
        let html = '';
        
        if (suggestions.characters.length > 0) {
            html += `
                <div class="context-section">
                    <h5>Related Characters</h5>
                    <div class="context-items">
                        ${suggestions.characters.map(char => `
                            <span class="context-item character-item" onclick="window.kinoGeistApp.navigateToCharacter(${char.id})" title="Go to ${char.name}'s profile">
                                ${char.name}
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        if (suggestions.locations.length > 0) {
            html += `
                <div class="context-section">
                    <h5>Related Locations</h5>
                    <div class="context-items">
                        ${suggestions.locations.map(loc => `
                            <span class="context-item location-item" onclick="window.kinoGeistApp.navigateToLocation(${loc.id})" title="Go to ${loc.name}'s details">
                                ${loc.name}
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        if (suggestions.keywords.length > 0) {
            const uniqueKeywords = [...new Set(suggestions.keywords)].slice(0, 10);
            html += `
                <div class="context-section">
                    <h5>Relevant Keywords</h5>
                    <div class="context-items">
                        ${uniqueKeywords.map(keyword => `
                            <span class="context-item keyword-item" onclick="window.kinoGeistApp.addKeywordToCurrentPrompt('${keyword}')" title="Add to prompt">
                                ${keyword}
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        contextPanel.innerHTML = html || '<p class="context-empty">No related items found for this scene.</p>';
    }
    
    addKeywordToCurrentPrompt(keyword) {
        // If Prompt Workbench is open, add to it
        const workbenchTextarea = document.getElementById('prompt-workbench-textarea');
        if (workbenchTextarea && !document.getElementById('prompt-workbench-modal').classList.contains('hidden')) {
            this.addKeywordToPrompt(keyword);
            return;
        }
        
        // Otherwise, show a temporary notification
        this.showNotification(`"${keyword}" ready to add to prompt. Open Prompt Workbench on any shot.`, 'info');
    }
    
    // Enhanced Asset Nexus integration - show context-aware asset suggestions
    showContextAwareAssets(sceneId) {
        const suggestions = this.getContextSuggestions(sceneId);
        const assetSuggestions = document.getElementById('context-asset-suggestions');
        
        if (!assetSuggestions || !suggestions.assets.length) return;
        
        assetSuggestions.innerHTML = `
            <h5>Suggested Assets for This Scene</h5>
            <div class="context-assets">
                ${suggestions.assets.slice(0, 6).map(asset => `
                    <div class="context-asset-item" onclick="window.kinoGeistApp.navigateToAsset('${asset.id}')">
                        <div class="context-asset-name">${asset.name}</div>
                        <div class="context-asset-type">${asset.assetType}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // Smart prompt suggestions based on selected scene
    getSmartPromptSuggestions(sceneId) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return [];
        
        const suggestions = this.getContextSuggestions(sceneId);
        const promptSuggestions = [];
        
        // Base scene description
        promptSuggestions.push(`${scene.description}`);
        
        // Add character-specific suggestions
        if (suggestions.characters.length > 0) {
            const charNames = suggestions.characters.map(c => c.name).join(', ');
            promptSuggestions.push(`featuring ${charNames}`);
        }
        
        // Add location-specific suggestions
        if (suggestions.locations.length > 0) {
            const locNames = suggestions.locations.map(l => l.name).join(', ');
            promptSuggestions.push(`set in ${locNames}`);
        }
        
        // Add style keywords
        if (suggestions.keywords.length > 0) {
            const styleKeywords = suggestions.keywords.slice(0, 5).join(', ');
            promptSuggestions.push(`${styleKeywords}`);
        }
        
        // Add global style if available
        const globalStyle = this.project.visualDNA?.globalStyle;
        if (globalStyle) {
            const globalElements = [
                globalStyle.palette,
                globalStyle.lighting,
                globalStyle.influences
            ].filter(Boolean);
            
            if (globalElements.length > 0) {
                promptSuggestions.push(globalElements.join(', '));
            }
        }
        
        return promptSuggestions.filter(Boolean);
    }
    
    // Setup universal search functionality
    setupUniversalSearch() {
        const searchInput = document.getElementById('universal-search-input');
        const searchResults = document.getElementById('universal-search-results');
        
        if (!searchInput || !searchResults) return;
        
        let searchTimeout;
        
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (query.length < 2) {
                    searchResults.classList.add('hidden');
                    return;
                }
                
                const results = this.performUniversalSearch(query);
                this.displaySearchResults(results);
            }, 300);
        });
        
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2) {
                const results = this.performUniversalSearch(searchInput.value.trim());
                this.displaySearchResults(results);
            }
        });
        
        // Hide search results when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.add('hidden');
            }
        });
        
        // Handle keyboard navigation
        searchInput.addEventListener('keydown', (e) => {
            const activeResult = searchResults.querySelector('.search-result-item.active');
            const allResults = searchResults.querySelectorAll('.search-result-item');
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (activeResult) {
                    activeResult.classList.remove('active');
                    const next = activeResult.nextElementSibling;
                    if (next) {
                        next.classList.add('active');
                    } else {
                        allResults[0]?.classList.add('active');
                    }
                } else {
                    allResults[0]?.classList.add('active');
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (activeResult) {
                    activeResult.classList.remove('active');
                    const prev = activeResult.previousElementSibling;
                    if (prev) {
                        prev.classList.add('active');
                    } else {
                        allResults[allResults.length - 1]?.classList.add('active');
                    }
                } else {
                    allResults[allResults.length - 1]?.classList.add('active');
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activeResult) {
                    activeResult.click();
                }
            } else if (e.key === 'Escape') {
                searchResults.classList.add('hidden');
                searchInput.blur();
            }
        });
    }
    
    displaySearchResults(results) {
        const searchResults = document.getElementById('universal-search-results');
        if (!searchResults) return;
        
        if (results.length === 0) {
            searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
            searchResults.classList.remove('hidden');
            return;
        }
        
        searchResults.innerHTML = results.map(result => `
            <div class="search-result-item" data-result-type="${result.type}">
                <div class="search-result-title">${result.title}</div>
                <div class="search-result-subtitle">${result.subtitle} • ${result.module.replace('-', ' ')}</div>
                ${result.content ? `<div class="search-result-content">${result.content}</div>` : ''}
            </div>
        `).join('');
        
        // Add click handlers
        searchResults.querySelectorAll('.search-result-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                results[index].action();
                searchResults.classList.add('hidden');
                document.getElementById('universal-search-input').value = '';
            });
        });
        
        searchResults.classList.remove('hidden');
    }

    //----------------------------------------------------------------
    // EVENT HANDLING
    //----------------------------------------------------------------
    setupNavigation() {
        const navButtons = document.querySelectorAll('.nav-btn');
        const dashboardCards = document.querySelectorAll('.dashboard-card');
        const logo = document.querySelector('.logo');

        const allNavElements = [...navButtons, ...dashboardCards, logo];

        allNavElements.forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                const section = el.dataset.section || 'dashboard';
                this.navigateToSection(section);
            });
        });
    }

    navigateToSection(sectionName) {
        document.querySelectorAll('.section.active').forEach(s => s.classList.remove('active'));
        const targetSection = document.getElementById(sectionName);
        if (targetSection) {
            targetSection.classList.add('active');
        }
        document.querySelectorAll('.nav-btn.active').forEach(b => b.classList.remove('active'));
        document.querySelector(`.nav-btn[data-section="${sectionName}"]`)?.classList.add('active');
    }

    setupEventListeners() {
        this.lastSelection = null;
        const editor = document.getElementById('story-editor');
        editor?.addEventListener('focusout', () => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                this.lastSelection = selection.getRangeAt(0);
            }
        });

        // Save Button
        document.getElementById('save-story')?.addEventListener('click', () => this.saveProject());

        // Story Bible Tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;
                btn.parentElement.querySelector('.active').classList.remove('active');
                btn.classList.add('active');
                btn.closest('.story-bible').querySelector('.tab-content.active').classList.remove('active');
                document.getElementById(`${tabName}-tab`).classList.add('active');
            });
        });

        // Shot Lab Scene Selection
        document.getElementById('scenes-list-content').addEventListener('click', (e) => {
            const sceneItem = e.target.closest('.scene-item');
            if (sceneItem) {
                document.querySelectorAll('.scene-item.active').forEach(i => i.classList.remove('active'));
                sceneItem.classList.add('active');
                this.selectScene(sceneItem.dataset.sceneId);
            }
        });

        // Shot Lab Action Buttons
        document.getElementById('ai-breakdown-btn')?.addEventListener('click', () => this.performAIBreakdown());
        document.getElementById('add-scene-btn')?.addEventListener('click', () => this.openSceneEditor());
        document.getElementById('add-shot-btn')?.addEventListener('click', () => this.addManualShot());
        document.getElementById('send-to-screening-room')?.addEventListener('click', () => this.sendCurrentSceneToScreeningRoom());

        document.getElementById('upload-script')?.addEventListener('click', () => document.getElementById('script-upload-input').click());
        document.getElementById('script-upload-input')?.addEventListener('change', (e) => this.handleScriptUpload(e));

        // Asset Nexus Event Listeners
        document.getElementById('upload-visual-asset-btn')?.addEventListener('click', () => this.openAssetUploadModal('visual'));
        document.getElementById('upload-text-asset-btn')?.addEventListener('click', () => this.openAssetUploadModal('text'));
        document.getElementById('asset-search')?.addEventListener('input', (e) => this.filterAssets(e.target.value));
        document.getElementById('asset-type-filter')?.addEventListener('change', (e) => this.filterAssetsByType(e.target.value));
        document.getElementById('asset-status-filter')?.addEventListener('change', (e) => this.filterAssetsByStatus(e.target.value));

        // Mock AI/Action buttons
        document.getElementById('ask-ai')?.addEventListener('click', () => this.askAI());
        document.getElementById('convert-screenplay')?.addEventListener('click', () => this.convertToScreenplay());
        document.getElementById('auto-populate')?.addEventListener('click', () => this.analyzeAndExtract());
        
        // Visual DNA save button
        document.getElementById('save-global-style')?.addEventListener('click', () => this.saveGlobalStyle());

        // Screening Room Event Listeners
        document.getElementById('populate-timeline-btn')?.addEventListener('click', () => this.populateTimelineFromShotLab());
        document.getElementById('clear-timeline-btn')?.addEventListener('click', () => this.clearTimeline());
        document.getElementById('export-animatic-btn')?.addEventListener('click', () => this.exportAnimatic());
        document.getElementById('play-pause-btn')?.addEventListener('click', () => this.startTimelinePlayback());
        document.getElementById('stop-btn')?.addEventListener('click', () => this.stopTimelinePlayback());
        document.getElementById('prev-frame-btn')?.addEventListener('click', () => this.previousFrame());
        document.getElementById('next-frame-btn')?.addEventListener('click', () => this.nextFrame());

        // Universal Search Event Listeners
        this.setupUniversalSearch();

        // Refine AI event listeners
        document.addEventListener('selectionchange', () => this.handleTextSelection());
        document.querySelectorAll('.refine-btn').forEach(btn => {
            btn.addEventListener('click', () => this.refineAI(btn.dataset.refineType));
        });
        document.getElementById('refine-ai')?.addEventListener('click', () => this.refineAI('custom'));
        
        // Setup Prompt Workbench
        this.setupPromptWorkbench();
    }

    //----------------------------------------------------------------
    // MOCK ACTIONS & UTILITIES
    //----------------------------------------------------------------
    async askAI() {
        const promptInput = document.getElementById('ai-prompt');
        const prompt = promptInput.value.trim();
        if (!prompt) {
            this.showNotification('Please enter a prompt.', 'error');
            return;
        }

        this.showNotification("Querying Gemini Collaborator...", "info");
        const aiResponseContainer = document.getElementById('ai-response');
        if (aiResponseContainer) {
            aiResponseContainer.innerHTML = `<div class="ai-suggestion"><p>Generating suggestions...</p></div>`;
        }

        // Get current text from the editor
        const editor = document.getElementById('story-editor');
        const currentText = editor ? editor.innerText || editor.textContent : '';

        // Prepare the context
        const context = {
            logline: this.project.logline,
            characters: this.project.storyBible.characters.map(c => ({ name: c.name, role: c.role, backstory: c.backstory }))
        };

        try {
            const response = await fetch('/api/gemini/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt, context, currentText }), // Send prompt, context, and current text
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const content = data.candidates[0].content.parts[0].text;

            if (aiResponseContainer) {
                aiResponseContainer.innerHTML = `
                    <div class="ai-response-content">
                        ${this.formatAIResponse(content)}
                    </div>
                    <div class="ai-response-actions">
                        <button class="btn btn--sm btn--outline" onclick="navigator.clipboard.writeText('${content.replace(/'/g, "\\'")}')">Copy</button>
                        <button class="btn btn--sm btn--insert add-to-story-btn">Insert at Cursor</button>
                        <button class="btn btn--sm btn--primary append-to-story-btn">Append to End</button>
                    </div>
                `;
                
                // Add event listeners for the action buttons
                aiResponseContainer.querySelector('.add-to-story-btn').addEventListener('click', () => this.insertAITextAtCursor(content));
                aiResponseContainer.querySelector('.append-to-story-btn').addEventListener('click', () => this.appendAITextToStory(content));
            }
            promptInput.value = ''; // Clear the prompt input
        } catch (error) {
            console.error('Error with Gemini API:', error);
            this.showNotification('Failed to get response from Gemini.', 'error');
            if (aiResponseContainer) {
                aiResponseContainer.innerHTML = `<div class="ai-suggestion"><p>Error: Could not connect to the AI. Please check the server and your API key.</p></div>`;
            }
        }
    }

    async convertToScreenplay() {
        const editor = document.getElementById('story-editor');
        const prose = editor.innerText; // Use innerText to get the raw text content

        if (!prose.trim()) {
            this.showNotification('There is no story to format.', 'error');
            return;
        }

        this.showNotification('Gemini is formatting your script... ', 'info');

        try {
            const response = await fetch('/api/gemini/format-screenplay', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prose }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const formattedScreenplay = data.candidates[0].content.parts[0].text;

            // Update the editor with the formatted content
            editor.innerHTML = this.formatScreenplayHtml(formattedScreenplay);
            this.project.story.screenplay = formattedScreenplay;
            this.saveProject(); // Save the newly formatted screenplay

            this.showNotification('Screenplay formatting complete!', 'success');
        } catch (error) {
            console.error('Error formatting screenplay:', error);
            this.showNotification('Error formatting screenplay.', 'error');
        }
    }

    formatScreenplayHtml(screenplayText) {
        let html = '';
        const lines = screenplayText.split(/\r?\n/);

        lines.forEach(line => {
            line = line.trim();
            if (line.length === 0) {
                html += '<br>'; // Preserve empty lines as breaks
            } else if (line.match(/^(INT\.|EXT\.)/)) {
                html += `<p class="scene-heading">${line}</p>`;
            } else if (line.match(/^[A-Z\s]+$/) && line.length < 30) { // Heuristic for character names
                html += `<p class="character-name">${line}</p>`;
            } else if (line.startsWith('(') && line.endsWith(')')) {
                html += `<p class="parenthetical">${line}</p>`;
            } else if (line.match(/^[A-Z][a-z]+\s[A-Z][a-z]+/)) { // Heuristic for dialogue
                html += `<p class="dialogue">${line}</p>`;
            } else {
                html += `<p class="action-line">${line}</p>`;
            }
        });
        return html;
    }

    async analyzeAndExtract() {
        const scriptContent = this.project.story.screenplay || this.project.story.treatment;

        if (!scriptContent.trim()) {
            this.showNotification('There is no script to analyze.', 'error');
            return;
        }

        // Show confirmation dialog
        this.showConfirmation(
            'Auto-Populate Story Bible',
            'This will analyze your script and add new characters, locations, and themes to your Story Bible. This will NOT overwrite existing items, but will add new ones. Do you want to continue?',
            () => {
                console.log('Attempting to analyze and extract with script content:', scriptContent);
                this.performAnalyzeAndExtract(scriptContent);
            }
        );
    }

    async performAnalyzeAndExtract(scriptContent) {
        this.showNotification('Gemini is analyzing your script... ', 'info');

        try {
            const response = await fetch('/api/gemini/analyze-script', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script: scriptContent }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const extractedData = JSON.parse(data.candidates[0].content.parts[0].text);

            // Merge the extracted data with the existing story bible
            this.mergeStoryBible(extractedData);

            this.showNotification('Story Bible updated with extracted entities!', 'success');
        } catch (error) {
            console.error('Error analyzing script:', error);
            this.showNotification('Error analyzing script.', 'error');
        }
    }

    handleTextSelection() {
        const selection = window.getSelection();
        const brainstormPanel = document.getElementById('ai-brainstorm-panel');
        const refinePanel = document.getElementById('ai-refine-panel');

        if (selection.toString().trim().length > 0) {
            brainstormPanel.classList.add('hidden');
            refinePanel.classList.remove('hidden');
        } else {
            brainstormPanel.classList.remove('hidden');
            refinePanel.classList.add('hidden');
        }
    }

    async refineAI(refineType) {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();

        if (!selectedText) {
            this.showNotification('Please select text to refine.', 'error');
            return;
        }

        let prompt = '';
        switch (refineType) {
            case 'improve':
                prompt = `Improve the following text: "${selectedText}"`;
                break;
            case 'visual':
                prompt = `Make the following text more visual: "${selectedText}"`;
                break;
            case 'dialogue':
                prompt = `Punch up the following dialogue: "${selectedText}"`;
                break;
            case 'custom':
                const customPrompt = document.getElementById('refine-prompt').value.trim();
                if (!customPrompt) {
                    this.showNotification('Please enter a custom refinement prompt.', 'error');
                    return;
                }
                prompt = `${customPrompt}: "${selectedText}"`;
                break;
        }

        this.showNotification('Gemini is refining your text...', 'info');
        const refineResponseContainer = document.getElementById('refine-response');
        if (refineResponseContainer) {
            refineResponseContainer.innerHTML = `<div class="ai-suggestion"><p>Generating refinement...</p></div>`;
        }

        try {
            const response = await fetch('/api/gemini/refine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const refinedText = data.candidates[0].content.parts[0].text;

            if (refineResponseContainer) {
                refineResponseContainer.innerHTML = `<div class="ai-suggestion"><p>${refinedText}</p><button class="btn btn--sm btn--primary replace-text-btn">Replace</button></div>`;
                refineResponseContainer.querySelector('.replace-text-btn').addEventListener('click', () => this.replaceSelectedText(refinedText));
            }
        } catch (error) {
            console.error('Error refining text:', error);
            this.showNotification('Error refining text.', 'error');
        }
    }

    replaceSelectedText(newText) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            range.insertNode(document.createTextNode(newText));
        }
        this.saveProject();
    }

    formatAIResponse(text) {
        // Basic formatting: convert line breaks to HTML
        return text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    }

    insertAITextAtCursor(text) {
        const editor = document.getElementById('story-editor');
        if (!editor) return;

        editor.focus();
        
        if (this.lastSelection) {
            // Restore the last selection
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(this.lastSelection);
            
            // Insert the content
            const formattedText = text.replace(/\n/g, '<br>');
            document.execCommand('insertHTML', false, ` ${formattedText} `);
        } else {
            // No selection, insert at end
            this.appendAITextToStory(text);
        }

        this.project.story.treatment = editor.innerHTML;
        this.saveProject();
        this.showNotification('AI content inserted successfully!', 'success');
    }

    appendAITextToStory(text) {
        const editor = document.getElementById('story-editor');
        if (!editor) return;

        const formattedText = text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        editor.innerHTML += `<p>${formattedText}</p>`;
        
        this.project.story.treatment = editor.innerHTML;
        this.saveProject();
        this.showNotification('AI content appended successfully!', 'success');
        
        // Scroll to bottom to show new content
        editor.scrollTop = editor.scrollHeight;
    }

    async handleScriptUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Check file type
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!['txt', 'md', 'pdf'].includes(fileExtension)) {
            this.showNotification('Please upload a .txt, .md, or .pdf file', 'error');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/upload/script', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                const editor = document.getElementById('story-editor');
                if (editor) {
                    // Convert plain text to HTML for display
                    const htmlContent = result.content.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
                    editor.innerHTML = `<p>${htmlContent}</p>`;
                    
                    this.project.story.treatment = editor.innerHTML;
                    await this.saveProject();
                    this.showNotification(`Script "${result.filename}" uploaded successfully!`, 'success');
                }
            } else {
                this.showNotification('Error uploading script: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Error uploading script. Please try again.', 'error');
        }
    }

    async handleAssetUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Check file type
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!['txt', 'md', 'pdf'].includes(fileExtension)) {
            this.showNotification('Please upload a .txt, .md, or .pdf file', 'error');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);
            
            // You could add category selection here
            const category = prompt('Enter category for this asset (e.g., script, note, reference):', 'document');
            if (category) {
                formData.append('category', category);
            }

            const tags = prompt('Enter tags (comma-separated, optional):', '');
            if (tags) {
                formData.append('tags', tags);
            }

            const response = await fetch('/api/upload/asset', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                await this.loadProject(); // Refresh project data
                this.renderAssetNexus(); // Re-render assets
                this.showNotification(`Asset "${result.asset.name}" uploaded successfully!`, 'success');
            } else {
                this.showNotification('Error uploading asset: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Asset upload error:', error);
            this.showNotification('Error uploading asset. Please try again.', 'error');
        }
    }

    filterAssets(searchTerm) {
        const assets = this.project.assets || [];
        const filteredAssets = assets.filter(asset => 
            asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (asset.tags && asset.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase())))
        );
        this.renderAssetGrid(filteredAssets);
    }

    filterAssetsByType(type) {
        const assets = this.project.assets || [];
        let filteredAssets = assets;
        
        if (type !== 'all') {
            filteredAssets = assets.filter(asset => asset.category === type);
        }
        
        this.renderAssetGrid(filteredAssets);
    }

    mergeStoryBible(extractedData) {
        if (extractedData.characters) {
            extractedData.characters.forEach(newChar => {
                if (!this.project.storyBible.characters.some(existing => existing.name.toLowerCase() === newChar.name.toLowerCase())) {
                    const newId = this.project.storyBible.characters.length + 1;
                    this.project.storyBible.characters.push({ id: newId, ...newChar });
                    // Create a corresponding DNA Kit
                    this.project.visualDNA.characterKits.push({ charId: newId, name: newChar.name, anchorImage: null, promptLexicon: '' });
                }
            });
        }
        if (extractedData.locations) {
            extractedData.locations.forEach(newLoc => {
                if (!this.project.storyBible.locations.some(existing => existing.name.toLowerCase() === newLoc.name.toLowerCase())) {
                    const newId = this.project.storyBible.locations.length + 1;
                    this.project.storyBible.locations.push({ id: newId, ...newLoc });
                    // Create a corresponding DNA Kit
                    this.project.visualDNA.locationKits.push({ locId: newId, name: newLoc.name, anchorImage: null, promptLexicon: '' });
                }
            });
        }
        this.renderStoryBible();
        this.renderVisualDNA(); // Re-render the Visual DNA section to show the new kits
        this.saveProject();
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 100);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }
    
    //----------------------------------------------------------------
    // CONFIRMATION SYSTEM
    //----------------------------------------------------------------
    
    showConfirmation(title, message, onConfirm) {
        const modal = document.getElementById('confirmation-modal');
        const titleElement = document.getElementById('confirmation-title');
        const messageElement = document.getElementById('confirmation-message');
        const confirmBtn = document.getElementById('confirmation-confirm');
        const cancelBtn = document.getElementById('confirmation-cancel');

        titleElement.textContent = title;
        messageElement.textContent = message;

        // Remove existing event listeners
        const newConfirmBtn = confirmBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

        // Add new event listeners
        newConfirmBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
            onConfirm();
        });

        newCancelBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });

        modal.classList.remove('hidden');
    }
    
    //----------------------------------------------------------------
    // DELETE FUNCTIONALITY
    //----------------------------------------------------------------
    
    confirmDeleteCharacter(characterId) {
        const character = this.project.storyBible.characters.find(c => c.id === characterId);
        if (!character) return;
        
        this.showConfirmation(
            'Delete Character',
            `Are you sure you want to delete "${character.name}"? This will also remove their Visual DNA kit and cannot be undone.`,
            () => this.deleteCharacter(characterId)
        );
    }
    
    deleteCharacter(characterId) {
        // Remove from story bible
        this.project.storyBible.characters = this.project.storyBible.characters.filter(c => c.id !== characterId);
        
        // Remove corresponding Visual DNA kit
        this.project.visualDNA.characterKits = this.project.visualDNA.characterKits.filter(k => k.charId !== characterId);
        
        this.saveProject();
        this.renderStoryBible();
        this.renderVisualDNA();
        this.showNotification('Character deleted successfully', 'info');
    }
    
    confirmDeleteLocation(locationId) {
        const location = this.project.storyBible.locations.find(l => l.id === locationId);
        if (!location) return;
        
        this.showConfirmation(
            'Delete Location',
            `Are you sure you want to delete "${location.name}"? This will also remove its Visual DNA kit and cannot be undone.`,
            () => this.deleteLocation(locationId)
        );
    }
    
    deleteLocation(locationId) {
        // Remove from story bible
        this.project.storyBible.locations = this.project.storyBible.locations.filter(l => l.id !== locationId);
        
        // Remove corresponding Visual DNA kit
        this.project.visualDNA.locationKits = this.project.visualDNA.locationKits.filter(k => k.locId !== locationId);
        
        this.saveProject();
        this.renderStoryBible();
        this.renderVisualDNA();
        this.showNotification('Location deleted successfully', 'info');
    }
    
    confirmDeleteProp(propId) {
        const prop = this.project.storyBible.props.find(p => p.id === propId);
        if (!prop) return;
        
        this.showConfirmation(
            'Delete Prop',
            `Are you sure you want to delete "${prop.name}"? This cannot be undone.`,
            () => this.deleteProp(propId)
        );
    }
    
    deleteProp(propId) {
        this.project.storyBible.props = this.project.storyBible.props.filter(p => p.id !== propId);
        this.saveProject();
        this.renderStoryBible();
        this.showNotification('Prop deleted successfully', 'info');
    }
    
    confirmDeleteTheme(themeId) {
        const theme = this.project.storyBible.themes.find(t => t.id === themeId);
        if (!theme) return;
        
        this.showConfirmation(
            'Delete Theme',
            `Are you sure you want to delete "${theme.title}"? This cannot be undone.`,
            () => this.deleteTheme(themeId)
        );
    }
    
    deleteTheme(themeId) {
        this.project.storyBible.themes = this.project.storyBible.themes.filter(t => t.id !== themeId);
        this.saveProject();
        this.renderStoryBible();
        this.showNotification('Theme deleted successfully', 'info');
    }
    
    confirmDeleteScene(sceneId) {
        const scene = this.project.shotLab.scenes.find(s => s.id === sceneId);
        if (!scene) return;
        
        this.showConfirmation(
            'Delete Scene',
            `Are you sure you want to delete "${scene.title}"? This will also delete all shots in this scene and cannot be undone.`,
            () => this.deleteScene(sceneId)
        );
    }
    
    deleteScene(sceneId) {
        this.project.shotLab.scenes = this.project.shotLab.scenes.filter(s => s.id !== sceneId);
        this.saveProject();
        this.renderShotLab();
        this.showNotification('Scene deleted successfully', 'info');
    }
    
    //----------------------------------------------------------------
    // SHOT LAB MANAGEMENT
    //----------------------------------------------------------------
    
    async performAIBreakdown() {
        if (!this.currentSelectedScene) {
            this.showNotification('Please select a scene first', 'error');
            return;
        }

        const scene = this.project.shotLab.scenes.find(s => s.id == this.currentSelectedScene);
        if (!scene) {
            this.showNotification('Scene not found', 'error');
            return;
        }

        this.showNotification('Gemini is analyzing the scene...', 'info');

        try {
            const response = await fetch('/api/gemini/suggest-shots', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    sceneText: scene.description, 
                    sceneTitle: scene.title 
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const suggestions = JSON.parse(data.candidates[0].content.parts[0].text);

            this.showShotSuggestions(suggestions);
        } catch (error) {
            console.error('Error getting shot suggestions:', error);
            this.showNotification('Error getting AI suggestions. Please try again.', 'error');
        }
    }

    showShotSuggestions(suggestions) {
        const modal = document.getElementById('shot-suggestions-modal');
        const suggestionsContainer = document.getElementById('suggestions-list-content');

        if (suggestionsContainer) {
            suggestionsContainer.innerHTML = suggestions.map((suggestion, index) => `
                <div class="suggestion-item">
                    <input type="checkbox" class="suggestion-checkbox" id="suggestion-${index}" checked>
                    <h4>${suggestion.type}</h4>
                    <div class="description">${suggestion.description}</div>
                    <div class="purpose">Purpose: ${suggestion.purpose}</div>
                    <div class="duration">Est. Duration: ${suggestion.duration}s</div>
                </div>
            `).join('');
        }

        modal?.classList.remove('hidden');
        this.setupShotSuggestionsEventListeners();
    }

    setupShotSuggestionsEventListeners() {
        const closeBtn = document.getElementById('suggestions-modal-close-btn');
        const rejectBtn = document.getElementById('reject-all-shots');
        const acceptBtn = document.getElementById('accept-selected-shots');
        const modal = document.getElementById('shot-suggestions-modal');

        closeBtn?.addEventListener('click', () => this.closeShotSuggestions());
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) this.closeShotSuggestions();
        });

        rejectBtn?.addEventListener('click', () => this.closeShotSuggestions());
        acceptBtn?.addEventListener('click', () => this.acceptSelectedShots());
    }

    acceptSelectedShots() {
        const checkboxes = document.querySelectorAll('.suggestion-checkbox:checked');
        const suggestions = [];

        checkboxes.forEach((checkbox, index) => {
            const suggestionItem = checkbox.closest('.suggestion-item');
            const type = suggestionItem.querySelector('h4').textContent;
            const description = suggestionItem.querySelector('.description').textContent;
            
            suggestions.push({
                type: type,
                description: description
            });
        });

        this.addShotsToScene(this.currentSelectedScene, suggestions);
        this.closeShotSuggestions();
    }

    addShotsToScene(sceneId, shotSuggestions) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return;

        const nextShotId = Math.max(...this.project.shotLab.scenes.flatMap(s => s.shots.map(shot => shot.id)), 0) + 1;

        shotSuggestions.forEach((suggestion, index) => {
            scene.shots.push({
                id: nextShotId + index,
                type: suggestion.type,
                description: suggestion.description,
                image: null
            });
        });

        this.saveProject();
        this.renderShotsList(sceneId);
        this.renderStoryboardForScene(sceneId);
        this.showNotification(`Added ${shotSuggestions.length} shots to the scene!`, 'success');
    }

    closeShotSuggestions() {
        const modal = document.getElementById('shot-suggestions-modal');
        modal?.classList.add('hidden');
    }

    openSceneEditor(sceneId = null) {
        const modal = document.getElementById('scene-editor-modal');
        const titleElement = document.getElementById('scene-editor-title');
        const titleInput = document.getElementById('scene-title-input');
        const descriptionInput = document.getElementById('scene-description-input');

        if (sceneId) {
            // Edit existing scene
            const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
            if (scene) {
                titleElement.textContent = 'Edit Scene';
                titleInput.value = scene.title;
                descriptionInput.value = scene.description;
                this.currentEditingScene = sceneId;
            }
        } else {
            // Add new scene
            titleElement.textContent = 'Add New Scene';
            titleInput.value = '';
            descriptionInput.value = '';
            this.currentEditingScene = null;
        }

        modal?.classList.remove('hidden');
        titleInput?.focus();
        this.setupSceneEditorEventListeners();
    }

    setupSceneEditorEventListeners() {
        const closeBtn = document.getElementById('scene-editor-close-btn');
        const cancelBtn = document.getElementById('cancel-scene-edit');
        const saveBtn = document.getElementById('save-scene');
        const modal = document.getElementById('scene-editor-modal');

        closeBtn?.addEventListener('click', () => this.closeSceneEditor());
        cancelBtn?.addEventListener('click', () => this.closeSceneEditor());
        saveBtn?.addEventListener('click', () => this.saveScene());
        
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) this.closeSceneEditor();
        });
    }

    saveScene() {
        const titleInput = document.getElementById('scene-title-input');
        const descriptionInput = document.getElementById('scene-description-input');

        const title = titleInput?.value.trim();
        const description = descriptionInput?.value.trim();

        if (!title || !description) {
            this.showNotification('Please fill in both title and description', 'error');
            return;
        }

        if (this.currentEditingScene) {
            // Edit existing scene
            const scene = this.project.shotLab.scenes.find(s => s.id == this.currentEditingScene);
            if (scene) {
                scene.title = title;
                scene.description = description;
                this.showNotification('Scene updated successfully!', 'success');
            }
        } else {
            // Add new scene
            const newSceneId = Math.max(...this.project.shotLab.scenes.map(s => s.id), 0) + 1;
            this.project.shotLab.scenes.push({
                id: newSceneId,
                title: title,
                description: description,
                shots: []
            });
            this.showNotification('New scene added successfully!', 'success');
        }

        this.saveProject();
        this.renderShotLab();
        this.closeSceneEditor();
    }

    closeSceneEditor() {
        const modal = document.getElementById('scene-editor-modal');
        modal?.classList.add('hidden');
        this.currentEditingScene = null;
    }

    addManualShot() {
        if (!this.currentSelectedScene) {
            this.showNotification('Please select a scene first', 'error');
            return;
        }

        const shotType = prompt('Enter shot type (e.g., Close-up, Wide Shot):');
        const shotDescription = prompt('Enter shot description:');

        if (!shotType || !shotDescription) {
            this.showNotification('Both shot type and description are required', 'error');
            return;
        }

        this.addShotsToScene(this.currentSelectedScene, [{
            type: shotType,
            description: shotDescription
        }]);
    }

    editShot(sceneId, shotId) {
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        const shot = scene?.shots.find(s => s.id == shotId);

        if (!shot) {
            this.showNotification('Shot not found', 'error');
            return;
        }

        const newType = prompt('Edit shot type:', shot.type);
        const newDescription = prompt('Edit shot description:', shot.description);

        if (newType && newDescription) {
            shot.type = newType;
            shot.description = newDescription;
            this.saveProject();
            this.renderShotsList(sceneId);
            this.renderStoryboardForScene(sceneId);
            this.showNotification('Shot updated successfully!', 'success');
        }
    }

    deleteShot(sceneId, shotId) {
        if (!confirm('Are you sure you want to delete this shot?')) return;

        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        if (!scene) return;

        scene.shots = scene.shots.filter(s => s.id != shotId);
        this.saveProject();
        this.renderShotsList(sceneId);
        this.renderStoryboardForScene(sceneId);
        this.showNotification('Shot deleted successfully!', 'info');
    }
    
    sendCurrentSceneToScreeningRoom() {
        if (!this.currentSelectedScene) {
            this.showNotification('Please select a scene first', 'error');
            return;
        }
        
        const scene = this.project.shotLab.scenes.find(s => s.id == this.currentSelectedScene);
        if (!scene || !scene.shots.length) {
            this.showNotification('Selected scene has no shots to send', 'error');
            return;
        }
        
        const defaultDuration = parseFloat(document.getElementById('default-frame-duration')?.value || '3');
        
        // Add scene shots to timeline
        scene.shots.forEach(shot => {
            this.project.screeningRoom.timeline.push({
                shotId: shot.id,
                sceneId: scene.id,
                shotType: shot.type,
                description: shot.description,
                image: shot.image,
                duration: defaultDuration
            });
        });
        
        this.saveProject();
        this.showNotification(`Added ${scene.shots.length} shots from "${scene.title}" to Screening Room timeline!`, 'success');
        
        // Optionally navigate to Screening Room
        this.navigateToSection('screening-room');
        this.renderScreeningRoom();
    }
    
    //----------------------------------------------------------------
    // VISUAL DNA MANAGEMENT
    //----------------------------------------------------------------
    
    setupVisualDNAEventListeners() {
        // Save kit buttons
        document.querySelectorAll('.save-kit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const kitType = btn.dataset.kitType;
                const kitId = btn.dataset.kitId;
                this.saveVisualDNAKit(kitType, kitId);
            });
        });
        
        // Anchor image upload
        document.getElementById('anchor-image-upload')?.addEventListener('change', (e) => {
            this.handleAnchorImageUpload(e);
        });
    }
    
    saveGlobalStyle() {
        const palette = document.getElementById('color-palette').value;
        const lighting = document.getElementById('lighting-style').value;
        const influences = document.getElementById('cinematic-influences').value;
        
        this.project.visualDNA.globalStyle = {
            palette: palette,
            lighting: lighting,
            influences: influences
        };
        
        this.saveProject();
        this.showNotification('Global style saved successfully!', 'success');
    }
    
    saveVisualDNAKit(kitType, kitId) {
        const textarea = document.querySelector(`textarea[data-kit-type="${kitType}"][data-kit-id="${kitId}"]`);
        if (!textarea) {
            this.showNotification('Error: Could not find kit to save', 'error');
            return;
        }
        
        const promptLexicon = textarea.value;
        
        if (kitType === 'character') {
            const kit = this.project.visualDNA.characterKits.find(k => k.charId == kitId);
            if (kit) {
                kit.promptLexicon = promptLexicon;
            }
        } else if (kitType === 'location') {
            const kit = this.project.visualDNA.locationKits.find(k => k.locId == kitId);
            if (kit) {
                kit.promptLexicon = promptLexicon;
            }
        }
        
        this.saveProject();
        this.showNotification(`${kitType} DNA kit saved successfully!`, 'success');
    }
    
    uploadAnchorImage(kitType, kitId) {
        // Store context for the upload
        this.currentImageUploadContext = { kitType, kitId };
        
        // Trigger file input
        document.getElementById('anchor-image-upload').click();
    }
    
    handleAnchorImageUpload(event) {
        const file = event.target.files[0];
        if (!file || !this.currentImageUploadContext) return;
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showNotification('Please select a valid image file', 'error');
            return;
        }
        
        // Check file size (limit to 5MB)
        if (file.size > 5 * 1024 * 1024) {
            this.showNotification('Image file too large. Please select a file under 5MB.', 'error');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const imageDataUrl = e.target.result;
            this.setAnchorImage(this.currentImageUploadContext.kitType, this.currentImageUploadContext.kitId, imageDataUrl);
            this.currentImageUploadContext = null;
        };
        
        reader.onerror = () => {
            this.showNotification('Error reading image file', 'error');
            this.currentImageUploadContext = null;
        };
        
        reader.readAsDataURL(file);
    }
    
    setAnchorImage(kitType, kitId, imageDataUrl) {
        let kit = null;
        
        if (kitType === 'character') {
            kit = this.project.visualDNA.characterKits.find(k => k.charId == kitId);
        } else if (kitType === 'location') {
            kit = this.project.visualDNA.locationKits.find(k => k.locId == kitId);
        }
        
        if (kit) {
            kit.anchorImage = imageDataUrl;
            this.saveProject();
            this.renderVisualDNA(); // Re-render to show the new image
            this.showNotification(`Anchor image uploaded for ${kit.name}!`, 'success');
        } else {
            this.showNotification('Error: Could not find DNA kit', 'error');
        }
    }
    
    removeAnchorImage(kitType, kitId) {
        let kit = null;
        
        if (kitType === 'character') {
            kit = this.project.visualDNA.characterKits.find(k => k.charId == kitId);
        } else if (kitType === 'location') {
            kit = this.project.visualDNA.locationKits.find(k => k.locId == kitId);
        }
        
        if (kit) {
            kit.anchorImage = null;
            this.saveProject();
            this.renderVisualDNA(); // Re-render to show the placeholder
            this.showNotification(`Anchor image removed from ${kit.name}`, 'info');
        } else {
            this.showNotification('Error: Could not find DNA kit', 'error');
        }
    }
    
    //----------------------------------------------------------------
    // PROMPT WORKBENCH FUNCTIONALITY
    //----------------------------------------------------------------
    
    setupPromptWorkbench() {
        const modal = document.getElementById('prompt-workbench-modal');
        const closeBtn = document.getElementById('modal-close-btn');
        const clearBtn = document.getElementById('clear-prompt-btn');
        const copyBtn = document.getElementById('copy-prompt-btn');
        
        // Close modal events
        closeBtn?.addEventListener('click', () => this.closePromptWorkbench());
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closePromptWorkbench();
            }
        });
        
        // Modal action buttons
        clearBtn?.addEventListener('click', () => this.clearPrompt());
        copyBtn?.addEventListener('click', () => this.copyPrompt());
        
        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal?.classList.contains('hidden')) {
                this.closePromptWorkbench();
            }
        });
    }
    
    openPromptWorkbench(shotId, sceneId) {
        const modal = document.getElementById('prompt-workbench-modal');
        const textarea = document.getElementById('prompt-workbench-textarea');
        
        // Store current shot context
        this.currentWorkbenchContext = { shotId, sceneId };
        
        // Get shot details for initial context
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        const shot = scene?.shots.find(s => s.id == shotId);
        
        if (shot) {
            // Pre-populate with shot description
            textarea.value = `${shot.type}: ${shot.description}`;
        }
        
        // Populate keyword banks with smart suggestions
        this.populateKeywordBanks();
        
        // Show context-aware assets and smart prompt suggestions
        this.showContextAwareAssets(shotId, sceneId);
        this.getSmartPromptSuggestions(shotId, sceneId);
        
        // Show modal
        modal?.classList.remove('hidden');
        textarea?.focus();
        
        this.showNotification('Prompt Workbench opened with smart suggestions! Click keywords to add to your prompt.', 'info');
    }
    
    closePromptWorkbench() {
        const modal = document.getElementById('prompt-workbench-modal');
        modal?.classList.add('hidden');
        this.currentWorkbenchContext = null;
    }
    
    populateKeywordBanks() {
        this.populateGlobalKeywords();
        this.populateCharacterKeywords();
        this.populateLocationKeywords();
    }
    
    populateGlobalKeywords() {
        const bank = document.getElementById('global-keyword-bank');
        if (!bank) return;
        
        const globalStyle = this.project.visualDNA.globalStyle;
        const keywords = [];
        
        // Extract keywords from global style properties
        if (globalStyle.palette) {
            keywords.push(...globalStyle.palette.split(',').map(k => k.trim()));
        }
        if (globalStyle.lighting) {
            keywords.push(...globalStyle.lighting.split(',').map(k => k.trim()));
        }
        if (globalStyle.influences) {
            keywords.push(...globalStyle.influences.split(',').map(k => k.trim()));
        }
        
        bank.innerHTML = keywords.map(keyword => 
            `<span class="keyword-tag global-style" data-keyword="${keyword}">${keyword}</span>`
        ).join('');
        
        // Add click events
        bank.querySelectorAll('.keyword-tag').forEach(tag => {
            tag.addEventListener('click', () => this.addKeywordToPrompt(tag.dataset.keyword));
        });
    }
    
    populateCharacterKeywords() {
        const bank = document.getElementById('character-keyword-bank');
        if (!bank) return;
        
        const characterKits = this.project.visualDNA.characterKits;
        const keywords = [];
        
        characterKits.forEach(kit => {
            if (kit.promptLexicon) {
                keywords.push(`[${kit.name}]`); // Add character name as context
                keywords.push(...kit.promptLexicon.split(',').map(k => k.trim()));
            }
        });
        
        bank.innerHTML = keywords.map(keyword => 
            `<span class="keyword-tag character" data-keyword="${keyword}">${keyword}</span>`
        ).join('');
        
        // Add click events
        bank.querySelectorAll('.keyword-tag').forEach(tag => {
            tag.addEventListener('click', () => this.addKeywordToPrompt(tag.dataset.keyword));
        });
    }
    
    populateLocationKeywords() {
        const bank = document.getElementById('location-keyword-bank');
        if (!bank) return;
        
        const locationKits = this.project.visualDNA.locationKits;
        const keywords = [];
        
        locationKits.forEach(kit => {
            if (kit.promptLexicon) {
                keywords.push(`[${kit.name}]`); // Add location name as context
                keywords.push(...kit.promptLexicon.split(',').map(k => k.trim()));
            }
        });
        
        bank.innerHTML = keywords.map(keyword => 
            `<span class="keyword-tag location" data-keyword="${keyword}">${keyword}</span>`
        ).join('');
        
        // Add click events
        bank.querySelectorAll('.keyword-tag').forEach(tag => {
            tag.addEventListener('click', () => this.addKeywordToPrompt(tag.dataset.keyword));
        });
    }
    
    addKeywordToPrompt(keyword) {
        const textarea = document.getElementById('prompt-workbench-textarea');
        if (!textarea) return;
        
        const currentValue = textarea.value;
        const cursorPosition = textarea.selectionStart;
        
        // Add keyword at cursor position (or end if no cursor position)
        const beforeCursor = currentValue.substring(0, cursorPosition);
        const afterCursor = currentValue.substring(cursorPosition);
        
        // Add appropriate spacing
        const needsSpaceBefore = beforeCursor.length > 0 && !beforeCursor.endsWith(' ') && !beforeCursor.endsWith(', ');
        const separator = needsSpaceBefore ? ', ' : '';
        
        const newValue = beforeCursor + separator + keyword + afterCursor;
        textarea.value = newValue;
        
        // Update cursor position
        const newCursorPosition = cursorPosition + separator.length + keyword.length;
        textarea.setSelectionRange(newCursorPosition, newCursorPosition);
        
        textarea.focus();
        
        // Visual feedback
        this.showNotification(`Added "${keyword}" to prompt`, 'success');
    }
    
    clearPrompt() {
        const textarea = document.getElementById('prompt-workbench-textarea');
        if (!textarea) return;
        
        textarea.value = '';
        textarea.focus();
        this.showNotification('Prompt cleared', 'info');
    }
    
    copyPrompt() {
        const textarea = document.getElementById('prompt-workbench-textarea');
        if (!textarea) return;
        
        const prompt = textarea.value.trim();
        if (!prompt) {
            this.showNotification('No prompt to copy', 'error');
            return;
        }
        
        // Copy to clipboard
        navigator.clipboard.writeText(prompt).then(() => {
            this.showNotification('Prompt copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            textarea.select();
            document.execCommand('copy');
            this.showNotification('Prompt copied to clipboard!', 'success');
        });
    }
    
    getFallbackProjectData() {
        // This returns a default project structure if the server is unavailable
        return {
            title: 'New Project',
            logline: '',
            story: { treatment: '<h1>Welcome to KINO-GEIST</h1><p>Please start the server and refresh the page to load your project data.</p>', screenplay: '' },
            storyBible: { characters: [], locations: [], props: [], themes: [] },
            visualDNA: { globalStyle: {palette: '', lighting: '', influences: ''}, characterKits: [], locationKits: [] },
            shotLab: { scenes: [] },
            assets: [],
            screeningRoom: { timeline: [] }
        };
    }

    // Asset status management
    async updateAssetStatus(assetId, status) {
        try {
            const response = await fetch(`/api/assets/${assetId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            
            if (response.ok) {
                await this.loadProject();
                this.renderAssetNexus();
                this.showNotification('Asset status updated', 'success');
            } else {
                this.showNotification('Failed to update asset status', 'error');
            }
        } catch (error) {
            console.error('Error updating asset status:', error);
            this.showNotification('Error updating asset status', 'error');
        }
    }

    // Asset details viewer
    viewAssetDetails(assetId) {
        const asset = (this.project.assets || []).find(a => a.id === assetId);
        if (!asset) return;

        const modal = document.createElement('div');
        modal.className = 'modal asset-details-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Asset Details</h3>
                    <button type="button" class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="asset-detail-grid">
                        <div class="asset-preview">
                            ${this.generateAssetPreview(asset)}
                        </div>
                        <div class="asset-metadata">
                            <h4>${asset.name}</h4>
                            <p><strong>Type:</strong> ${asset.type}</p>
                            <p><strong>Status:</strong> 
                                <span class="status-badge status-${asset.status}">${asset.status}</span>
                            </p>
                            <p><strong>Created:</strong> ${new Date(asset.uploadDate).toLocaleDateString()}</p>
                            <p><strong>Size:</strong> ${this.formatFileSize(asset.size)}</p>
                            ${asset.aiAnalysis ? `
                                <div class="ai-analysis">
                                    <h5>AI Analysis:</h5>
                                    <p>${asset.aiAnalysis}</p>
                                </div>
                            ` : ''}
                            ${asset.versions && asset.versions.length > 1 ? `
                                <div class="versions">
                                    <h5>Versions (${asset.versions.length}):</h5>
                                    ${asset.versions.map((v, i) => `
                                        <div class="version-item">
                                            <span>v${i + 1}</span>
                                            <span>${new Date(v.uploadDate).toLocaleDateString()}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.style.display = 'flex';

        // Close modal handlers
        modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    // Link asset to shot
    async linkAssetToShot(assetId, shotId) {
        try {
            const response = await fetch(`/api/assets/${assetId}/link-shot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shotId })
            });
            
            if (response.ok) {
                await this.loadProject();
                this.renderAssetNexus();
                this.showNotification('Asset linked to shot', 'success');
            } else {
                this.showNotification('Failed to link asset to shot', 'error');
            }
        } catch (error) {
            console.error('Error linking asset to shot:', error);
            this.showNotification('Error linking asset to shot', 'error');
        }
    }

    // Add new version to asset
    async addAssetVersion(assetId, file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('assetId', assetId);

            const response = await fetch('/api/assets/add-version', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                await this.loadProject();
                this.renderAssetNexus();
                this.showNotification('New version added successfully', 'success');
            } else {
                this.showNotification('Error adding version: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('Error adding asset version:', error);
            this.showNotification('Error adding asset version', 'error');
        }
    }

    // Filter assets by type
    filterAssetsByType(type) {
        const assets = document.querySelectorAll('.asset-card');
        assets.forEach(card => {
            const assetType = card.dataset.assetType;
            if (type === 'all' || assetType === type) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });

        // Update active filter button
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-filter="${type}"]`).classList.add('active');
    }

    // Filter assets by status
    filterAssetsByStatus(status) {
        const assets = document.querySelectorAll('.asset-card');
        assets.forEach(card => {
            const assetStatus = card.dataset.assetStatus;
            if (status === 'all' || assetStatus === status) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    // Search assets
    searchAssets(query) {
        const assets = document.querySelectorAll('.asset-card');
        const searchTerm = query.toLowerCase();

        assets.forEach(card => {
            const assetName = card.querySelector('.asset-name').textContent.toLowerCase();
            const assetAnalysis = card.dataset.aiAnalysis ? card.dataset.aiAnalysis.toLowerCase() : '';
            
            if (assetName.includes(searchTerm) || assetAnalysis.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Context-aware Prompt Workbench methods
    showContextAwareAssets(shotId, sceneId) {
        const bank = document.getElementById('context-assets-bank');
        if (!bank) return;
        
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        const shot = scene?.shots.find(s => s.id == shotId);
        
        if (!shot) {
            bank.innerHTML = '<span class="keyword-tag context-asset">No context available</span>';
            return;
        }
        
        const contextAssets = [];
        
        // Get characters in this shot
        if (shot.characters && shot.characters.length > 0) {
            shot.characters.forEach(charId => {
                const character = this.project.storyBible.characters.find(c => c.id == charId);
                if (character) {
                    contextAssets.push(`character: ${character.name}`);
                    contextAssets.push(`${character.name} appearance`);
                }
            });
        }
        
        // Get location information
        if (scene.location) {
            const location = this.project.storyBible.locations.find(l => l.name === scene.location);
            if (location) {
                contextAssets.push(`location: ${location.name}`);
                contextAssets.push(`${location.name} setting`);
            }
        }
        
        // Add shot type specific keywords
        if (shot.type) {
            contextAssets.push(`${shot.type} shot`);
            contextAssets.push(`${shot.type} composition`);
        }
        
        // Add mood/tone if available in scene
        if (scene.notes && scene.notes.includes('mood:')) {
            const moodMatch = scene.notes.match(/mood:\s*([^,\n]+)/i);
            if (moodMatch) {
                contextAssets.push(`${moodMatch[1].trim()} mood`);
            }
        }
        
        bank.innerHTML = contextAssets.map(asset => 
            `<span class="keyword-tag context-asset" data-keyword="${asset}">${asset}</span>`
        ).join('');
        
        // Add click events
        bank.querySelectorAll('.keyword-tag').forEach(tag => {
            tag.addEventListener('click', () => this.addKeywordToPrompt(tag.dataset.keyword));
        });
    }
    
    getSmartPromptSuggestions(shotId, sceneId) {
        const bank = document.getElementById('smart-prompts-bank');
        if (!bank) return;
        
        const scene = this.project.shotLab.scenes.find(s => s.id == sceneId);
        const shot = scene?.shots.find(s => s.id == shotId);
        
        if (!shot) {
            bank.innerHTML = '<span class="keyword-tag smart-prompt">No analysis available</span>';
            return;
        }
        
        const smartSuggestions = [];
        
        // Analyze shot description for key elements
        const description = shot.description.toLowerCase();
        
        // Suggest camera techniques based on shot type
        const shotTypeMap = {
            'extreme close-up': ['macro lens', 'shallow depth of field', 'intimate framing'],
            'close-up': ['portrait lens', 'bokeh background', 'facial details'],
            'medium shot': ['standard lens', 'balanced composition', 'character interaction'],
            'wide shot': ['wide angle lens', 'environmental context', 'establishing shot'],
            'establishing shot': ['aerial view', 'landscape', 'wide perspective']
        };
        
        if (shot.type && shotTypeMap[shot.type.toLowerCase()]) {
            smartSuggestions.push(...shotTypeMap[shot.type.toLowerCase()]);
        }
        
        // Analyze description for emotional content
        const emotionKeywords = {
            'tense': ['dramatic lighting', 'high contrast', 'shadows'],
            'peaceful': ['soft lighting', 'warm tones', 'gentle'],
            'action': ['dynamic movement', 'motion blur', 'energy'],
            'romantic': ['warm light', 'soft focus', 'golden hour'],
            'mysterious': ['low key lighting', 'silhouettes', 'fog']
        };
        
        for (const [emotion, keywords] of Object.entries(emotionKeywords)) {
            if (description.includes(emotion)) {
                smartSuggestions.push(...keywords);
            }
        }
        
        // Time of day suggestions
        if (description.includes('morning')) smartSuggestions.push('golden hour', 'sunrise');
        if (description.includes('night')) smartSuggestions.push('blue hour', 'artificial lighting');
        if (description.includes('sunset')) smartSuggestions.push('golden hour', 'warm backlight');
        
        // Weather suggestions
        if (description.includes('rain')) smartSuggestions.push('wet surfaces', 'reflections');
        if (description.includes('snow')) smartSuggestions.push('cold tones', 'white balance');
        if (description.includes('fog')) smartSuggestions.push('atmospheric', 'diffused light');
        
        // Remove duplicates and limit to 8 suggestions
        const uniqueSuggestions = [...new Set(smartSuggestions)].slice(0, 8);
        
        bank.innerHTML = uniqueSuggestions.map(suggestion => 
            `<span class="keyword-tag smart-prompt" data-keyword="${suggestion}">${suggestion}</span>`
        ).join('');
        
        // Add click events
        bank.querySelectorAll('.keyword-tag').forEach(tag => {
            tag.addEventListener('click', () => this.addKeywordToPrompt(tag.dataset.keyword));
        });
    }
}

// Initialize the application
window.kinoGeistApp = new KinoGeistStudio();

// Add CSS for notifications
const style = document.createElement('style');
style.innerHTML = `
    .notification {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        background-color: var(--c-dark-gray);
        color: var(--c-white);
        border: 1px solid var(--border-color);
        z-index: 1001;
        transform: translateX(calc(100% + 30px));
        transition: transform 0.5s ease-in-out;
        font-size: var(--fz-sm);
    }
    .notification.show {
        transform: translateX(0);
    }
    .notification.notification--info {
        border-left: 4px solid var(--c-primary);
    }
    .notification.notification--success {
        border-left: 4px solid var(--c-accent-green);
    }
    .notification.notification--error {
        border-left: 4px solid var(--c-accent-red);
    }
`;
document.head.appendChild(style);