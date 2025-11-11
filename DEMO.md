# Demo & Usage Guide

## What You'll See

When you open `http://localhost:5000`, you'll see a clean, modern web interface with:

### Header Section
```
📝 Blog Automation
Generate and publish blog posts to Webflow CMS
```

### Main Form
A beautiful form with the following fields:

1. **Blog Topic / Prompt** (Required)
   - Large textarea
   - Example: "Write about the top 5 theaters in downtown Houston and what makes them special"
   - This is where you describe what content you want

2. **Author ID**
   - Pre-filled with: `671fcf925e3bc8b2761baaa2`
   - Links the post to a Webflow author

3. **Category ID**
   - Pre-filled with: `66ba3e3134ef3aa9b21a2fa1`
   - Links the post to a Webflow category

4. **Featured Image URL** (Optional)
   - Provide a direct image URL
   - If left blank, automatically fetches from Unsplash

5. **Publish Date** (Optional)
   - Date/time picker
   - Defaults to today if not specified

6. **Publish Checkbox**
   - Unchecked = Save as draft
   - Checked = Publish immediately

7. **Generate Button**
   - Large purple button
   - Shows spinner while generating

## Example Usage Scenarios

### Scenario 1: Quick Draft Post
```
Topic: "Write about why Houston is the best city for theater lovers"
Author ID: [default]
Category ID: [default]
Featured Image: [leave blank]
Publish: [unchecked]
Publish Date: [leave blank]

Click "Generate Blog Post"
Wait ~45 seconds
Result: Draft post created in Webflow
```

### Scenario 2: Publish Immediately with Custom Image
```
Topic: "Top 10 things to do in Houston this October"
Author ID: [default]
Category ID: [default]
Featured Image: https://unsplash.com/photos/houston-skyline.jpg
Publish: [checked]
Publish Date: [today]

Click "Generate Blog Post"
Wait ~50 seconds
Result: Published post live in Webflow
```

### Scenario 3: Schedule Future Post
```
Topic: "Holiday events in Houston - December guide"
Author ID: [default]
Category ID: [default]
Featured Image: [leave blank]
Publish: [unchecked]
Publish Date: 2025-12-01 09:00
Click "Generate Blog Post"
Wait ~45 seconds
Result: Draft post with future publish date
```

## Success Response

After generation completes, you'll see a green success box with:

```
✅ Blog Post Created Successfully!

Status: 📝 Draft (or ✅ Published)
Title: Top 10 Things to Do in Houston This October
Slug: top-10-things-to-do-in-houston-this-october
Reading Time: 7 min
Item ID: 68ee596d19e615bc52faa2ae

Subtitle
Discover the best attractions, events, and hidden gems...

Check your Webflow CMS collection to view and edit the post.
```

## Error Response

If something goes wrong, you'll see a red error box:

```
❌ Error

Missing OPENAI_API_KEY

Please check your configuration and try again.
```

Common errors:
- `Missing OPENAI_API_KEY` — Export your OpenAI key
- `Create item failed: 401` — Check Webflow API token
- `OpenAI returned invalid JSON` — Retry, may be temporary API issue
- `No Unsplash results` — Try a different search query or provide custom image URL

## Tips for Best Results

### Writing Great Prompts

**Good Prompts:**
- ✅ "Write a comprehensive guide to Houston's Museum District, including the top 5 museums, visitor tips, and parking information"
- ✅ "Create a blog post about the best rooftop bars in Houston, featuring prices, ambiance, and what makes each unique"
- ✅ "Write about the history of theater in Houston, from its founding to present day, highlighting major venues and productions"

**Bad Prompts:**
- ❌ "Houston" (too vague)
- ❌ "Write something" (no direction)
- ❌ "Blog post" (no topic)

### Content Tips

1. **Be Specific**: The more detailed your prompt, the better the output
2. **Include Context**: Mention target audience, tone, or specific details
3. **Length Guidance**: The system targets 700-1000 words automatically
4. **Local Focus**: Works best with Houston-specific topics

### Image Selection

- **Auto (Unsplash)**: Works great for generic topics (theaters, restaurants, events)
- **Custom URL**: Use when you have a specific image in mind
- **Pro Tip**: Unsplash images are optimized for web use automatically

## Generated Content Structure

The AI generates content with this structure:

```html
<h5>Introduction Section</h5>
<p>Opening paragraph that hooks the reader...</p>

<h5>Main Point 1</h5>
<p>Detailed explanation of the first point...</p>
<p>Additional context and examples...</p>

<h5>Main Point 2</h5>
<p>Detailed explanation of the second point...</p>

... (4-6 major sections)

<h5>Conclusion</h5>
<p>Wrapping up with final thoughts...</p>
```

Features:
- Uses `<h5>` for section headings
- `<p>` tags for paragraphs
- `<strong>` for emphasis
- No promotional content or calls to action
- Neutral, informative tone

## Testing Checklist

Before you start creating real posts, test with:

- [ ] Generate a draft post (publish unchecked)
- [ ] Check the post appears in Webflow CMS
- [ ] Verify the reading time is accurate
- [ ] Test with a custom image URL
- [ ] Test with Unsplash auto-image
- [ ] Try publishing immediately
- [ ] Set a future publish date
- [ ] Test with different prompt lengths

## Performance Expectations

| Step | Duration |
|------|----------|
| Submit form | Instant |
| OpenAI content generation | 30-50 seconds |
| Image fetch/upload | 2-5 seconds |
| Webflow CMS creation | 1-2 seconds |
| **Total** | **35-60 seconds** |

Progress indicators:
- Button shows spinner during generation
- Browser tab may show "waiting" cursor
- Success/error message appears when complete

## Troubleshooting

### Form Won't Submit
- Check browser console for errors (F12)
- Verify prompt field is not empty
- Try refreshing the page

### Long Wait Times (>2 minutes)
- OpenAI API may be slow - wait a bit longer
- Check terminal for error messages
- Verify internet connection

### "Network Error"
- Is the Flask server running?
- Check `http://localhost:5000/health`
- Look for error messages in terminal

### Success But Post Not in Webflow
- Check Webflow CMS collection directly
- Verify collection ID is correct
- Check Webflow API token permissions

## Next Steps After Testing

1. **Customize System Prompt**: Edit `api/index.py` to change writing style
2. **Add Authentication**: Protect the form with login
3. **Schedule Posts**: Add cron job or scheduling feature
4. **Deploy**: Push to Vercel for production use
5. **Monitor**: Add analytics to track post performance

Happy blogging! 🎉


