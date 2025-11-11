# 🚀 Quick Start Guide

Get your blog automation app running in 3 minutes!

## Prerequisites

- Python 3.9 or higher
- An OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Setup Instructions

### 1. Run the setup script
```bash
./setup.sh
```

This will:
- ✅ Create a Python virtual environment
- ✅ Install all dependencies
- ✅ Verify Python installation

### 2. Set your OpenAI API key
```bash
export OPENAI_API_KEY='sk-your-api-key-here'
```

**Important:** The Webflow credentials are already configured in the code, so you only need to set the OpenAI key!

### 3. Start the server
```bash
./run.sh
```

You should see:
```
🚀 Starting Blog Automation Server...

📱 Open your browser to: http://localhost:5000

Press Ctrl+C to stop the server

 * Serving Flask app 'index'
 * Running on http://0.0.0.0:5000
```

### 4. Open your browser

Navigate to: **http://localhost:5000**

You'll see a beautiful web interface! 🎨

## Using the Web Interface

1. **Enter a blog topic/prompt**
   - Example: "Write about the top 5 theaters in downtown Houston"

2. **Configure settings**
   - Author ID and Category ID are pre-filled
   - Optionally add a custom featured image URL
   - Choose to publish immediately or save as draft

3. **Click "Generate Blog Post"**
   - Wait 30-60 seconds while AI generates content
   - The post will be automatically created in Webflow!

4. **View result**
   - See the created post details
   - Get the Webflow item ID
   - Check your Webflow CMS to view the full post

## Troubleshooting

### "Command not found: ./setup.sh"
Make the script executable:
```bash
chmod +x setup.sh run.sh
./setup.sh
```

### "Virtual environment not found"
Run `./setup.sh` first before running `./run.sh`

### "Missing OPENAI_API_KEY"
Make sure you export it in the same terminal where you run `./run.sh`:
```bash
export OPENAI_API_KEY='your-key'
./run.sh
```

### Port 5000 already in use
Kill the process using port 5000:
```bash
lsof -ti:5000 | xargs kill -9
```

Or change the port in `api/index.py`:
```python
app.run(host="0.0.0.0", port=8000)  # Change to any available port
```

## Next Steps

### Deploy to Vercel

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   vercel --prod
   ```

3. Set environment variable in Vercel dashboard:
   - `OPENAI_API_KEY`

### Customize Content Generation

Edit the system prompt in `api/index.py` (line ~177) to customize:
- Writing style
- Content length
- Tone and voice
- Specific topics or themes

### Add More Features

- Email notifications when posts are created
- Schedule posts for future publishing
- Multiple content templates
- Integration with other CMS platforms

## Support

If you run into issues:
1. Check that Python 3.9+ is installed: `python3 --version`
2. Verify the virtual environment exists: `ls -la venv/`
3. Check Flask is running: `curl http://localhost:5000/health`

Happy blogging! 📝✨

