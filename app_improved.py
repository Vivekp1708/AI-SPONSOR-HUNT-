import os
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import RequestBlocked, TranscriptsDisabled, NoTranscriptFound
from anthropic import Anthropic
import traceback
from streamlit.errors import StreamlitSecretNotFoundError
from saas_database import SAAS_DATABASE, format_for_claude_prompt

# Page config
st.set_page_config(page_title="Sponsor Scout Pro", page_icon="🤖", layout="wide")

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .stat-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="main-header">🤖 Sponsor Scout Pro</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI-Powered Creator Outreach Agent - Generate perfect sponsorship pitches for any YouTube channel</p>', unsafe_allow_html=True)

# Secure API Key Retrieval
try:
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
except StreamlitSecretNotFoundError:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    st.error("⚠️ API Key not found! Add 'ANTHROPIC_API_KEY' to your Streamlit Secrets or environment variables.")
    st.stop()

# Helper Functions
def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("/")[-1].split("?")[0]
    elif "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return None

def get_full_transcript_with_fallback(video_id, use_cookies=False):
    """
    Get full video transcript with multiple fallback strategies
    
    Strategy 1: Try direct API call (no auth)
    Strategy 2: Try with cookies if enabled
    Strategy 3: Try with different languages
    """
    
    # Strategy 1: Direct API call (works ~70% of time)
    try:
        st.info("🔄 Attempting transcript fetch (Method 1: Direct API)...")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text, len(full_text), "direct_api"
    
    except RequestBlocked:
        st.warning("⚠️ Method 1 failed (IP blocked). Trying fallback methods...")
    
    except (TranscriptsDisabled, NoTranscriptFound):
        raise Exception("This video has no transcript available (captions disabled)")
    
    # Strategy 2: Try with cookies (if file exists)
    if use_cookies and os.path.exists('youtube_cookies.txt'):
        try:
            st.info("🔄 Attempting with cookies (Method 2)...")
            import http.cookiejar
            import requests
            
            session = requests.Session()
            cj = http.cookiejar.MozillaCookieJar('youtube_cookies.txt')
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cj
            
            ytt = YouTubeTranscriptApi(http_client=session)
            fetched = ytt.fetch(video_id)
            transcript_list = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
            full_text = " ".join([item['text'] for item in transcript_list])
            return full_text, len(full_text), "cookies"
        
        except Exception as e:
            st.warning(f"⚠️ Method 2 failed: {str(e)}")
    
    # Strategy 3: Try auto-generated transcript in different languages
    try:
        st.info("🔄 Trying auto-generated transcripts (Method 3)...")
        transcript_list_obj = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get any available transcript
        for transcript in transcript_list_obj:
            try:
                transcript_data = transcript.fetch()
                full_text = " ".join([item['text'] for item in transcript_data])
                return full_text, len(full_text), "auto_generated"
            except:
                continue
    
    except Exception as e:
        st.warning(f"⚠️ Method 3 failed: {str(e)}")
    
    # If all methods fail
    raise RequestBlocked(
        "All transcript fetch methods failed. Possible solutions:\n"
        "1. Try a different video from the same channel\n"
        "2. Add youtube_cookies.txt file (export from browser)\n"
        "3. Use a VPN or proxy to change your IP\n"
        "4. Wait 10-15 minutes and try again (temporary IP ban)"
    )

def analyze_with_improved_claude(transcript, video_count=1):
    """
    Enhanced Claude prompt for better pitch quality
    - More nuanced analysis
    - Better company matching logic
    - Realistic pricing
    - Actionable strategies
    """
    
    # Get formatted SaaS database
    saas_companies_text = format_for_claude_prompt()
    
    system_prompt = f"""You are an elite talent manager and sponsorship strategist with 10+ years experience in creator partnerships. You've negotiated deals worth $50M+ across YouTube, Twitch, and Instagram.

**YOUR MISSION:**
Analyze YouTube creator content and generate professional sponsorship pitches that match them with perfect SaaS partners from our database.

**50+ SAAS COMPANIES DATABASE (ALL NICHES):**
{saas_companies_text}

**ANALYSIS FRAMEWORK:**

1. **Deep Creator Profiling**
   - Content niche (be specific - not just "tech" but "Python tutorials for beginners")
   - Teaching/presentation style (energetic, calm, technical, beginner-friendly)
   - Production quality (matters for brand alignment)
   - Unique differentiators (what makes them special)
   - Upload consistency and channel trajectory

2. **Sophisticated Audience Analysis**
   - Demographic inference from content style and topic
   - Career stage (students, career-changers, professionals)
   - Purchase intent (how likely to buy B2B SaaS)
   - Geographic hints from language/references
   - Pain points mentioned or implied in content

3. **Intelligent Company Matching**
   - Match 3 companies from database using these criteria:
     * Content-product alignment (must be natural fit)
     * Audience-customer overlap (ICP match)
     * Integration potential (can it be demo'd organically?)
     * Competitive positioning (avoid if competitor already sponsors)
   - Assign realistic fit scores (most are 3-4 stars, only perfect matches get 5)
   - Consider creator size (pricing tier adjustment)

4. **Strategic Pitch Construction**
   - Lead with data-driven insights
   - Highlight mutual value (not just what creator gets)
   - Provide specific integration examples from their content
   - Realistic pricing based on: channel size, engagement, niche, production quality

**OUTPUT STRUCTURE:**

---
## 🎯 CREATOR PROFILE

**Channel Name**: [Extract from content or say "Unknown Channel"]
**Content Niche**: [Be hyper-specific - e.g. "Frontend web development for React beginners" not "web dev"]
**Technical Level**: [Beginner-friendly / Intermediate / Advanced / Mixed]
**Content Style**: [e.g. "Fast-paced tutorial walkthroughs", "Calm explanatory", "Energetic project builds"]
**Production Quality**: [Basic / Professional / Premium] - matters for brand alignment
**Unique Value Proposition**: [2-3 sentences on what makes them different]
**Channel Trajectory**: [Growing / Stable / Declining - based on content patterns]

---
## 👥 AUDIENCE ANALYSIS

**Primary Demographics**:
- Age range: [Educated estimate based on content complexity]
- Career stage: [e.g. "50% students, 30% junior devs, 20% career changers"]
- Geographic focus: [Based on language, cultural references, time zones mentioned]
- Income level: [Relevant for purchase power]

**Audience Pain Points** (from video content):
1. [Specific pain point mentioned or implied]
2. [Second pain point with context]
3. [Third pain point]

**Purchase Intent**: [Low/Medium/High] - **[2 sentence justification]**

**Engagement Signals**: [Comment patterns, question types, emotional reactions visible in content]

---
## 🏆 TOP SAAS MATCHES

### Match #1: [Company Name]
**Fit Score**: ⭐⭐⭐⭐⭐ (X/5) - [Brief justification for score]

**Why This Works**:
[3-4 sentences with SPECIFIC examples from their content. Reference actual topics/problems discussed in the video. Explain product-content alignment and audience-customer fit.]

**Integration Ideas**:
1. **"[Catchy Video Title Idea]"** - [30-word description of how to naturally integrate product into content. Make it feel organic, not ad-like.]
2. **"[Second Integration Angle]"** - [Alternative approach if first doesn't fit their style]

**Expected Performance**: [Views estimate], [CTR estimate], [Conversion estimate]

**Estimated Partnership Value**: 
- Single video: $[range]
- 4-6 video series: $[range]
- Affiliate-only: [commission % + estimated earnings]

**Negotiation Tip**: [One specific leverage point for this company]

---
### Match #2: [Company Name]
[Same structure]

---
### Match #3: [Company Name]
[Same structure]

---
## 📧 OUTREACH EMAIL TEMPLATE

**Subject**: [Compelling subject line with hook]

[Write 180-220 word email that:]
- Opens with specific observation about creator's content (shows you watched)
- Bridges to company's product value prop
- Includes 1-2 data points (views, engagement, audience demographics)
- Proposes specific content concept (not generic "we'd love to work with you")
- Clear CTA with next step
- Professional but warm tone

**Send to**: partnerships@[company].com or use LinkedIn to find Partnership Manager

---
## 💡 STRATEGIC RECOMMENDATIONS

**For This Creator:**
1. [Specific actionable tip about their sponsorship positioning]
2. [Content angle that would attract sponsors]
3. [Pricing strategy for their channel size/niche]

**Red Flags to Avoid:**
- [Company types that would be bad fit]
- [Common mistakes for their niche]

**Growth Opportunities:**
- [How to increase sponsorship value]

---
## 📊 COMPETITIVE LANDSCAPE

**Similar Channels Doing Sponsorships:**
[If you can infer from content, mention 2-3 comparable creators and what sponsors they work with]

**Market Rate Context:**
Channels in this niche with [size estimate] typically command $[range] per integration.

---

**CRITICAL RULES:**
- Be HONEST with fit scores - 5/5 is rare, most are 3-4
- Base ALL analysis on actual transcript content
- NO generic recommendations - everything must be specific to this creator
- Realistic pricing - don't oversell or undersell
- Only recommend companies from our database
- If transcript is unclear, say so - don't make up details
- Consider creator size when pricing (small channel ≠ huge rates)
- Integration ideas must be NATURAL to their content style

**PRICING CONTEXT:**
- Nano (1K-10K subs): $500-$2K per video
- Micro (10K-50K subs): $1.5K-$4K per video
- Mid (50K-250K subs): $3K-$8K per video
- Macro (250K-1M subs): $6K-$15K per video
- Mega (1M+ subs): $10K-$50K+ per video

Adjust based on: niche (B2B tech = premium), engagement rate, production quality, brand safety."""

    client = Anthropic(api_key=api_key)
    
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8000,  # Increased for detailed output
        system=system_prompt,
        messages=[{
            "role": "user", 
            "content": f"""Analyze this YouTube video transcript(s) and generate a comprehensive sponsorship pitch.

**ANALYSIS CONTEXT:**
- Number of videos: {video_count}
- Total transcript length: {len(transcript):,} characters
- Your task: Deep analysis → Company matches → Pitch strategy

**TRANSCRIPT:**
{transcript[:80000]}

**INSTRUCTIONS:**
1. Read the ENTIRE transcript carefully
2. Identify creator's niche, style, and audience
3. Match with 3 BEST companies from our 50+ company database
4. Generate professional pitch following the exact structure
5. Be specific, realistic, and actionable

Generate the analysis now."""
        }]
    )
    
    return message.content[0].text

# ============================================
# MAIN UI
# ============================================

# Sidebar
with st.sidebar:
    st.markdown("## 🚀 Features")
    st.markdown("""
    ✅ **50+ SaaS Companies** (all niches)  
    ✅ **Smart IP blocking workaround**  
    ✅ **Full transcript analysis**  
    ✅ **Multi-video support**  
    ✅ **Realistic pricing**  
    ✅ **Ready-to-send emails**  
    ✅ **Strategic recommendations**
    """)
    
    st.markdown("---")
    st.markdown("## 📊 Database Coverage")
    
    # Show niche categories
    categories = {}
    for company in SAAS_DATABASE.values():
        cat = company['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        st.markdown(f"**{category}**: {count} companies")
    
    st.markdown("---")
    st.markdown("## 💰 Monetization")
    st.markdown("""
    **Use this tool to**:
    - Offer sponsorship consulting ($500-2K/pitch)
    - Create sponsorship marketplace
    - Build creator management agency
    - Sell access as SaaS ($99-299/mo)
    """)
    
    st.markdown("---")
    st.markdown("### 🔒 Privacy")
    st.caption("Transcripts processed via Claude API. No permanent storage.")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🎬 Video Input")
    video_urls = st.text_area(
        "Paste YouTube Video URL(s) - One per line",
        placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...",
        height=120,
        help="Analyze multiple videos for better channel insights"
    )

with col2:
    st.markdown("### ⚙️ Advanced Options")
    use_cookies = st.checkbox(
        "Enable cookie fallback",
        value=False,
        help="Use cookies if direct API fails (requires youtube_cookies.txt)"
    )
    
    show_debug = st.checkbox("Show debug info", value=False)

# Info boxes
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.info("💡 **Tip**: Analyze 3-5 recent videos for best results")
with col_b:
    st.info("🌍 **Global**: Covers all content niches & regions")
with col_c:
    st.info("🎯 **Smart**: 50+ SaaS companies, auto-matched")

# Generate Button
if st.button("🚀 Generate Professional Pitch", type="primary", use_container_width=True):
    
    urls = [url.strip() for url in video_urls.split('\n') if url.strip()]
    
    if not urls:
        st.error("⚠️ Please enter at least one YouTube video URL")
        st.stop()
    
    # Validate URLs
    valid_urls = []
    for url in urls:
        video_id = extract_video_id(url)
        if video_id:
            valid_urls.append((url, video_id))
        else:
            st.warning(f"⚠️ Invalid URL (skipped): {url}")
    
    if not valid_urls:
        st.error("❌ No valid YouTube URLs found")
        st.stop()
    
    try:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_transcripts = []
        total_chars = 0
        fetch_methods = []
        
        status_text.text(f"📥 Fetching transcripts from {len(valid_urls)} video(s)...")
        
        # Fetch transcripts
        for idx, (url, video_id) in enumerate(valid_urls):
            progress = (idx + 1) / (len(valid_urls) + 1)
            progress_bar.progress(progress)
            status_text.text(f"📥 Fetching transcript {idx+1}/{len(valid_urls)}... Video ID: {video_id}")
            
            try:
                transcript, char_count, method = get_full_transcript_with_fallback(video_id, use_cookies)
                all_transcripts.append(f"--- VIDEO {idx+1} (ID: {video_id}) ---\n{transcript}")
                total_chars += char_count
                fetch_methods.append(method)
                
                st.success(f"✅ Video {idx+1} fetched successfully ({char_count:,} chars) via {method}")
            
            except Exception as e:
                st.error(f"❌ Video {idx+1} failed: {str(e)}")
                if show_debug:
                    st.code(traceback.format_exc())
        
        if not all_transcripts:
            st.error("❌ Failed to fetch any transcripts. See errors above.")
            st.info("""
            **Troubleshooting Tips:**
            1. Try videos from a different channel
            2. Wait 10-15 minutes if IP blocked
            3. Enable 'cookie fallback' option
            4. Use a VPN to change your IP address
            5. Some videos have transcripts disabled
            """)
            st.stop()
        
        # Combine transcripts
        combined_transcript = "\n\n".join(all_transcripts)
        
        # Display stats
        st.success(f"✅ Successfully fetched {len(all_transcripts)}/{len(valid_urls)} video(s)")
        
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        stat_col1.metric("Videos Analyzed", len(all_transcripts))
        stat_col2.metric("Total Characters", f"{total_chars:,}")
        stat_col3.metric("Estimated Words", f"{total_chars//5:,}")
        stat_col4.metric("Companies in DB", len(SAAS_DATABASE))
        
        # Analyze with Claude
        status_text.text("🤖 Analyzing with Claude Sonnet 4.5... (this may take 20-40 seconds)")
        progress_bar.progress(0.8)
        
        pitch = analyze_with_improved_claude(combined_transcript, len(all_transcripts))
        
        progress_bar.progress(1.0)
        status_text.text("✅ Analysis complete!")
        
        # Display results
        st.markdown("---")
        st.markdown("# 📊 Professional Sponsorship Pitch")
        st.markdown(pitch)
        
        # Action buttons
        col_download, col_copy = st.columns(2)
        
        with col_download:
            st.download_button(
                label="📥 Download as Markdown",
                data=pitch,
                file_name=f"pitch_{valid_urls[0][1]}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col_copy:
            st.code(pitch, language="markdown")
        
        # Debug info
        if show_debug:
            with st.expander("🔍 Debug Information"):
                st.json({
                    "videos_attempted": len(valid_urls),
                    "videos_successful": len(all_transcripts),
                    "total_characters": total_chars,
                    "fetch_methods": fetch_methods,
                    "companies_in_db": len(SAAS_DATABASE),
                    "transcript_preview": combined_transcript[:500]
                })
        
    except Exception as e:
        st.error(f"❌ Error: {type(e).__name__}")
        st.error(str(e))
        
        with st.expander("🔍 Full Error Details"):
            st.code(traceback.format_exc())
        
        # Helpful suggestions based on error type
        if "RequestBlocked" in str(type(e).__name__):
            st.warning("""
            **Your IP is blocked by YouTube.** Solutions:
            
            1. **Wait 10-15 minutes** - Temporary blocks usually expire
            2. **Use VPN** - Change your IP address
            3. **Enable cookies** - Check 'Enable cookie fallback' option
            4. **Try different videos** - Some channels are less restricted
            5. **Deploy locally** - Run on your home network instead of cloud
            """)
        
        elif "TranscriptsDisabled" in str(e) or "NoTranscriptFound" in str(e):
            st.warning("""
            **This video has no transcript.**
            
            - Creator disabled captions
            - Try a different video from the same channel
            - Most popular channels have transcripts enabled
            """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6c757d; padding: 1rem;'>
    <p><strong>Sponsor Scout Pro</strong> • 50+ SaaS Companies • All Content Niches</p>
    <p>Built with Anthropic Claude Sonnet 4.5 • YouTube Transcript API</p>
</div>
""", unsafe_allow_html=True)
