const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const axios = require('axios');
const multer = require('multer');
const pdfParse = require('pdf-parse');
const sharp = require('sharp');
require('dotenv').config();

const app = express();
const PORT = 3000;

// Configure multer for file uploads
const storage = multer.memoryStorage();
const upload = multer({ 
    storage: storage,
    limits: {
        fileSize: 50 * 1024 * 1024 // 50MB limit for video/audio files
    },
    fileFilter: (req, file, cb) => {
        const allowedTypes = /\.(txt|md|pdf|jpg|jpeg|png|gif|mp4|mov|avi|wav|mp3|m4a)$/i;
        const isValid = allowedTypes.test(file.originalname);
        if (isValid) {
            cb(null, true);
        } else {
            cb(new Error('Only text, image, video, and audio files are allowed'));
        }
    }
});

// Middleware to parse JSON bodies
app.use(express.json());

// Serve static files from the root directory (for index.html, style.css, app.js)
app.use(express.static(path.join(__dirname)));

// Serve uploaded assets
app.use('/assets', express.static(path.join(__dirname, 'assets')));

const projectFilePath = path.join(__dirname, 'film_production_research.json');

// API Endpoint to get the current project state
app.get('/api/project', async (req, res) => {
    try {
        const data = await fs.readFile(projectFilePath, 'utf8');
        res.json(JSON.parse(data));
    } catch (error) {
        console.error('Error reading project file:', error);
        res.status(500).json({ message: 'Error loading project data.' });
    }
});

// API Endpoint to save the project state
app.post('/api/project', async (req, res) => {
    try {
        const projectData = req.body;
        await fs.writeFile(projectFilePath, JSON.stringify(projectData, null, 2), 'utf8');
        res.json({ message: 'Project saved successfully!' });
    } catch (error) {
        console.error('Error saving project file:', error);
        res.status(500).json({ message: 'Error saving project data.' });
    }
});

// API Endpoint for file upload to Writer's Room
app.post('/api/upload/script', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ message: 'No file uploaded' });
        }

        let content = '';
        const fileExtension = path.extname(req.file.originalname).toLowerCase();

        switch (fileExtension) {
            case '.txt':
            case '.md':
                content = req.file.buffer.toString('utf-8');
                break;
            case '.pdf':
                const pdfData = await pdfParse(req.file.buffer);
                content = pdfData.text;
                break;
            default:
                return res.status(400).json({ message: 'Unsupported file type' });
        }

        res.json({ 
            success: true, 
            content: content,
            filename: req.file.originalname,
            type: fileExtension
        });
    } catch (error) {
        console.error('Error processing uploaded file:', error);
        res.status(500).json({ message: 'Error processing file' });
    }
});

// API Endpoint for comprehensive asset upload to Asset Nexus
app.post('/api/upload/asset', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ message: 'No file uploaded' });
        }

        const fileExtension = path.extname(req.file.originalname).toLowerCase();
        const fileName = `${Date.now()}_${req.file.originalname}`;
        const filePath = path.join(__dirname, 'assets', fileName);
        
        // Determine asset type and category
        const assetType = getAssetType(fileExtension);
        const category = req.body.category || assetType;
        
        // Save the file to disk
        await fs.writeFile(filePath, req.file.buffer);
        
        // Extract text content for text-based files
        let content = '';
        let thumbnail = null;
        let aiAnalysis = null;

        if (['text', 'document'].includes(assetType)) {
            switch (fileExtension) {
                case '.txt':
                case '.md':
                    content = req.file.buffer.toString('utf-8');
                    break;
                case '.pdf':
                    const pdfData = await pdfParse(req.file.buffer);
                    content = pdfData.text;
                    break;
            }
        } else if (assetType === 'image') {
            // Generate thumbnail for images
            thumbnail = await generateImageThumbnail(req.file.buffer, fileName);
            
            // Get AI analysis of the image
            if (process.env.GEMINI_API_KEY) {
                aiAnalysis = await analyzeImageWithGemini(req.file.buffer);
            }
        } else if (assetType === 'video') {
            // For video files, we'll generate a thumbnail later
            // For now, just note that it's a video
            content = `Video file: ${req.file.originalname}`;
        } else if (assetType === 'audio') {
            content = `Audio file: ${req.file.originalname}`;
        }

        // Create asset object
        const asset = {
            id: Date.now().toString(),
            name: req.file.originalname,
            fileName: fileName,
            type: fileExtension,
            assetType: assetType,
            category: category,
            tags: req.body.tags ? req.body.tags.split(',').map(t => t.trim()) : [],
            content: content,
            thumbnail: thumbnail,
            aiAnalysis: aiAnalysis,
            uploadDate: new Date().toISOString(),
            size: req.file.size,
            status: 'pending', // pending, approved, rejected
            version: 1,
            parentId: null // For versioning
        };

        // Load current project, add asset, and save
        const projectData = JSON.parse(await fs.readFile(projectFilePath, 'utf8'));
        projectData.assets = projectData.assets || [];
        projectData.assets.push(asset);
        await fs.writeFile(projectFilePath, JSON.stringify(projectData, null, 2), 'utf8');

        res.json({ 
            success: true, 
            asset: asset,
            message: 'Asset uploaded successfully'
        });
    } catch (error) {
        console.error('Error uploading asset:', error);
        res.status(500).json({ message: 'Error uploading asset: ' + error.message });
    }
});

// Helper function to determine asset type
function getAssetType(extension) {
    const imageTypes = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
    const videoTypes = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];
    const audioTypes = ['.wav', '.mp3', '.m4a', '.aac', '.ogg'];
    const textTypes = ['.txt', '.md', '.pdf'];

    if (imageTypes.includes(extension)) return 'image';
    if (videoTypes.includes(extension)) return 'video';
    if (audioTypes.includes(extension)) return 'audio';
    if (textTypes.includes(extension)) return 'text';
    return 'document';
}

// Generate thumbnail for images
async function generateImageThumbnail(buffer, fileName) {
    try {
        const thumbnailFileName = `thumb_${fileName.replace(/\.[^/.]+$/, '.jpg')}`;
        const thumbnailPath = path.join(__dirname, 'assets', 'thumbnails', thumbnailFileName);
        
        await sharp(buffer)
            .resize(300, 300, { fit: 'cover' })
            .jpeg({ quality: 80 })
            .toFile(thumbnailPath);
            
        return `/assets/thumbnails/${thumbnailFileName}`;
    } catch (error) {
        console.error('Error generating thumbnail:', error);
        return null;
    }
}

// Analyze image with Gemini Vision API
async function analyzeImageWithGemini(imageBuffer) {
    try {
        const base64Image = imageBuffer.toString('base64');
        
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
            {
                contents: [{
                    parts: [
                        {
                            text: "Analyze this image for a film production context. Describe: 1) Visual elements (lighting, composition, colors), 2) Subject matter (characters, objects, locations), 3) Mood and atmosphere, 4) Potential use in filmmaking (storyboard, reference, concept art). Provide 5-7 relevant tags for categorization."
                        },
                        {
                            inlineData: {
                                mimeType: "image/jpeg",
                                data: base64Image
                            }
                        }
                    ]
                }]
            }
        );

        return response.data.candidates[0].content.parts[0].text;
    } catch (error) {
        console.error('Error analyzing image with Gemini:', error);
        return null;
    }
}

// API Endpoint to update asset status (approve/reject)
app.post('/api/assets/:id/status', async (req, res) => {
    try {
        const assetId = req.params.id;
        const { status } = req.body;

        if (!['pending', 'approved', 'rejected'].includes(status)) {
            return res.status(400).json({ message: 'Invalid status' });
        }

        const projectData = JSON.parse(await fs.readFile(projectFilePath, 'utf8'));
        const asset = projectData.assets.find(a => a.id === assetId);
        
        if (!asset) {
            return res.status(404).json({ message: 'Asset not found' });
        }

        asset.status = status;
        await fs.writeFile(projectFilePath, JSON.stringify(projectData, null, 2), 'utf8');

        res.json({ success: true, message: `Asset ${status} successfully` });
    } catch (error) {
        console.error('Error updating asset status:', error);
        res.status(500).json({ message: 'Error updating asset status' });
    }
});

// API Endpoint to create asset version
app.post('/api/assets/:id/version', upload.single('file'), async (req, res) => {
    try {
        const parentId = req.params.id;
        
        if (!req.file) {
            return res.status(400).json({ message: 'No file uploaded' });
        }

        const projectData = JSON.parse(await fs.readFile(projectFilePath, 'utf8'));
        const parentAsset = projectData.assets.find(a => a.id === parentId);
        
        if (!parentAsset) {
            return res.status(404).json({ message: 'Parent asset not found' });
        }

        // Create new version similar to original upload
        const fileExtension = path.extname(req.file.originalname).toLowerCase();
        const fileName = `${Date.now()}_v${parentAsset.version + 1}_${req.file.originalname}`;
        const filePath = path.join(__dirname, 'assets', fileName);
        
        await fs.writeFile(filePath, req.file.buffer);

        const assetType = getAssetType(fileExtension);
        let thumbnail = null;
        let aiAnalysis = null;

        if (assetType === 'image') {
            thumbnail = await generateImageThumbnail(req.file.buffer, fileName);
            if (process.env.GEMINI_API_KEY) {
                aiAnalysis = await analyzeImageWithGemini(req.file.buffer);
            }
        }

        const newVersion = {
            id: Date.now().toString(),
            name: req.file.originalname,
            fileName: fileName,
            type: fileExtension,
            assetType: assetType,
            category: parentAsset.category,
            tags: parentAsset.tags,
            thumbnail: thumbnail,
            aiAnalysis: aiAnalysis,
            uploadDate: new Date().toISOString(),
            size: req.file.size,
            status: 'pending',
            version: parentAsset.version + 1,
            parentId: parentId
        };

        projectData.assets.push(newVersion);
        await fs.writeFile(projectFilePath, JSON.stringify(projectData, null, 2), 'utf8');

        res.json({ success: true, asset: newVersion });
    } catch (error) {
        console.error('Error creating asset version:', error);
        res.status(500).json({ message: 'Error creating asset version' });
    }
});

// API Endpoint to link asset to shot
app.post('/api/shots/:shotId/link-asset', async (req, res) => {
    try {
        const shotId = req.params.shotId;
        const { assetId } = req.body;

        const projectData = JSON.parse(await fs.readFile(projectFilePath, 'utf8'));
        
        // Find the shot and asset
        let shot = null;
        for (const scene of projectData.shotLab.scenes) {
            const foundShot = scene.shots?.find(s => s.id == shotId);
            if (foundShot) {
                shot = foundShot;
                break;
            }
        }

        const asset = projectData.assets.find(a => a.id === assetId);

        if (!shot) {
            return res.status(404).json({ message: 'Shot not found' });
        }
        if (!asset) {
            return res.status(404).json({ message: 'Asset not found' });
        }

        // Link asset to shot
        shot.linkedAssets = shot.linkedAssets || [];
        if (!shot.linkedAssets.includes(assetId)) {
            shot.linkedAssets.push(assetId);
        }

        await fs.writeFile(projectFilePath, JSON.stringify(projectData, null, 2), 'utf8');
        res.json({ success: true, message: 'Asset linked to shot successfully' });
    } catch (error) {
        console.error('Error linking asset to shot:', error);
        res.status(500).json({ message: 'Error linking asset to shot' });
    }
});

// API Endpoint for Gemini AI
app.post('/api/gemini/ask', async (req, res) => {
    const { prompt, context, currentText } = req.body;

    if (!prompt) {
        return res.status(400).json({ message: 'Prompt is required.' });
    }

    // Construct a more detailed prompt for the AI
    let fullPrompt = `You are a creative assistant for a filmmaker. Here is the context for the film project:

`;
    if (context.logline) {
        fullPrompt += `Logline: ${context.logline}\n\n`;
    }
    if (context.characters && context.characters.length > 0) {
        fullPrompt += 'Characters:\n';
        context.characters.forEach(c => {
            fullPrompt += `- ${c.name}: ${c.role}. ${c.backstory}\n`;
        });
        fullPrompt += '\n';
    }
    
    // Include current text if provided
    if (currentText && currentText.trim().length > 0) {
        fullPrompt += `Current story/script text in the editor:\n---\n${currentText}\n---\n\n`;
    }
    
    fullPrompt += `Based on this context, please respond to the following user request: "${prompt}"

Please provide your response in a format that can be easily inserted into the story if the user likes it. Focus on being creative and helpful.`;

    try {
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
            {
                contents: [{ parts: [{ text: fullPrompt }] }],
            }
        );

        res.json(response.data);
    } catch (error) {
        console.error('Error with Gemini API:', error.response ? error.response.data : error.message);
        res.status(500).json({ message: 'Error communicating with Gemini API.' });
    }
});

// API Endpoint for formatting screenplay
app.post('/api/gemini/format-screenplay', async (req, res) => {
    const { prose } = req.body;

    if (!prose) {
        return res.status(400).json({ message: 'Prose is required.' });
    }

    const fullPrompt = `You are a screenplay formatting assistant. Convert the following prose into a standard screenplay format. Identify scene headings (INT./EXT.), character names, dialogue, and action lines. Here is the prose:

---

${prose}`; // Note: The original_new_string had '\n\n---\n\n' which is equivalent to the corrected_old_string's '\n\n---\n\n'. No change needed here.

    try {
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
            {
                contents: [{ parts: [{ text: fullPrompt }] }],
            }
        );

        res.json(response.data);
    } catch (error) {
        console.error('Error with Gemini API:', error.response ? error.response.data : error.message);
        res.status(500).json({ message: 'Error communicating with Gemini API.' });
    }
});

// API Endpoint for analyzing script
app.post('/api/gemini/analyze-script', async (req, res) => {
    const { script } = req.body;

    if (!script) {
        console.error('Analyze Script Error: No script provided.');
        return res.status(400).json({ message: 'Script is required.' });
    }

    console.log('Received request to analyze script. Script length:', script.length);

    const fullPrompt = `You are a script analysis assistant. Read the following script and extract the characters and locations. Return the data as a JSON object with the keys "characters" and "locations". Each character should have: name, role, occupation, backstory, traits. Each location should have: name, description.

Script to analyze:

${script}`;

    try {
        console.log('Sending request to Gemini API for script analysis...');
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
            {
                contents: [{ parts: [{ text: fullPrompt }] }],
            }
        );

        console.log('Received response from Gemini API for script analysis.');
        // Log the full response data to inspect its structure
        console.log('Gemini API Response Data:', JSON.stringify(response.data, null, 2));

        res.json(response.data);
    } catch (error) {
        console.error('Error with Gemini API for script analysis:', error.response ? error.response.data : error.message);
        res.status(500).json({ message: 'Error communicating with Gemini API.' });
    }
});

// API Endpoint for AI-assisted shot breakdown
app.post('/api/gemini/suggest-shots', async (req, res) => {
    const { sceneText, sceneTitle } = req.body;

    if (!sceneText) {
        return res.status(400).json({ message: 'Scene text is required.' });
    }

    const fullPrompt = `You are a professional cinematographer and shot breakdown specialist. Analyze the following scene and suggest a comprehensive shot list that would effectively capture the action, emotion, and pacing.

Scene Title: ${sceneTitle || 'Scene'}

Scene Content:
${sceneText}

Please return a JSON array of shot suggestions. Each shot should have:
- "type": The shot type (e.g., "Wide Shot", "Medium Shot", "Close-up", "Insert", "Over-the-Shoulder", "Tracking Shot", etc.)
- "description": A detailed description of what the shot captures
- "purpose": Why this shot is needed (e.g., "Establishes location", "Shows character emotion", "Reveals important detail")
- "duration": Estimated duration in seconds (rough estimate)

Focus on:
1. Establishing shots to set location and mood
2. Character coverage for dialogue and reactions
3. Important details that need emphasis
4. Smooth flow and visual storytelling
5. Practical shooting considerations

Return only the JSON array, no additional text.`;

    try {
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
            {
                contents: [{ parts: [{ text: fullPrompt }] }],
            }
        );

        res.json(response.data);
    } catch (error) {
        console.error('Error with Gemini API:', error.response ? error.response.data : error.message);
        res.status(500).json({ message: 'Error communicating with Gemini API.' });
    }
});

// API Endpoint for refining text
app.post('/api/gemini/refine', async (req, res) => {
    const { prompt } = req.body;

    if (!prompt) {
        return res.status(400).json({ message: 'Prompt is required.' });
    }

    try {
        const response = await axios.post(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
            {
                contents: [{ parts: [{ text: prompt }] }],
            }
        );

        res.json(response.data);
    } catch (error) {
        console.error('Error with Gemini API:', error.response ? error.response.data : error.message);
        res.status(500).json({ message: 'Error communicating with Gemini API.' });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`KINO-GEIST Server running at http://localhost:${PORT}`);
});