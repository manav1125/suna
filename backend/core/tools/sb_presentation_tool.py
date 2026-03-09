from core.agentpress.tool import ToolResult, openapi_schema, tool_metadata
from core.sandbox.tool_base import SandboxToolsBase
from core.agentpress.thread_manager import ThreadManager
from core.utils.logger import logger
from core.services.http_client import get_http_client
from core.utils.config import get_config
from core.billing.credits.media_integration import media_billing
from typing import List, Dict, Optional, Union, TYPE_CHECKING, Any
from bs4 import BeautifulSoup, NavigableString
from html import escape
import json
import os
from datetime import datetime
import re
import asyncio
from pathlib import Path
from urllib.parse import unquote
import replicate

if TYPE_CHECKING:
    import httpx

@tool_metadata(
    display_name="Presentations",
    description="Create and manage stunning presentation slides",
    icon="Presentation",
    color="bg-orange-100 dark:bg-orange-800/50",
    weight=70,
    visible=True,
    usage_guide="""
### PRESENTATION CREATION WORKFLOW

**MANDATORY QUALITY GATES (DO NOT SKIP):**
- If you call `load_template_design` with `presentation_name`, you MUST then use `create_slide` to replace the initialized placeholder content while preserving the copied template's framework/layout, design system, and assets. `populate_template_slide` is now a legacy fallback for exact template surgery only.
- If you are using a built-in template, initialize the template first and then use `create_slide` for the actual slide output so the deck stays deterministic.
- Never finish right after template copy; template copy is setup only, not final output.
- Every custom slide must include a clear visual structure (styled layout, chart/table/image/iconography), not plain text-only HTML.
- If using `../images/...` paths, ensure those files actually exist first.
- For custom slides, do NOT hotlink public internet image URLs directly inside `<img src="">`. Download them into `presentations/images/` first or use generated workspace assets.
- If the user asks for no images or wants images removed from a deck, keep the work inside presentation tools and create/update the slide without visuals. Do NOT use canvas tools for that.

**🚨 CRITICAL: This tool provides the create_slide function for presentations!**
- **Use create_slide for both custom-theme decks and template-initialized decks**
- **For template-based presentations, load the template with `presentation_name` first, then use create_slide to preserve the template framework while rendering each real slide**
- **NEVER** use generic create_file to create presentation slides
- This tool is specialized for presentation creation with proper formatting, validation, and navigation

**🚨 ABSOLUTE REQUIREMENT - NO SEARCHES BEFORE INITIALIZATION:**
- **DO NOT perform ANY web search, image search, or research BEFORE initializing the presentation tool**
- **MUST initialize the presentation tool FIRST** using initialize_tools
- **ONLY AFTER initialization**, follow the guide phases in exact order - Phase 1 → Phase 2 → Phase 3 → Phase 4 → Final Phase
- **MUST FOLLOW THE GUIDE BLINDLY** - execute each phase exactly as specified, in order, without skipping steps or doing work out of sequence
- The guide specifies exactly when to do searches (Phase 2 and Phase 3) - do NOT do them earlier

**DEFAULT: CUSTOM THEME (ALWAYS USE UNLESS USER EXPLICITLY REQUESTS TEMPLATE)**
Always create truly unique presentations with custom design systems based on the topic's actual brand colors and visual identity.

**EFFICIENCY RULES - CRITICAL:**
1. **Web/Image Search:** ALWAYS use batch mode with multiple queries - use web_search with multiple queries - ALL queries in ONE call
2. **Shell Commands:** Chain ALL folder creation + downloads in ONE command
3. **Task Updates:** ONLY update tasks when completing a PHASE. Batch updates in SAME call

**FOLDER STRUCTURE:**
```
presentations/
  ├── images/              (shared images folder - used BEFORE presentation folder created)
  │     └── image1.png
  └── [title]/             (created when first slide made)
        └── slide01.html
```
- Images go to `presentations/images/` BEFORE the presentation folder exists
- Reference images using `../images/[filename]` (go up one level from presentation folder)

**CUSTOM THEME WORKFLOW (DEFAULT):**

Follow this workflow for every presentation. **Complete each phase fully before moving to the next.**

**Phase 1: Topic Confirmation** 📋

1. **Extract Topic from User Input**: Identify the presentation topic from the user's message. If the user has already provided clear topic information, proceed directly to Phase 2 with reasonable defaults:
   - **Target audience**: Default to "General public" unless explicitly specified
   - **Presentation goals**: Default to "Informative overview" unless explicitly specified
   - **Requirements**: Use sensible defaults based on the topic

2. **Only Ask if Truly Ambiguous**: ONLY use the `ask` tool if:
   - The topic is completely unclear or missing
   - There are multiple valid interpretations that would significantly change the presentation
   - The user explicitly requests clarification
   
   **DO NOT ask for:**
   - Target audience if not specified (use "General public" default)
   - Presentation goals if not specified (use "Informative overview" default)
   - Requirements if not specified (proceed with sensible defaults)
   
   **Action-first approach**: When the topic is clear, immediately proceed to Phase 2. Don't ask unnecessary questions that delay creation.

**Phase 2: Theme and Content Planning** 📝

1. **Batch Web Search for Brand Identity**: Use `web_search` in BATCH MODE to research the topic's visual identity efficiently:
   ```
   use web_search with multiple queries ([topic] brand colors, [topic] visual identity, [topic] official website design, [topic] brand guidelines)
   ```
   **ALL queries in ONE call.** Search for specific brand colors, visual identity, and design elements:
   - For companies/products: Search for their official website, brand guidelines, marketing materials
   - For people: Search for their personal website, portfolio, professional profiles
   - For topics: Search for visual identity, brand colors, or design style associated with the topic

2. **Define Context-Based Custom Color Scheme and Design Elements**: Based on the research findings, define the custom color palette, font families, typography, and layout patterns. **🚨 CRITICAL REQUIREMENTS - NO GENERIC COLORS ALLOWED**:
   - **USE ACTUAL TOPIC-SPECIFIC COLORS**: The color scheme MUST be based on the actual topic's brand colors, visual identity, or associated colors discovered in research, NOT generic color associations:
     - **CORRECT APPROACH**: Research the actual topic's brand colors, visual identity, or design elements from official sources (website, brand guidelines, marketing materials, etc.) and use those specific colors discovered in research
     - **WRONG APPROACH**: Using generic color associations like "blue for tech", "red for speed", "green for innovation", "purple-to-blue gradient for tech" without first checking what the actual topic's brand uses
     - **For companies/products**: Use their actual brand colors from their official website, brand guidelines, or marketing materials discovered in research
     - **For people**: Use your research to find their actual visual identity from relevant sources (website, portfolio, professional profiles, etc.)
     - **For topics**: Use visual identity, brand colors, or design style associated with the topic discovered through research
     - **Always verify first**: Never use generic industry color stereotypes without checking the actual topic's brand/visual identity
   - **🚨 ABSOLUTELY FORBIDDEN**: Do NOT use generic tech color schemes like "purple-to-blue gradient", "blue for tech", "green for innovation" unless your research specifically shows these are the topic's actual brand colors. Always verify first!
   - **Research-Driven**: If the topic has specific brand colors discovered in research, you MUST use those. If research shows no specific brand colors exist, only then use colors that are contextually associated with the topic based on your research findings, but EXPLAIN why those colors are contextually appropriate based on your research.
   - **No Generic Associations**: Avoid generic color meanings like "blue = tech", "red = speed", "green = growth", "purple-to-blue gradient = tech" unless your research specifically shows these colors are associated with the topic. These generic associations are FORBIDDEN.
   - **For People Specifically**: If researching a person, you MUST use your research to find their actual color scheme and visual identity from relevant sources. Determine what sources are appropriate based on the person's profession, field, and what you discover in research (could be website, portfolio, professional profiles, social media, etc. - decide based on context). Only if you cannot find any visual identity, then use colors contextually appropriate based on their field/work, but EXPLAIN the reasoning and what research you did.
   - **Match Visual Identity**: Font families, typography, and layout patterns should also align with the topic's actual visual identity if discoverable, or be contextually appropriate based on research
   - **Document Your Theme**: When defining the theme, you MUST document:
     - Where you found the color information (specific URLs, portfolio link, brand website, etc.)
     - If no specific colors were found, explain what research you did and why you chose the colors based on context
     - Never use generic tech/industry color schemes without explicit research justification

**✅ Update tasks: Mark Phase 2 complete + Start Phase 3 in ONE call**

**Phase 3: Research and Content Planning** 📝
**Complete ALL steps in this phase, including ALL image downloads, before proceeding to Phase 4.**

1. **Batch Content Research**: Use `web_search` in BATCH MODE to thoroughly research the topic efficiently:
   ```
   use web_search with multiple queries ([topic] history background, [topic] key features characteristics, [topic] statistics data facts, [topic] significance importance impact)
   ```
   **ALL queries in ONE call.** Then use `web_scrape` to gather detailed information, facts, data, and insights. The more context you gather, the better you can select appropriate images.

2. **Create Content Outline** (MANDATORY): Develop a structured outline that maps out content for each slide. Focus on one main idea per slide. For each image needed, note the specific query. **CRITICAL**: Use your research context to create intelligent, context-aware image queries that are **TOPIC-SPECIFIC**, not generic:
   - **CORRECT APPROACH**: Always include the actual topic name, brand, product, person's name, or entity in your queries:
     - `"[actual topic name] [specific attribute]"`
     - `"[actual brand] [specific element]"`
     - `"[actual person name] [relevant context]"`
     - `"[actual location] [specific feature]"`
   - **WRONG APPROACH**: Generic category queries without the specific topic name (e.g., using "technology interface" instead of including the actual topic name, or "tropical destination" instead of including the actual location name)
   - **For companies/products**: Include the actual company/product name in queries (e.g., "[company name] headquarters", "[product name] interface")
   - **For people**: ALWAYS include the person's full name in the query along with relevant context
   - **For topics/locations**: ALWAYS include the topic/location name in the query along with specific attributes
   - Match image queries to the EXACT topic being researched, not just the category
   - Use specific names, brands, products, people, locations you discovered in research
   - **Document which slide needs which image** - you'll need this mapping in Phase 4

3. **Batch Image Search** (MANDATORY): Use `image_search` in BATCH MODE with ALL topic-specific queries:
   ```
   use image_search with multiple queries ([topic] exterior view, [topic] interior detail, [topic] key feature, [topic] overview context) and num_results 2
   ```
   **ALL queries in ONE call.** Results now include enriched metadata for each image:
   ```json
   {
     "batch_results": [{
       "query": "...",
       "images": [{
         "imageUrl": "https://...",
         "title": "Image title",
         "width": 1920,
         "height": 1080,
         "description": "Text extracted from the image",
         "source": "example.com"
       }, ...]
     }, ...]
   }
   ```
   - **TOPIC-SPECIFIC IMAGES REQUIRED**: Images MUST be specific to the actual topic/subject being researched, NOT generic category images
   - **For companies/products**: ALWAYS include the actual company/product name in every image query
   - **For people**: ALWAYS include the person's full name in every image query along with relevant context
   - **For topics/locations**: ALWAYS include the topic/location name in every image query along with specific attributes
   - Use context-aware queries based on your research that include the specific topic name/brand/product/person/location
   - Set `num_results=2` to get 2-3 relevant results per query for selection flexibility

4. **Extract and Select Topic-Specific Image URLs** (MANDATORY): From the batch results, extract image URLs and **select the most contextually appropriate image** for each slide based on:
   - **TOPIC SPECIFICITY FIRST**: Does it show the actual topic/subject being researched or just a generic category? Always prefer images that directly show the specific topic, brand, product, person, or entity over generic category images
   - **USE OCR TEXT FOR CONTEXT**: Check the `description` field - if it contains relevant text (brand names, product names, labels), this confirms the image is topic-specific
   - **USE DIMENSIONS FOR LAYOUT**: Check `width` and `height` to determine image orientation:
     - **Landscape (width > height)**: Best for full-width backgrounds, hero images, banner sections
     - **Portrait (height > width)**: Best for side panels, profile photos, vertical accent images
     - **Square-ish**: Flexible for various layouts
   - How well it matches the slide content and your research findings
   - How well it aligns with your research findings (specific names, brands, products discovered)
   - How well it fits the presentation theme and color scheme
   - Visual quality and relevance

5. **Single Command - Folder + All Downloads + Verify** (MANDATORY): Download ALL images in ONE chained command:
   ```bash
   mkdir -p presentations/images && wget "URL1" -O presentations/images/slide1_exterior.jpg && wget "URL2" -O presentations/images/slide2_interior.jpg && wget "URL3" -O presentations/images/slide3_detail.jpg && wget "URL4" -O presentations/images/slide4_overview.jpg && ls -lh presentations/images/
   ```
   **ONE COMMAND** creates folder, downloads ALL images, and verifies. NEVER use multiple separate commands!
   - **CRITICAL**: Do NOT use `2>/dev/null` to suppress errors - you need to see if downloads fail
   - **CRITICAL**: After the `ls -lh` command, VERIFY that ALL expected image files are present
   - **CRITICAL**: If any image download fails, you MUST retry or find alternative image URLs
   - **CRITICAL**: Count the files in `ls` output and ensure it matches the number of images you attempted to download
   - Use descriptive filenames that clearly identify the image's purpose (e.g., `slide1_intro_image.jpg`, `slide2_team_photo.jpg`)
   - Preserve or add appropriate file extensions (.jpg, .png, etc.) based on the image URL
   - If using `curl` instead of `wget`, use: `curl -L "URL" -o filename` (without suppressing errors)

6. **Document Image Mapping with Metadata** (MANDATORY): Create a clear mapping of slide number → image filename with layout info for reference in Phase 4:
   - Slide 1 → `slide1_exterior.jpg` (1920x1080, landscape, OCR: "Company Name")
   - Slide 2 → `slide2_interior.jpg` (800x1200, portrait, OCR: "Product Label")
   - Slide 3 → `slide3_team.jpg` (1000x1000, square, no text)
   - etc.
   - **INCLUDE METADATA**: For each image, note:
     - Dimensions (width x height) from image_search results
     - Orientation (landscape/portrait/square)
     - OCR text summary (if any relevant text was detected)
     - Planned placement (background, side panel, hero image, etc.)
   - **CRITICAL VERIFICATION**: After `ls -lh`, count the files and ensure the number matches the number of images you attempted to download
   - **CRITICAL VERIFICATION**: Check that ALL expected filenames appear in the `ls` output
   - **CRITICAL**: If any image is missing, you MUST retry the download or find alternative image URLs - do NOT proceed to Phase 4 with missing images
   - Confirm every expected image file exists and is accessible from the `ls` output

**✅ Update tasks: Mark Phase 3 complete + Start Phase 4 in ONE call**

**Phase 4: Slide Creation** (USE AS MANY IMAGES AS POSSIBLE)
**Only start after Phase 3 checkpoint - all images must be downloaded and verified.**

1. **Create Slides in PARALLEL** (MANDATORY FOR CUSTOM THEMES ONLY): Use the `create_slide` tool to create ALL slides simultaneously using parallel execution. **DO NOT create slides one-by-one sequentially** - create them all at once in parallel for efficiency:
   
   **🚨 CRITICAL - EXACT PARAMETER NAMES REQUIRED:**
   - **MUST use**: `presentation_name` (string) - Name of the presentation folder
   - **MUST use**: `slide_number` (integer) - Slide number starting from 1
   - **MUST use**: `slide_title` (string) - Title of this specific slide
   - **MUST use**: `content` (string) - HTML body content for the slide
   - **OPTIONAL**: `presentation_title` (string) - Main title of the presentation (defaults to "Presentation")
   - **❌ NEVER use**: `file_path` - This parameter does NOT exist! Use `presentation_name` instead.
   
   **Example correct call:**
   ```
   create_slide(
     presentation_name="my_presentation",
     slide_number=1,
     slide_title="Introduction",
     content="<div>...</div>",
     presentation_title="My Awesome Presentation"
   )
   ```
   
   - Prepare all slide content first (based on your outline from Phase 3)
   - Call `create_slide` for ALL slides in parallel (e.g., slide 1, 2, 3, 4, 5 all at once)
   - This dramatically speeds up presentation creation
   - All styling MUST be derived from the **custom color scheme and design elements** defined in Phase 2. Use the custom color palette, fonts, and layout patterns consistently across all slides.
   - **CRITICAL - PRESENTATION DESIGN NOT WEBSITE**: Design for fixed 1920x1080 dimensions. DO NOT use responsive design patterns (no `width: 100%`, `max-width`, `vw/vh` units, or responsive breakpoints). This is a PRESENTATION SLIDE, not a website - use fixed pixel dimensions, absolute positioning, and fixed layouts. **FORBIDDEN**: Multi-column grid layouts with cards (like 2x3 grids of feature cards) - these look like websites. Use centered, focused layouts with large content instead.

2. **Use Downloaded Images with Smart Placement**: For each slide that requires images, **MANDATORY**: Use the images that were downloaded in Phase 3. **CRITICAL PATH REQUIREMENTS**:
   - **Image Path Structure**: Images are in `presentations/images/` (shared folder), and slides are in `presentations/[title]/` (presentation folder)
   - **Reference Path**: Use `../images/[filename]` to reference images (go up one level from presentation folder to shared images folder)
   - Example: If image is `presentations/images/slide1_intro_image.jpg` and slide is `presentations/[presentation-title]/slide_01.html`, use path: `../images/slide1_intro_image.jpg`
   
   **🎯 IMAGE PLACEMENT BASED ON DIMENSIONS** (use metadata from Phase 3):
   - **Landscape Images (width > height)**: 
     - Use as full-width backgrounds with `width: 100%; object-fit: cover`
     - Or as hero images spanning 60-80% of slide width
     - Great for banner sections at top/bottom of slides
   - **Portrait Images (height > width)**:
     - Use in side panels (30-40% of slide width)
     - Or as accent images alongside text content
     - Never stretch to full width - looks distorted
   - **Square Images**:
     - Flexible - work well in grids or as centered focal points
     - Good for profile photos, logos, icons
   
   **🔤 USE OCR TEXT FOR CONTEXT**:
   - If `description` contains brand names, product names, or labels - this confirms the image is relevant
   - Use OCR text to inform caption text or surrounding content
   - If OCR reveals unexpected text (wrong brand, irrelevant content), consider using a different image
   
   - **CRITICAL REQUIREMENTS**:
     - **DO NOT skip images** - if a slide outline specified images, they must be included in the slide HTML
     - Use the exact filenames you verified in Phase 3 (e.g., `../images/slide1_intro_image.jpg`)
     - Include images in `<img>` tags within your slide HTML content
     - Match image dimensions to layout - don't force portrait images into landscape slots
     - If an image doesn't appear, verify the filename matches exactly (including extension) and the path is correct (`../images/` not `images/`)

**Final Phase: Deliver** 🎯

1. **Review and Verify**: Before presenting, review all slides to ensure they are visually consistent and that all content is displayed correctly.

2. **Deliver the Presentation**: Use the `complete` tool with the **first slide** (e.g., `presentations/[name]/slide_01.html`) attached to deliver the final, polished presentation to the user. **IMPORTANT**: Only attach the opening/first slide to keep the UI tidy - the presentation card will automatically appear and show the full presentation when any presentation slide file is attached.

### TYPOGRAPHY & ICONS

**Google Fonts (Inter) is pre-loaded** - All slides automatically use Inter font family for modern, clean typography. No need to load additional fonts unless specifically required.

**Icons & Graphics:**
- **Use emoji** for icons: 📊 📈 💡 🚀 ⚡ 🎯 ✅ ❤️ 👥 🌍 🏭 👤 🕐 🏆 etc.
- **Unicode symbols** for simple graphics: → ← ↑ ↓ • ✓ ✗ ⚡ ★
- **NO Font Awesome** - Use emoji or Unicode symbols instead
- For bullet points, use emoji or styled divs with Unicode symbols

**Typography Guidelines:**
- **Titles**: 48-72px (bold, weight: 700-900)
- **Subtitles**: 32-42px (semi-bold, weight: 600-700)
- **Headings**: 28-36px (semi-bold, weight: 600)
- **Body**: 20-24px (normal, weight: 400-500)
- **Small**: 16-18px (light, weight: 300-400)
- **Line Height**: 1.5-1.8 for readability

### DESIGN PRINCIPLES

**Visual Consistency:**
- Maintain consistent color scheme throughout entire presentation
- Use theme colors: Primary (backgrounds), Secondary (subtle backgrounds), Accent (highlights), Text (all text)
- Consistent spacing: 40-60px between major sections, 20-30px between related items

**Content Richness:**
- Include real data: specific numbers, percentages, metrics
- Add quotes & testimonials for credibility
- Use case examples to illustrate concepts
- Include emotional hooks and storytelling elements

**Layout Best Practices:**
- Focus on 1-2 main ideas per slide
- Limit to 3-5 bullet points max
- Use `overflow: hidden` on containers
- Always use `box-sizing: border-box` on containers with padding
- Embrace whitespace - don't fill every pixel
- **CRITICAL**: Use centered, focused layouts - NOT multi-column card grids (which look like websites)
- For multiple items: Use simple vertical lists or 2-3 large items side-by-side (NOT 6+ cards in grid)
- Think PowerPoint slide: Large title, centered content, minimal elements - NOT website feature sections

**Dimension Requirements:**
- Slide size: 1920x1080 pixels (16:9 aspect ratio)
- Container padding: Maximum 40px on all edges
- **CRITICAL**: Never add conflicting body styles - template already sets fixed dimensions
"""
)
class SandboxPresentationTool(SandboxToolsBase):
    """
    Per-slide HTML presentation tool for creating presentation slides.
    Each slide is created as a basic HTML document without predefined CSS styling.
    Users can include their own CSS styling inline or in style tags as needed.
    """
    
    def __init__(self, project_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.presentations_dir = "presentations"
        # Path to built-in templates (on the backend filesystem, not in sandbox)
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "presentations")
        self._metadata_locks: Dict[str, asyncio.Lock] = {}
        self._metadata_locks_guard = asyncio.Lock()


    async def _ensure_presentations_dir(self):
        """Ensure the presentations directory exists"""
        full_path = f"{self.workspace_path}/{self.presentations_dir}"
        try:
            await self.sandbox.fs.create_folder(full_path, "755")
        except:
            pass

    async def _ensure_shared_images_dir(self):
        """Ensure the shared presentations/images directory exists"""
        shared_images_path = f"{self.workspace_path}/{self.presentations_dir}/images"
        try:
            await self.sandbox.fs.create_folder(shared_images_path, "755")
        except:
            pass

    async def _ensure_presentation_dir(self, presentation_name: str):
        """Ensure a specific presentation directory exists"""
        safe_name = self._sanitize_filename(presentation_name)
        presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
        try:
            await self.sandbox.fs.create_folder(presentation_path, "755")
        except:
            pass
        return safe_name, presentation_path

    def _sanitize_filename(self, name: str) -> str:
        """Convert presentation name to safe filename"""
        return "".join(c for c in name if c.isalnum() or c in "-_").lower()

    def _normalize_identifier(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
        return normalized.strip("_")

    def _resolve_template_name(self, template_name: str) -> Optional[str]:
        requested = (template_name or "").strip()
        if not requested:
            return None

        direct_path = os.path.join(self.templates_dir, requested)
        if os.path.isdir(direct_path):
            return requested

        normalized_requested = {
            requested.lower(),
            self._normalize_identifier(requested),
            re.sub(r"[^a-z0-9]+", "", requested.lower()),
        }
        normalized_requested.discard("")

        for item in os.listdir(self.templates_dir):
            template_path = os.path.join(self.templates_dir, item)
            if not os.path.isdir(template_path):
                continue

            metadata = self._load_template_metadata(item)
            template_aliases = {
                item,
                metadata.get("title", ""),
                metadata.get("presentation_name", ""),
            }

            normalized_aliases = set()
            for alias in template_aliases:
                if not alias:
                    continue
                normalized_aliases.add(alias.lower())
                normalized_aliases.add(self._normalize_identifier(alias))
                normalized_aliases.add(re.sub(r"[^a-z0-9]+", "", alias.lower()))

            if normalized_requested & normalized_aliases:
                return item

        return requested

    async def _get_metadata_lock(self, presentation_path: str) -> asyncio.Lock:
        """Get/create a per-presentation lock to avoid metadata races across parallel slide writes."""
        async with self._metadata_locks_guard:
            lock = self._metadata_locks.get(presentation_path)
            if lock is None:
                lock = asyncio.Lock()
                self._metadata_locks[presentation_path] = lock
            return lock

    def _is_plain_slide_content(self, slide_content: str) -> bool:
        """
        Detect very plain content (just headings/paragraphs/lists) so we can auto-apply
        a visual baseline instead of rendering bare text-only slides.
        """
        lowered = slide_content.lower()
        if "style=" in lowered or "<style" in lowered:
            return False

        visual_markers = ("<img", "<svg", "<canvas", "<video", "<iframe", "<table", "<chart")
        if any(marker in lowered for marker in visual_markers):
            return False

        tags = re.findall(r"<\s*/?\s*([a-z0-9-]+)", lowered)
        if not tags:
            return True

        plain_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "strong", "em", "b", "i", "a", "span", "br", "small"}
        return all(tag in plain_tags for tag in tags)

    def _validate_slide_content_workflow(self, slide_content: str) -> Optional[str]:
        lowered = (slide_content or "").lower()

        placeholder_markers = [
            "presentation template",
            "welcome to brightpath",
            "brightpath",
            "yourwebsite.org",
            "lorem ipsum",
            "slidekit",
            "presentation system 2025",
            "elevator pitch template",
            "elevator pitch example",
        ]
        placeholder_hits = [marker for marker in placeholder_markers if marker in lowered]
        if placeholder_hits:
            return (
                "Slide content rejected because template placeholder text is still present "
                f"({', '.join(sorted(set(placeholder_hits)))}). Replace placeholder copy with researched content."
            )

        instruction_hits = []
        instruction_patterns = {
            "example copy": r"\bexample\s*:",
            "generic instruction": r"\b(?:this slide|in this section|could include|should include)\b",
            "placeholder investor phrasing": r"\b(?:highlight key|your startup|your company|relevant achievements)\b",
        }
        for label, pattern in instruction_patterns.items():
            if re.search(pattern, lowered):
                instruction_hits.append(label)

        if instruction_hits:
            return (
                "Slide content rejected because it still contains instruction/example placeholder copy "
                f"({', '.join(sorted(set(instruction_hits)))}). Replace it with researched, presentation-ready content."
            )

        class_attr_count = len(re.findall(r"\bclass\s*=", slide_content, flags=re.IGNORECASE))
        inline_style_count = len(re.findall(r"\bstyle\s*=", slide_content, flags=re.IGNORECASE))
        has_style_block = "<style" in lowered

        if class_attr_count >= 4 and not has_style_block and inline_style_count < 2:
            return (
                "Slide content rejected because it relies on CSS classes without any accompanying styles. "
                "This usually means template HTML was copied directly into create_slide. For template-based presentations, "
                "call load_template_design with presentation_name first, then create fresh slide content with create_slide so the deck inherits "
                "the initialized template design system. Use populate_template_slide only for exact DOM-preserving edits. "
                "For custom slides, include a <style> block or inline styles so the slide renders correctly."
            )

        return None

    def _validate_slide_assets(self, slide_content: str) -> Optional[str]:
        soup = BeautifulSoup(slide_content or "", "html.parser")
        disallowed_sources: List[str] = []

        for image in soup.find_all("img"):
            src = (image.get("src") or "").strip()
            if not src:
                continue

            lowered = src.lower()
            if lowered.startswith(("http://", "https://", "data:", "blob:")):
                disallowed_sources.append(src)

        if not disallowed_sources:
            return None

        preview = ", ".join(
            f"{src[:80]}{'...' if len(src) > 80 else ''}"
            for src in disallowed_sources[:2]
        )

        return (
            "Slide content rejected because custom presentation slides must use workspace image assets, "
            "not hotlinked public URLs. Download topic-specific images into presentations/images/ and "
            "reference them via ../images/... or use generated workspace files first. "
            f"Found external image source(s): {preview}"
        )

    def _should_auto_design_slide(self, slide_content: str) -> bool:
        lowered = (slide_content or "").lower()
        if "<style" in lowered:
            return False

        class_attr_count = len(re.findall(r"\bclass\s*=", slide_content, flags=re.IGNORECASE))
        inline_style_count = len(re.findall(r"\bstyle\s*=", slide_content, flags=re.IGNORECASE))

        if class_attr_count >= 3 or inline_style_count >= 6:
            return False

        tags = re.findall(r"<\s*/?\s*([a-z0-9-]+)", lowered)
        if not tags:
            return True

        simple_tags = {
            "article",
            "aside",
            "b",
            "blockquote",
            "br",
            "div",
            "em",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "i",
            "img",
            "li",
            "main",
            "ol",
            "p",
            "section",
            "small",
            "span",
            "strong",
            "sub",
            "sup",
            "ul",
        }
        return all(tag in simple_tags for tag in tags)

    def _is_instruction_like_text(self, value: str) -> bool:
        normalized = re.sub(r"\s+", " ", (value or "").strip().lower())
        if not normalized:
            return False

        patterns = [
            r"^example\s*:",
            r"\bfor example\b",
            r"^this slide\b",
            r"^in this section\b",
            r"\bcould include\b",
            r"\bshould include\b",
            r"\bhighlight key\b",
            r"\byour startup\b",
            r"\byour company\b",
            r"\brelevant achievements\b",
            r"\bplaceholder\b",
            r"\binsert your\b",
            r"\bslidekit\b",
            r"\bpresentation system 2025\b",
        ]
        return any(re.search(pattern, normalized) for pattern in patterns)

    def _split_into_sentences(self, values: List[str]) -> List[str]:
        sentences: List[str] = []
        for value in values:
            for sentence in re.split(r"(?<=[.!?;])\s+|\n+", value or ""):
                cleaned = re.sub(r"\s+", " ", sentence).strip(" -•\t\r\n")
                if not cleaned or self._is_instruction_like_text(cleaned):
                    continue
                sentences.append(cleaned)
        return self._dedupe_text_items(sentences)

    def _extract_structured_brief_sections(self, slide_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(slide_content or "", "html.parser")
        for tag in soup.find_all(["style", "script", "noscript"]):
            tag.decompose()

        single_labels = {
            "title": "title",
            "slide title": "title",
            "headline": "title",
            "kicker": "kicker",
            "thesis": "lead",
            "lead": "lead",
            "objective": "lead",
            "narrative": "lead",
            "summary": "lead",
            "visual brief": "visual_brief",
            "visual": "visual_brief",
            "image prompt": "visual_brief",
        }
        list_labels = {
            "evidence": "evidence",
            "supporting points": "evidence",
            "proof points": "evidence",
            "key points": "key_points",
            "bullets": "key_points",
            "metrics": "metrics",
            "stats": "metrics",
        }
        sections: Dict[str, Any] = {
            "title": "",
            "kicker": "",
            "lead": "",
            "visual_brief": "",
            "evidence": [],
            "key_points": [],
            "metrics": [],
        }

        current_list_key: Optional[str] = None
        for raw_line in soup.get_text("\n", strip=False).splitlines():
            line = re.sub(r"\s+", " ", unquote(raw_line or "")).strip()
            if not line:
                continue

            bullet_match = re.match(r"^[•*\-–]\s*(.+)$", line)
            if bullet_match and current_list_key:
                candidate = bullet_match.group(1).strip()
                if candidate and not self._is_instruction_like_text(candidate):
                    sections[current_list_key].append(candidate)
                continue

            label_match = re.match(r"^([A-Za-z][A-Za-z\s/&-]{1,40}):\s*(.*)$", line)
            if label_match:
                label = label_match.group(1).strip().lower()
                remainder = label_match.group(2).strip()

                if label in single_labels:
                    current_list_key = None
                    if remainder and not self._is_instruction_like_text(remainder):
                        sections[single_labels[label]] = remainder
                    continue

                if label in list_labels:
                    current_list_key = list_labels[label]
                    if remainder and not self._is_instruction_like_text(remainder):
                        sections[current_list_key].append(remainder)
                    continue

            if current_list_key and not self._is_instruction_like_text(line):
                sections[current_list_key].append(line)

        for key, value in sections.items():
            if isinstance(value, list):
                sections[key] = self._dedupe_text_items(value)
        return sections

    def _extract_metric_phrases(self, values: List[str]) -> List[str]:
        metric_candidates: List[str] = []
        metric_pattern = re.compile(
            r"(\$?\d[\d,]*(?:\.\d+)?(?:\+|%|x)?|\b\d[\d,]*(?:\.\d+)?\s*(?:million|billion|thousand|users|founders|customers|partners|markets)\b)",
            flags=re.IGNORECASE,
        )
        for value in values:
            if not value or self._is_instruction_like_text(value):
                continue
            if metric_pattern.search(value):
                metric_candidates.append(value)
        return self._dedupe_text_items(metric_candidates)[:3]

    def _dedupe_text_items(self, values: List[str]) -> List[str]:
        seen = set()
        deduped: List[str] = []
        for value in values:
            normalized = re.sub(r"\s+", " ", (value or "").strip())
            if not normalized:
                continue
            if self._is_instruction_like_text(normalized):
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
        return deduped

    def _extract_slide_semantics(self, slide_content: str, slide_title: str) -> Dict[str, object]:
        soup = BeautifulSoup(slide_content or "", "html.parser")
        for tag in soup.find_all(["style", "script", "noscript"]):
            tag.decompose()
        structured_sections = self._extract_structured_brief_sections(slide_content)

        def clean_text(value: str) -> str:
            return re.sub(r"\s+", " ", unquote(value or "")).strip()

        headings = self._dedupe_text_items(
            [clean_text(tag.get_text(" ", strip=True)) for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
        )
        paragraphs = self._dedupe_text_items(
            [clean_text(tag.get_text(" ", strip=True)) for tag in soup.find_all("p")]
        )
        bullets = self._dedupe_text_items(
            [clean_text(tag.get_text(" ", strip=True)) for tag in soup.find_all("li")]
        )
        quotes = self._dedupe_text_items(
            [clean_text(tag.get_text(" ", strip=True)) for tag in soup.find_all("blockquote")]
        )

        images: List[Dict[str, str]] = []
        seen_images = set()
        for tag in soup.find_all("img"):
            src = clean_text(tag.get("src", ""))
            alt = clean_text(tag.get("alt", ""))
            if not src:
                continue
            lowered = src.lower()
            if lowered.startswith(("http://", "https://", "data:", "blob:")):
                continue
            if src in seen_images:
                continue
            seen_images.add(src)
            images.append({"src": src, "alt": alt})

        fallback_texts: List[str] = []
        for node in soup.find_all(string=True):
            if not isinstance(node, NavigableString):
                continue
            parent = node.parent
            if parent and parent.name in {"style", "script", "title", "head"}:
                continue

            text = clean_text(str(node))
            if not text or len(text) < 6:
                continue

            fallback_texts.append(text)

        fallback_texts = self._dedupe_text_items(fallback_texts)
        title_text = (
            structured_sections.get("title")
            or (headings[0] if headings else "")
            or clean_text(slide_title)
            or (fallback_texts[0] if fallback_texts else "Slide")
        )

        sentence_pool = self._split_into_sentences(paragraphs + quotes + fallback_texts)
        narrative_pool = self._dedupe_text_items(
            ([structured_sections.get("lead")] if structured_sections.get("lead") else [])
            + paragraphs
            + quotes
            + sentence_pool
            + fallback_texts
        )
        narrative_pool = [item for item in narrative_pool if item.lower() != title_text.lower()]

        lead = structured_sections.get("lead") or (narrative_pool[0] if narrative_pool else "")
        supporting_candidates = self._dedupe_text_items(
            structured_sections.get("evidence", [])
            + structured_sections.get("key_points", [])
            + bullets
            + sentence_pool
            + narrative_pool[1:]
        )
        supporting = [item for item in supporting_candidates if item.lower() != (lead or "").lower()][:4]

        key_points = self._dedupe_text_items(
            structured_sections.get("key_points", [])
            + structured_sections.get("evidence", [])
            + bullets
            + supporting
        )[:5]
        if not key_points:
            key_points = [item for item in supporting[:4] if len(item) <= 180]

        if not supporting and lead:
            supporting = [item for item in self._split_into_sentences([lead]) if item.lower() != lead.lower()][:3]

        kicker = ""
        if structured_sections.get("kicker"):
            kicker = structured_sections["kicker"]
        elif len(headings) > 1:
            kicker = headings[1]
        elif slide_title and clean_text(slide_title).lower() != title_text.lower():
            kicker = clean_text(slide_title)

        metrics = self._dedupe_text_items(
            structured_sections.get("metrics", []) + self._extract_metric_phrases(key_points + supporting + narrative_pool)
        )[:3]

        return {
            "title": title_text,
            "kicker": kicker,
            "lead": lead,
            "supporting": supporting,
            "key_points": key_points,
            "metrics": metrics,
            "visual_brief": structured_sections.get("visual_brief") or "",
            "image": images[0] if images else None,
        }

    def _normalize_hex_color(self, value: str) -> Optional[str]:
        if not value:
            return None

        candidate = value.strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", candidate):
            return None

        if len(candidate) == 4:
            candidate = "#" + "".join(char * 2 for char in candidate[1:])
        return candidate.lower()

    def _hex_to_rgb(self, color: str) -> tuple[int, int, int]:
        normalized = self._normalize_hex_color(color) or "#000000"
        return (
            int(normalized[1:3], 16),
            int(normalized[3:5], 16),
            int(normalized[5:7], 16),
        )

    def _hex_to_rgba(self, color: str, alpha: float) -> str:
        red, green, blue = self._hex_to_rgb(color)
        return f"rgba({red}, {green}, {blue}, {alpha})"

    def _color_luminance(self, color: str) -> float:
        red, green, blue = self._hex_to_rgb(color)
        return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255

    def _is_neutral_color(self, color: str) -> bool:
        red, green, blue = self._hex_to_rgb(color)
        return max(red, green, blue) - min(red, green, blue) < 28

    def _pick_font_family(self, fonts: List[str]) -> str:
        for font in fonts:
            if not font:
                continue

            query_match = re.search(r"family=([^:&]+)", font)
            if query_match:
                family = query_match.group(1).replace("+", " ").split(":")[0].strip()
                if family:
                    return f"'{family}', 'Inter', sans-serif"

            cleaned = re.sub(r"^@import\s+url\(.+?\)$", "", font).strip().strip("'\"")
            if cleaned and "http" not in cleaned and len(cleaned) < 48:
                family = cleaned.split(",")[0].strip().strip("'\"")
                if family:
                    return f"'{family}', 'Inter', sans-serif"

        return "'Inter', sans-serif"

    def _build_theme_palette(self, colors: List[str], seed_text: str) -> Dict[str, str]:
        curated_palettes = [
            {
                "background": "#0f172a",
                "surface": "#172554",
                "accent": "#38bdf8",
                "accent_secondary": "#8b5cf6",
                "text": "#f8fafc",
                "muted": "#cbd5e1",
            },
            {
                "background": "#111827",
                "surface": "#1f2937",
                "accent": "#f97316",
                "accent_secondary": "#fb7185",
                "text": "#f9fafb",
                "muted": "#d1d5db",
            },
            {
                "background": "#052e2b",
                "surface": "#0f3f3b",
                "accent": "#34d399",
                "accent_secondary": "#2dd4bf",
                "text": "#ecfeff",
                "muted": "#cce6e6",
            },
        ]

        fallback = curated_palettes[sum(ord(char) for char in seed_text or "ventureverse") % len(curated_palettes)]
        normalized_colors = []
        for color in colors:
            normalized = self._normalize_hex_color(color)
            if normalized and normalized not in normalized_colors:
                normalized_colors.append(normalized)

        if len(normalized_colors) < 3:
            return fallback

        darkest = min(normalized_colors, key=self._color_luminance)
        lightest = max(normalized_colors, key=self._color_luminance)
        remaining = [color for color in normalized_colors if color not in {darkest, lightest}]
        vivid_accents = [color for color in remaining if not self._is_neutral_color(color)]

        surface = next((color for color in remaining if color != darkest), fallback["surface"])
        accent = vivid_accents[0] if vivid_accents else fallback["accent"]
        accent_secondary = vivid_accents[1] if len(vivid_accents) > 1 else fallback["accent_secondary"]

        return {
            "background": darkest,
            "surface": surface,
            "accent": accent,
            "accent_secondary": accent_secondary,
            "text": lightest,
            "muted": fallback["muted"] if self._color_luminance(lightest) < 0.4 else "#cbd5e1",
        }

    def _list_template_assets(self, template_name: str) -> List[str]:
        template_path = os.path.join(self.templates_dir, template_name)
        if not os.path.isdir(template_path):
            return []

        asset_paths: List[str] = []
        for root, _, files in os.walk(template_path):
            for file_name in files:
                if Path(file_name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                    continue
                relative_path = os.path.relpath(os.path.join(root, file_name), template_path).replace("\\", "/")
                if relative_path.lower() in {
                    "image.png",
                    "image.jpg",
                    "image.jpeg",
                    "preview.png",
                    "preview.jpg",
                    "preview.jpeg",
                    "thumbnail.png",
                    "thumbnail.jpg",
                    "thumbnail.jpeg",
                }:
                    continue
                asset_paths.append(relative_path)

        return sorted(asset_paths)

    def _choose_template_background_asset(self, assets: List[str]) -> Optional[str]:
        if not assets:
            return None

        preferred_keywords = ("gradient", "background", "hero", "cover", "texture", "bg")
        scored_assets = []
        for asset in assets:
            lower = asset.lower()
            if lower in {"image.png", "image.jpg", "image.jpeg", "preview.png", "preview.jpg", "preview.jpeg"}:
                continue
            score = 100
            for index, keyword in enumerate(preferred_keywords):
                if keyword in lower:
                    score = index
                    break
            scored_assets.append((score, asset))

        if not scored_assets:
            return None

        scored_assets.sort(key=lambda item: (item[0], item[1]))
        return scored_assets[0][1]

    async def _load_presentation_theme_context(
        self,
        presentation_path: str,
        presentation_name: str,
        presentation_title: str,
    ) -> Dict[str, Any]:
        metadata = await self._load_presentation_metadata(presentation_path)
        design_system = metadata.get("template_design_system") or {}
        palette = self._build_theme_palette(
            design_system.get("color_palette", []) if isinstance(design_system, dict) else [],
            presentation_title or presentation_name,
        )
        font_family = self._pick_font_family(
            design_system.get("fonts", []) if isinstance(design_system, dict) else []
        )
        template_assets = metadata.get("template_assets") or []
        background_asset = self._choose_template_background_asset(template_assets)

        return {
            "presentation_name": presentation_name,
            "presentation_title": presentation_title,
            "template_source": metadata.get("template_source"),
            "template_reference_dir": metadata.get("template_reference_dir") or ".template_reference",
            "template_slide_count": int(metadata.get("template_slide_count") or 0),
            "deck_title": metadata.get("title") or presentation_title or presentation_name,
            "font_family": font_family,
            "palette": palette,
            "background_asset": background_asset,
        }

    def _is_template_placeholder_text(self, value: str) -> bool:
        normalized = re.sub(r"\s+", " ", (value or "").strip().lower())
        if not normalized:
            return False

        placeholder_markers = [
            "lorem ipsum",
            "yourwebsite.org",
            "slidekit",
            "presentation system 2025",
            "elevator pitch template",
            "elevator pitch example",
            "brightpath",
            "this document sets out a full creative brief",
            "in this project, we will design and ship a new brand design system",
            "we'll define the primary goal of the project",
            "gradient background",
        ]
        return any(marker in normalized for marker in placeholder_markers) or self._is_instruction_like_text(normalized)

    def _should_omit_slide_visual(self, slide_content: str, semantics: Dict[str, object]) -> bool:
        haystacks = [
            slide_content or "",
            str(semantics.get("visual_brief") or ""),
            str(semantics.get("lead") or ""),
        ]
        patterns = [
            r"\bno images?\b",
            r"\bwithout images?\b",
            r"\bno visual(?:s)?\b",
            r"\bwithout visual(?:s)?\b",
            r"\btext[- ]only\b",
            r"\bskip (?:the )?images?\b",
            r"\bdo not add images?\b",
            r"\bdo not use images?\b",
            r"\bremove images?\b",
            r"\bimage\s*:\s*none\b",
            r"\bvisual\s*:\s*none\b",
        ]
        for haystack in haystacks:
            lowered = (haystack or "").lower()
            if any(re.search(pattern, lowered) for pattern in patterns):
                return True
        return False

    def _extract_primary_domain(self, values: List[str]) -> Optional[str]:
        for value in values:
            if not value:
                continue
            match = re.search(
                r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})",
                value,
                flags=re.IGNORECASE,
            )
            if match:
                return match.group(1).lower()
        return None

    def _derive_template_branding(
        self,
        semantics: Dict[str, object],
        theme_context: Dict[str, Any],
        slide_content: str,
    ) -> Dict[str, str]:
        deck_title = str(theme_context.get("deck_title") or "")
        subject_hint = self._extract_subject_hint(deck_title, str(semantics.get("title") or ""))
        domain = self._extract_primary_domain([
            slide_content,
            str(semantics.get("lead") or ""),
            str(semantics.get("title") or ""),
            deck_title,
        ])

        brand = re.sub(
            r"\b(presentation|investor|pitch|deck|slides?|template|startup|company|overview)\b",
            " ",
            deck_title,
            flags=re.IGNORECASE,
        )
        brand = re.sub(r"\s+", " ", brand).strip(" -_:")
        if not brand:
            brand = subject_hint
        if not brand and domain:
            brand = domain.split(".")[0].replace("-", " ").replace("_", " ").title()

        return {
            "brand": brand or deck_title or "Presentation",
            "domain": domain or "",
            "year": str(datetime.now().year),
        }

    def _shorten_template_label(self, value: str, fallback: str = "Insight") -> str:
        cleaned = re.sub(r"\s+", " ", (value or "").strip()).strip(" -:;,.")
        if not cleaned:
            return fallback

        cleaned = re.sub(r"^[0-9$%x+.,\s-]+", "", cleaned).strip() or cleaned
        if ":" in cleaned:
            cleaned = cleaned.split(":", 1)[0].strip() or cleaned
        if len(cleaned) > 42:
            words = cleaned.split()
            cleaned = " ".join(words[:5]).strip()
        return cleaned[:42].strip() or fallback

    def _truncate_template_copy(self, value: str, max_chars: int = 180) -> str:
        cleaned = re.sub(r"\s+", " ", (value or "").strip())
        if len(cleaned) <= max_chars:
            return cleaned
        truncated = cleaned[: max_chars - 1].rsplit(" ", 1)[0].strip()
        return truncated or cleaned[:max_chars].strip()

    def _set_element_text(self, element: Any, value: str) -> None:
        if element is None:
            return
        element.clear()
        element.append(value)

    def _hide_template_element(self, element: Any) -> None:
        if element is None:
            return
        existing = (element.get("style") or "").strip().rstrip(";")
        hide_style = "display: none !important"
        element["style"] = f"{existing}; {hide_style}" if existing else hide_style

    def _select_template_reference_slide_number(self, requested_slide: int, template_slide_count: int) -> int:
        if template_slide_count <= 0:
            return requested_slide
        if requested_slide <= template_slide_count:
            return requested_slide
        if template_slide_count <= 2:
            return template_slide_count
        reusable_span = template_slide_count - 1
        return 2 + ((requested_slide - 2) % reusable_span)

    async def _load_template_reference_html(
        self,
        presentation_path: str,
        slide_number: int,
        theme_context: Dict[str, Any],
    ) -> Optional[str]:
        reference_dir = str(theme_context.get("template_reference_dir") or ".template_reference")
        template_slide_count = int(theme_context.get("template_slide_count") or 0)
        reference_slide_number = self._select_template_reference_slide_number(slide_number, template_slide_count)
        slide_filename = f"slide_{reference_slide_number:02d}.html"
        slide_path = f"{presentation_path}/{reference_dir}/{slide_filename}"
        try:
            content = await self.sandbox.fs.download_file(slide_path)
        except Exception:
            return None
        return content.decode() if isinstance(content, bytes) else str(content)

    async def _render_template_reference_slide(
        self,
        presentation_path: str,
        slide_content: str,
        semantics: Dict[str, object],
        theme_context: Dict[str, Any],
        slide_number: int,
        slide_title: str,
        presentation_title: str,
        omit_visual: bool,
    ) -> Optional[str]:
        reference_html = await self._load_template_reference_html(
            presentation_path=presentation_path,
            slide_number=slide_number,
            theme_context=theme_context,
        )
        if not reference_html:
            return None

        soup = BeautifulSoup(reference_html, "html.parser")
        branding = self._derive_template_branding(semantics, theme_context, slide_content)
        title_text = str(semantics.get("title") or slide_title or "Slide").strip()
        lead_text = self._truncate_template_copy(str(semantics.get("lead") or title_text), 220)
        supporting = [self._truncate_template_copy(str(item), 180) for item in semantics.get("supporting", []) if item]
        key_points = [self._truncate_template_copy(str(item), 120) for item in semantics.get("key_points", []) if item]
        metrics = [self._truncate_template_copy(str(item), 120) for item in semantics.get("metrics", []) if item]

        title_labels = [title_text] + [self._shorten_template_label(item) for item in (key_points + metrics + supporting)]
        body_copy = [lead_text] + supporting + key_points + metrics
        body_copy = [item for item in body_copy if item]
        if not body_copy:
            body_copy = [lead_text]

        title_queue = title_labels.copy()
        body_queue = body_copy.copy()

        def next_title(default: str = title_text) -> str:
            return title_queue.pop(0) if title_queue else default

        def next_body(default: str = lead_text) -> str:
            return body_queue.pop(0) if body_queue else default

        def assign_selectors(selectors: List[str], values: List[str], fallback_hide: bool = False) -> None:
            used: set[int] = set()
            queue = [value for value in values if value]
            for selector in selectors:
                for element in soup.select(selector):
                    marker = id(element)
                    if marker in used:
                        continue
                    used.add(marker)
                    if queue:
                        self._set_element_text(element, queue.pop(0))
                    elif fallback_hide:
                        self._hide_template_element(element)

        # Preserve well-known template framing while replacing placeholder copy.
        assign_selectors([".brand"], [branding["brand"]])
        assign_selectors([".company-name"], [branding["brand"]], fallback_hide=False)
        assign_selectors([".year"], [branding["year"]])
        assign_selectors([".website"], [branding["domain"]], fallback_hide=not bool(branding["domain"]))
        assign_selectors([".slide-number", ".section-number"], [str(slide_number)])

        cards = soup.select(".card")
        if cards:
            card_items = key_points or supporting or metrics or [lead_text]
            for index, card in enumerate(cards):
                item = card_items[index] if index < len(card_items) else ""
                title_el = card.select_one(".card-title")
                text_el = card.select_one(".card-text")
                if title_el:
                    self._set_element_text(title_el, self._shorten_template_label(item or f"Point {index + 1}", fallback=f"Point {index + 1}"))
                if text_el:
                    self._set_element_text(text_el, self._truncate_template_copy(item or lead_text, 140))

        index_items = soup.select(".index-item")
        if index_items:
            outline_items = [next_title()] + [self._shorten_template_label(item) for item in (key_points + supporting)]
            for index, item in enumerate(index_items, start=1):
                title_el = item.select_one(".index-title")
                number_el = item.select_one(".index-number")
                if title_el:
                    label = outline_items[index - 1] if index - 1 < len(outline_items) else f"Section {index}"
                    self._set_element_text(title_el, label)
                if number_el:
                    self._set_element_text(number_el, str(index))

        main_title = soup.select_one(".main-title")
        if main_title:
            self._set_element_text(main_title, next_title())

        assign_selectors(
            [
                ".subtitle",
                ".section-heading",
                ".description-text",
                ".green-box-text",
                ".purple-box-title",
                ".purple-box-text",
                ".text-paragraph",
                ".top-text-box",
                ".section-description",
                ".overlay-text",
            ],
            [next_body() for _ in range(8)],
        )

        # Replace any lingering placeholder nodes with remaining researched content.
        replacement_pool = [item for item in ([next_title()] + body_queue + title_queue) if item]
        for node in soup.find_all(string=True):
            if not isinstance(node, NavigableString):
                continue
            parent = node.parent
            if parent and parent.name in {"style", "script", "title", "head"}:
                continue
            current = re.sub(r"\s+", " ", str(node).strip())
            if not current or not self._is_template_placeholder_text(current):
                continue
            if replacement_pool:
                node.replace_with(replacement_pool.pop(0))

        visual_src = None
        image = semantics.get("image") if isinstance(semantics.get("image"), dict) else None
        if image and (image.get("src") or "").strip():
            visual_src = (image.get("src") or "").strip()
        elif not omit_visual:
            visual_prompt = self._build_slide_visual_prompt(
                semantics=semantics,
                layout_variant=self._choose_layout_variant(semantics, slide_number),
                theme_context=theme_context,
            )
            visual_src = await self._generate_slide_visual_asset(
                prompt=visual_prompt,
                presentation_name=str(theme_context.get("presentation_name") or presentation_title),
                slide_number=slide_number,
            )

        image_tags = [
            image_tag for image_tag in soup.find_all("img")
            if "logo" not in ((image_tag.get("alt") or "") + " " + (image_tag.get("src") or "")).lower()
        ]

        if omit_visual:
            for image_tag in image_tags:
                hide_target = image_tag
                for ancestor in image_tag.parents:
                    if getattr(ancestor, "name", None) in {"div", "figure", "section"}:
                        classes = " ".join(ancestor.get("class", []))
                        if any(token in classes.lower() for token in ("image", "photo", "portrait", "visual", "media", "background", "side")):
                            hide_target = ancestor
                            break
                self._hide_template_element(hide_target)
        elif visual_src:
            for image_tag in image_tags:
                image_tag["src"] = visual_src
                image_tag["alt"] = title_text

        if soup.title:
            soup.title.string = f"{presentation_title or branding['brand']} - Slide {slide_number}"

        preserved_assets: List[str] = []
        for tag in soup.select("head link[rel='stylesheet'], head script[src], head style"):
            serialized = str(tag).strip()
            if serialized:
                preserved_assets.append(serialized)

        body = soup.body or soup
        return "".join(preserved_assets + [str(child) for child in body.contents])

    def _choose_layout_variant(self, semantics: Dict[str, object], slide_number: int) -> str:
        title = str(semantics.get("title") or "").lower()
        key_points = semantics.get("key_points", []) or []
        metrics = semantics.get("metrics", []) or []

        if slide_number == 1 or any(token in title for token in ("title", "cover", "welcome", "intro")):
            return "cover"
        if any(token in title for token in ("timeline", "roadmap", "milestone", "phases", "journey")):
            return "timeline"
        if any(token in title for token in ("thank", "closing", "next steps", "contact")):
            return "closing"
        if metrics and any(token in title for token in ("traction", "market", "growth", "business model", "ask", "financial", "opportunity")):
            return "metrics"
        if len(key_points) >= 4:
            return "bullet_grid"
        return "split"

    def _extract_subject_hint(self, deck_title: str, slide_title: str) -> str:
        source = (deck_title or slide_title or "the subject").strip()
        source = re.sub(
            r"\b(investor|pitch|deck|presentation|slides|template|strategy|overview|premium|black)\b",
            " ",
            source,
            flags=re.IGNORECASE,
        )
        source = re.sub(r"\s+", " ", source).strip(" -_:")
        return source or slide_title or deck_title or "the subject"

    def _build_metric_cards(self, metrics: List[str]) -> List[Dict[str, str]]:
        cards: List[Dict[str, str]] = []
        for metric in metrics[:3]:
            display_match = re.search(
                r"(\$?\d[\d,]*(?:\.\d+)?(?:\+|%|x)?|\b\d[\d,]*(?:\.\d+)?\s*(?:million|billion|thousand)\b)",
                metric,
                flags=re.IGNORECASE,
            )
            if display_match:
                display = display_match.group(1).strip()
                label = metric.replace(display_match.group(1), "", 1).strip(" :-,")
                label = label or metric
            else:
                parts = metric.split(" ", 1)
                display = parts[0]
                label = parts[1] if len(parts) > 1 else metric
            cards.append({"display": display, "label": label})
        return cards

    def _build_slide_scene_direction(
        self,
        title: str,
        layout_variant: str,
        subject_hint: str,
        key_points: List[str],
        metrics: List[str],
    ) -> str:
        title_lower = title.lower()
        keyword_map = {
            "cover": (
                "Create a premium hero scene centered on the subject with a strong focal object or environment. "
                "Do not generate letters, initials, monograms, or faux logos."
            ),
            "about": (
                "Show the real-world context of the company or subject: founders, workspace, city context, ecosystem, or product environment. "
                "Avoid generic stock boardroom compositions unless the slide is explicitly about meetings."
            ),
            "team": (
                "Show an editorial team or leadership scene with confident people, strong human presence, and a modern working environment."
            ),
            "mission": (
                "Show an aspirational mission-driven scene with founders, community, ambition, and momentum. Emphasize people and purpose."
            ),
            "values": (
                "Show community, mentorship, collaboration, and value creation in action rather than abstract shapes."
            ),
            "service": (
                "Show the product or service world through concrete entrepreneurial scenes, venture tooling, workshops, founder support, or platform usage."
            ),
            "solution": (
                "Show the proposed solution as a concrete scene: founders using AI tools, mentorship, venture execution, or startup-building moments."
            ),
            "product": (
                "Show the product or platform in context with people using it. Avoid unreadable UI screenshots; instead use cinematic interface-glow cues around real usage."
            ),
            "market": (
                "Show market scale and network effects through a global venture ecosystem scene, maps, flows, city clusters, investors, and startup activity."
            ),
            "financial": (
                "Show financial performance through premium data sculpture, capital flows, charts made physical, or an investor context scene. Avoid plain office meetings."
            ),
            "traction": (
                "Show growth and traction through momentum, product adoption, investor interest, founder activity, and data-informed movement."
            ),
            "roadmap": (
                "Show a literal forward path, phased journey, milestones, or launch sequence with clear progression."
            ),
            "timeline": (
                "Show a literal forward path, phased journey, milestones, or launch sequence with clear progression."
            ),
            "closing": (
                "Show an aspirational closing moment with confidence, forward motion, and a clear next-step energy."
            ),
        }

        if layout_variant == "cover":
            return keyword_map["cover"]
        if layout_variant == "timeline":
            return keyword_map["timeline"]
        if layout_variant == "closing":
            return keyword_map["closing"]
        if layout_variant == "metrics":
            return keyword_map["financial"]

        title_keyword_groups = [
            (("about", "overview", "who we are", "company"), "about"),
            (("team", "leadership", "founder"), "team"),
            (("mission", "vision"), "mission"),
            (("values", "community"), "values"),
            (("service", "offered", "platform", "product"), "service"),
            (("solution", "approach"), "solution"),
            (("market", "opportunity", "position"), "market"),
            (("financial", "revenue", "economics", "business model", "ask"), "financial"),
            (("traction", "growth", "adoption"), "traction"),
            (("roadmap", "timeline", "milestone"), "roadmap"),
        ]
        for keywords, scene_key in title_keyword_groups:
            if any(keyword in title_lower for keyword in keywords):
                return keyword_map[scene_key]

        if metrics:
            return keyword_map["financial"]
        if any("founder" in point.lower() or "community" in point.lower() for point in key_points):
            return keyword_map["mission"]

        return (
            f"Show a subject-specific editorial scene about {subject_hint} with real-world context, people or environment, "
            "and a distinct focal subject. Avoid generic office fillers and abstract placeholder visuals."
        )

    def _build_slide_visual_prompt(
        self,
        semantics: Dict[str, object],
        layout_variant: str,
        theme_context: Dict[str, Any],
    ) -> str:
        title = str(semantics.get("title") or "Presentation Slide").strip()
        lead = str(semantics.get("lead") or "").strip()
        key_points = [str(item).strip() for item in semantics.get("key_points", [])[:4] if item]
        metrics = [str(item).strip() for item in semantics.get("metrics", [])[:3] if item]
        visual_brief = str(semantics.get("visual_brief") or "").strip()
        palette = theme_context.get("palette", {})
        subject_hint = self._extract_subject_hint(str(theme_context.get("deck_title") or ""), title)
        scene_direction = self._build_slide_scene_direction(
            title=title,
            layout_variant=layout_variant,
            subject_hint=subject_hint,
            key_points=key_points,
            metrics=metrics,
        )

        title_lower = title.lower()
        if layout_variant == "timeline":
            visual_direction = (
                f"Create a presentation-grade milestone scene about {subject_hint} with visible progression, "
                "clear pathing, and strategic motion cues. Show a literal roadmap rather than abstract color washes."
            )
        elif layout_variant == "closing":
            visual_direction = (
                f"Create a premium closing scene for {subject_hint} with confident human energy, forward motion, "
                "and a clear focal subject. Avoid blank or empty compositions."
            )
        elif layout_variant == "cover":
            visual_direction = (
                f"Create a high-end hero scene centered on {subject_hint}. The composition should feel specific to the topic, "
                "editorial, and recognizably about the subject, not generic abstract startup art."
            )
        elif layout_variant == "metrics" or any(token in title_lower for token in ("traction", "market", "growth", "business model", "ask", "financial")):
            visual_direction = (
                f"Create an investor-grade visual about {subject_hint} that shows momentum, market scale, product value, or business performance "
                "through a literal scene with data-informed objects, people, and ecosystem cues. Avoid screenshots and avoid pure abstract gradients."
            )
        elif any(token in title_lower for token in ("team", "founder", "leadership")):
            visual_direction = (
                f"Create a polished leadership or collaboration scene for {subject_hint} featuring confident professionals, "
                "a modern working environment, and premium editorial lighting. Avoid stock-photo cliches."
            )
        else:
            visual_direction = (
                f"Create a presentation-grade editorial illustration for {subject_hint} with a clear literal focal point, "
                "strategic atmosphere, and a subject-specific scene rather than an abstract placeholder."
            )

        context_bits = [lead] if lead else []
        if key_points:
            context_bits.append("Key themes: " + "; ".join(key_points))
        if metrics:
            context_bits.append("Evidence and metrics: " + "; ".join(metrics))
        if visual_brief:
            context_bits.append("Desired visual direction: " + visual_brief)

        return (
            f"Create a premium 16:9 keynote slide visual for '{title}' in a deck about {subject_hint}. "
            f"{visual_direction}. {scene_direction} "
            + (" ".join(context_bits) + " " if context_bits else "")
            + "Use a sophisticated palette inspired by "
            + f"{palette.get('background', '#0f172a')}, {palette.get('accent', '#38bdf8')}, and {palette.get('accent_secondary', '#8b5cf6')}. "
            + "The image must feel polished, strategic, subject-specific, and presentation-ready. "
            + "No readable text, no letters, no UI screenshots, no memes, no watermarks, no collage. "
            + "Avoid blank dark panels, empty abstract gradients, low-detail filler imagery, repeated boardroom scenes, and repeated visual motifs across slides. "
            + "Vary the setting, composition, and focal subject so this slide looks distinct from the rest of the deck while staying visually cohesive. "
            + "Use one strong focal scene with depth, lighting, and enough visual detail to carry an investor-grade slide."
        )

    async def _generate_slide_visual_asset(
        self,
        prompt: str,
        presentation_name: str,
        slide_number: int,
    ) -> Optional[str]:
        try:
            config = get_config()
            if not config.REPLICATE_API_TOKEN:
                return None

            account_id = getattr(self, "_account_id", None) or getattr(self, "account_id", None)
            if not account_id:
                account_id = getattr(self.thread_manager, "account_id", None)

            if account_id:
                has_credits, _, _ = await media_billing.check_credits(account_id)
                if not has_credits:
                    logger.warning("[PRESENTATION] Skipping visual generation due to insufficient credits")
                    return None

            await self._ensure_shared_images_dir()

            output = await asyncio.to_thread(
                replicate.run,
                "google/nano-banana-pro",
                input={
                    "prompt": prompt,
                    "aspect_ratio": "16:9",
                    "resolution": "2K",
                    "output_format": "png",
                    "safety_filter_level": "block_only_high",
                },
            )

            output_list = list(output) if hasattr(output, "__iter__") and not hasattr(output, "read") else [output]
            if not output_list:
                return None

            first_output = output_list[0]
            if hasattr(first_output, "read"):
                result_bytes = first_output.read()
            else:
                url = str(first_output.url) if hasattr(first_output, "url") else str(first_output)
                async with get_http_client() as client:
                    response = await client.get(url, timeout=120.0)
                    response.raise_for_status()
                    result_bytes = response.content

            safe_name = self._sanitize_filename(presentation_name) or "presentation"
            file_name = f"{safe_name}_slide_{slide_number:02d}_visual.png"
            relative_path = f"{self.presentations_dir}/images/{file_name}"
            await self.sandbox.fs.upload_file(result_bytes, f"{self.workspace_path}/{relative_path}")

            if account_id:
                try:
                    await media_billing.deduct_replicate_image(
                        account_id=account_id,
                        model="google/nano-banana-pro",
                        count=1,
                        description=f"Presentation visual generation for slide {slide_number}",
                    )
                except Exception as billing_error:
                    logger.warning(f"[PRESENTATION] Failed to deduct credits for slide visual: {billing_error}")

            return f"../images/{file_name}"
        except Exception as exc:
            logger.warning(f"[PRESENTATION] Failed to generate slide visual: {exc}")
            return None

    def _render_structured_slide(
        self,
        semantics: Dict[str, object],
        theme_context: Dict[str, Any],
        layout_variant: str,
        slide_number: int,
        visual_src: Optional[str],
    ) -> str:
        palette = theme_context.get("palette", {})
        font_family = theme_context.get("font_family", "'Inter', sans-serif")
        background_asset = theme_context.get("background_asset")
        title_text = escape(str(semantics.get("title") or "Slide"))
        kicker_text = escape(str(semantics.get("kicker") or "Research-backed narrative"))
        lead_text = escape(str(semantics.get("lead") or title_text))
        supporting = [escape(item) for item in semantics.get("supporting", [])[:2] if item]
        key_points = [escape(item) for item in semantics.get("key_points", [])[:5] if item]
        metric_cards = self._build_metric_cards([str(item) for item in semantics.get("metrics", []) if item])
        image_alt = title_text

        primary_visual = visual_src or background_asset or ""
        primary_visual_attr = escape(primary_visual, quote=True) if primary_visual else ""
        backdrop_visual_attr = ""
        if visual_src and background_asset and visual_src != background_asset:
            backdrop_visual_attr = escape(background_asset, quote=True)
        elif background_asset and primary_visual != background_asset:
            backdrop_visual_attr = escape(background_asset, quote=True)

        bullet_markup = "".join(
            f"""
            <div class="vv-point-card">
              <span class="vv-point-index">{index:02d}</span>
              <p>{point}</p>
            </div>
            """
            for index, point in enumerate(key_points, start=1)
        )
        timeline_markup = "".join(
            f"""
            <div class="vv-timeline-item">
              <div class="vv-timeline-index">{index}</div>
              <div class="vv-timeline-copy">{point}</div>
            </div>
            """
            for index, point in enumerate(key_points, start=1)
        )
        support_markup = "".join(
            f'<div class="vv-support-card"><p>{paragraph}</p></div>'
            for paragraph in supporting
        )
        metrics_markup = "".join(
            f"""
            <div class="vv-metric-card">
              <span class="vv-metric-display">{escape(card["display"])}</span>
              <p class="vv-metric-label">{escape(card["label"])}</p>
            </div>
            """
            for card in metric_cards
        )

        media_markup = ""
        if primary_visual_attr:
            media_markup = f"""
            <div class="vv-media-shell">
              <img src="{primary_visual_attr}" alt="{image_alt}" class="vv-media-image" />
            </div>
            """

        layout_markup = ""
        if layout_variant == "cover":
            layout_markup = f"""
            <div class="vv-copy-column vv-cover-copy">
              <p class="vv-kicker">{kicker_text}</p>
              <h1>{title_text}</h1>
              <p class="vv-lead">{lead_text}</p>
              {'<div class="vv-chip-row">' + ''.join(f'<span class="vv-chip">{point}</span>' for point in key_points[:3]) + '</div>' if key_points else ''}
            </div>
            {media_markup}
            """
        elif layout_variant == "timeline":
            layout_markup = f"""
            <div class="vv-copy-column">
              <p class="vv-kicker">{kicker_text}</p>
              <h1>{title_text}</h1>
              <p class="vv-lead">{lead_text}</p>
              <div class="vv-timeline-list">{timeline_markup}</div>
            </div>
            {media_markup}
            """
        elif layout_variant == "closing":
            layout_markup = f"""
            <div class="vv-closing-panel">
              <p class="vv-kicker">{kicker_text}</p>
              <h1>{title_text}</h1>
              <p class="vv-lead">{lead_text}</p>
              {'<div class="vv-metric-strip">' + metrics_markup + '</div>' if metrics_markup else ''}
              {'<div class="vv-support-grid">' + support_markup + '</div>' if support_markup else ''}
            </div>
            {media_markup}
            """
        elif layout_variant == "metrics":
            layout_markup = f"""
            <div class="vv-copy-column">
              <p class="vv-kicker">{kicker_text}</p>
              <h1>{title_text}</h1>
              <p class="vv-lead">{lead_text}</p>
              {'<div class="vv-metric-strip">' + metrics_markup + '</div>' if metrics_markup else ''}
              {'<div class="vv-points-grid">' + bullet_markup + '</div>' if bullet_markup else ''}
            </div>
            {media_markup}
            """
        else:
            layout_markup = f"""
            <div class="vv-copy-column">
              <p class="vv-kicker">{kicker_text}</p>
              <h1>{title_text}</h1>
              <p class="vv-lead">{lead_text}</p>
              {'<div class="vv-metric-strip">' + metrics_markup + '</div>' if metrics_markup else ''}
              {'<div class="vv-points-grid">' + bullet_markup + '</div>' if bullet_markup else ''}
              {'<div class="vv-support-grid">' + support_markup + '</div>' if support_markup else ''}
            </div>
            {media_markup}
            """

        backdrop_style = (
            f'background-image: linear-gradient(135deg, {self._hex_to_rgba(palette.get("background", "#0f172a"), 0.86)}, {self._hex_to_rgba(palette.get("surface", "#172554"), 0.92)}), url("{backdrop_visual_attr}");'
            if backdrop_visual_attr
            else ""
        )

        return f"""
<style>
  .vv-structured-slide {{
    width: 1920px;
    height: 1080px;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
    padding: 56px;
    color: {palette.get("text", "#f8fafc")};
    font-family: {font_family};
    background:
      radial-gradient(circle at 12% 16%, {self._hex_to_rgba(palette.get("accent", "#38bdf8"), 0.22)}, transparent 32%),
      radial-gradient(circle at 88% 14%, {self._hex_to_rgba(palette.get("accent_secondary", "#8b5cf6"), 0.18)}, transparent 28%),
      linear-gradient(135deg, {palette.get("background", "#0f172a")} 0%, {palette.get("surface", "#172554")} 100%);
    {backdrop_style}
    background-size: cover;
    background-position: center;
  }}
  .vv-structured-slide * {{
    box-sizing: border-box;
    font-family: inherit;
  }}
  .vv-shell {{
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 38px;
    overflow: hidden;
    border: 1px solid {self._hex_to_rgba(palette.get("text", "#f8fafc"), 0.12)};
    background: linear-gradient(160deg, {self._hex_to_rgba(palette.get("background", "#0f172a"), 0.86)}, {self._hex_to_rgba(palette.get("surface", "#172554"), 0.72)});
    box-shadow: 0 36px 100px {self._hex_to_rgba(palette.get("background", "#0f172a"), 0.35)};
    display: grid;
    grid-template-columns: {("1.05fr 0.95fr" if layout_variant in {"cover", "split", "timeline"} else "1fr 0.85fr") if primary_visual_attr else "1fr"};
    gap: 28px;
    padding: 54px;
  }}
  .vv-copy-column,
  .vv-closing-panel {{
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 24px;
    position: relative;
    z-index: 2;
  }}
  .vv-kicker {{
    margin: 0;
    font-size: 16px;
    line-height: 1.2;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: {palette.get("accent", "#38bdf8")};
    font-weight: 700;
  }}
  .vv-structured-slide h1 {{
    margin: 0;
    max-width: 940px;
    font-size: {("88px" if layout_variant == "cover" else "66px")};
    line-height: 0.96;
    letter-spacing: -0.05em;
    font-weight: 800;
  }}
  .vv-lead {{
    margin: 0;
    max-width: 860px;
    font-size: 28px;
    line-height: 1.45;
    color: {palette.get("muted", "#cbd5e1")};
    font-weight: 500;
  }}
  .vv-chip-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
  }}
  .vv-chip {{
    border-radius: 999px;
    padding: 12px 18px;
    background: {self._hex_to_rgba(palette.get("accent", "#38bdf8"), 0.14)};
    border: 1px solid {self._hex_to_rgba(palette.get("accent", "#38bdf8"), 0.28)};
    font-size: 18px;
    color: {palette.get("text", "#f8fafc")};
  }}
  .vv-points-grid,
  .vv-support-grid,
  .vv-metric-strip {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
  }}
  .vv-metric-strip {{
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }}
  .vv-point-card,
  .vv-support-card,
  .vv-timeline-item,
  .vv-metric-card {{
    border-radius: 26px;
    padding: 22px 22px 24px;
    border: 1px solid {self._hex_to_rgba(palette.get("text", "#f8fafc"), 0.12)};
    background: linear-gradient(180deg, {self._hex_to_rgba(palette.get("text", "#f8fafc"), 0.07)}, {self._hex_to_rgba(palette.get("surface", "#172554"), 0.18)});
    backdrop-filter: blur(12px);
  }}
  .vv-point-index,
  .vv-timeline-index {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    margin-bottom: 14px;
    border-radius: 999px;
    background: linear-gradient(135deg, {palette.get("accent", "#38bdf8")}, {palette.get("accent_secondary", "#8b5cf6")});
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }}
  .vv-point-card p,
  .vv-support-card p,
  .vv-timeline-copy,
  .vv-metric-label {{
    margin: 0;
    font-size: 23px;
    line-height: 1.45;
    color: {palette.get("text", "#f8fafc")};
  }}
  .vv-metric-display {{
    display: block;
    margin-bottom: 10px;
    font-size: 36px;
    line-height: 1;
    font-weight: 800;
    color: {palette.get("accent", "#38bdf8")};
  }}
  .vv-timeline-list {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }}
  .vv-media-shell {{
    position: relative;
    min-width: 0;
    min-height: 0;
    border-radius: 32px;
    overflow: hidden;
    border: 1px solid {self._hex_to_rgba(palette.get("text", "#f8fafc"), 0.12)};
    background: linear-gradient(180deg, {self._hex_to_rgba(palette.get("surface", "#172554"), 0.82)}, {self._hex_to_rgba(palette.get("background", "#0f172a"), 0.96)});
  }}
  .vv-media-image {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .vv-shell::after {{
    content: "Slide {slide_number:02d}";
    position: absolute;
    left: 54px;
    bottom: 28px;
    font-size: 15px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: {self._hex_to_rgba(palette.get("text", "#f8fafc"), 0.55)};
  }}
</style>
<div class="vv-structured-slide vv-{layout_variant}">
  <div class="vv-shell">
    {layout_markup}
  </div>
</div>
"""

    async def _apply_visual_baseline(
        self,
        slide_content: str,
        slide_title: str,
        presentation_name: str,
        presentation_title: str,
        slide_number: int,
        theme_context: Dict[str, Any],
        semantics: Optional[Dict[str, object]] = None,
        omit_visual: Optional[bool] = None,
    ) -> str:
        """Auto-design simple slide fragments into a polished fixed-layout presentation slide."""
        semantics = semantics or self._extract_slide_semantics(slide_content, slide_title)
        layout_variant = self._choose_layout_variant(semantics, slide_number)
        omit_visual = self._should_omit_slide_visual(slide_content, semantics) if omit_visual is None else omit_visual

        image = semantics.get("image") if isinstance(semantics.get("image"), dict) else None
        visual_src = (image or {}).get("src") if image else None
        if omit_visual:
            visual_src = None
        elif not visual_src:
            visual_prompt = self._build_slide_visual_prompt(semantics, layout_variant, theme_context)
            visual_src = await self._generate_slide_visual_asset(
                prompt=visual_prompt,
                presentation_name=presentation_name,
                slide_number=slide_number,
            )

        return self._render_structured_slide(
            semantics=semantics,
            theme_context=theme_context,
            layout_variant=layout_variant,
            slide_number=slide_number,
            visual_src=visual_src,
        )

    def _create_slide_html(self, slide_content: str, slide_number: int, total_slides: int, presentation_title: str) -> str:
        """Create a basic HTML document with Google Fonts"""
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1920, initial-scale=1.0">
    <title>{presentation_title} - Slide {slide_number}</title>
    <!-- Google Fonts - Inter for modern, clean typography -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <!-- Optional libraries loaded asynchronously - won't block page rendering -->
    <script src="https://d3js.org/d3.v7.min.js" async></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1" async></script>
    <style>
        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
        body {{
            height: 1080px;
            width: 1920px;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
    </style>
</head>
<body>
    {slide_content}
</body>
</html>"""
        return html_template

    async def _load_presentation_metadata(self, presentation_path: str):
        """Load presentation metadata, create if doesn't exist"""
        metadata_path = f"{presentation_path}/metadata.json"
        try:
            metadata_content = await self.sandbox.fs.download_file(metadata_path)
            return json.loads(metadata_content.decode())
        except:
            # Create default metadata
            return {
                "presentation_name": "",
                "title": "Presentation", 
                "description": "",
                "slides": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

    async def _save_presentation_metadata(self, presentation_path: str, metadata: Dict):
        """Save presentation metadata"""
        metadata["updated_at"] = datetime.now().isoformat()
        metadata_path = f"{presentation_path}/metadata.json"
        await self.sandbox.fs.upload_file(json.dumps(metadata, indent=2).encode(), metadata_path)

    def _load_template_metadata(self, template_name: str) -> Dict:
        """Load metadata from a template on the backend filesystem"""
        metadata_path = os.path.join(self.templates_dir, template_name, "metadata.json")
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {}

    def _read_template_slide(self, template_name: str, slide_filename: str) -> str:
        """Read a slide HTML file from a template"""
        slide_path = os.path.join(self.templates_dir, template_name, slide_filename)
        try:
            with open(slide_path, 'r') as f:
                return f.read()
        except Exception as e:
            return ""

    async def _copy_template_to_workspace(self, template_name: str, presentation_name: str) -> str:
        """
        Initialize a template-backed presentation in the workspace.

        Copy visual assets into the live presentation directory, but keep template HTML
        slides hidden under `.template_reference/` so placeholder template slides do not
        appear as part of the active deck unless explicitly promoted via populate_template_slide.
        """
        await self._ensure_sandbox()
        await self._ensure_presentations_dir()
        
        template_path = os.path.join(self.templates_dir, template_name)
        safe_name = self._sanitize_filename(presentation_name)
        presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
        template_reference_path = f"{presentation_path}/.template_reference"
        
        # Ensure presentation directory exists
        await self._ensure_presentation_dir(presentation_name)
        try:
            await self.sandbox.fs.create_folder(template_reference_path, "755")
        except:
            pass
        
        copied_assets: List[str] = []
        for root, dirs, files in os.walk(template_path):
            rel_path = os.path.relpath(root, template_path)
            for file in files:
                source_file = os.path.join(root, file)
                rel_file_path = os.path.relpath(source_file, template_path)
                suffix = Path(file).suffix.lower()
                target_root = template_reference_path if suffix == ".html" else presentation_path
                target_file = os.path.join(target_root, rel_file_path).replace('\\', '/')
                target_dir_path = os.path.dirname(target_file)
                if target_dir_path:
                    try:
                        await self.sandbox.fs.create_folder(target_dir_path, "755")
                    except:
                        pass
                
                try:
                    with open(source_file, 'rb') as f:
                        file_content = f.read()
                    await self.sandbox.fs.upload_file(file_content, target_file)
                    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                        relative_asset = rel_file_path.replace("\\", "/")
                        if relative_asset.lower() not in {
                            "image.png",
                            "image.jpg",
                            "image.jpeg",
                            "preview.png",
                            "preview.jpg",
                            "preview.jpeg",
                            "thumbnail.png",
                            "thumbnail.jpg",
                            "thumbnail.jpeg",
                        }:
                            copied_assets.append(relative_asset)
                except Exception as e:
                    print(f"Error copying {rel_file_path}: {str(e)}")
        
        template_metadata = self._load_template_metadata(template_name)

        metadata = {
            "presentation_name": presentation_name,
            "title": presentation_name,
            "description": template_metadata.get("description", ""),
            "slides": {},
            "template_source": template_name,
            "template_assets": sorted(set(copied_assets)),
            "template_reference_dir": ".template_reference",
            "template_slide_count": len(template_metadata.get("slides", {})),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        await self._save_presentation_metadata(presentation_path, metadata)
        
        return presentation_path

    def _extract_style_from_html(self, html_content: str) -> Dict:
        """Extract CSS styles and design patterns from HTML content"""
        style_info = {
            "fonts": [],
            "colors": [],
            "layout_patterns": [],
            "key_css_classes": []
        }
        
        # Extract font imports
        font_imports = re.findall(r'@import url\([\'"]([^\'"]+)[\'"]', html_content)
        font_families = re.findall(r'font-family:\s*[\'"]?([^;\'"]+)[\'"]?', html_content)
        style_info["fonts"] = list(set(font_imports + font_families))
        
        # Extract color values (hex, rgb, rgba)
        hex_colors = re.findall(r'#[0-9A-Fa-f]{3,6}', html_content)
        rgb_colors = re.findall(r'rgba?\([^)]+\)', html_content)
        style_info["colors"] = list(set(hex_colors + rgb_colors))[:20]  # Limit to top 20
        
        # Extract class names
        class_names = re.findall(r'class=[\'"]([^\'"]+)[\'"]', html_content)
        style_info["key_css_classes"] = list(set(class_names))[:30]
        
        # Identify layout patterns
        if 'display: flex' in html_content or 'display:flex' in html_content:
            style_info["layout_patterns"].append("flexbox")
        if 'display: grid' in html_content or 'display:grid' in html_content:
            style_info["layout_patterns"].append("grid")
        if 'position: absolute' in html_content:
            style_info["layout_patterns"].append("absolute positioning")
        
        return style_info


    @openapi_schema({
        "type": "function",
        "function": {
            "name": "list_templates",
            "description": "List all available presentation templates. ** CRITICAL: ONLY USE WHEN USER EXPLICITLY REQUESTS TEMPLATES ** **WHEN TO USE**: Call this tool ONLY when the user explicitly asks for templates (e.g., 'use a template', 'show me templates', 'use the minimalist template', 'I want to use a template'). **WHEN TO SKIP**: Do NOT call this tool by default. The default workflow is CUSTOM THEME which creates truly unique designs. Do NOT call this tool if: (1) the user requests a presentation without mentioning templates (use custom theme instead), (2) the user explicitly requests a custom theme, or (3) the user wants a unique/original design. **IMPORTANT**: Templates are optional - only use when explicitly requested. The default is always a custom, unique design based on the topic's actual brand colors and visual identity.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    async def list_templates(self) -> ToolResult:
        """List all available presentation templates with metadata and images"""
        try:
            templates = []
            
            # Check if templates directory exists
            if not os.path.exists(self.templates_dir):
                return self.success_response({
                    "message": "No templates directory found",
                    "templates": []
                })
            
            # List all subdirectories in templates folder
            for item in os.listdir(self.templates_dir):
                template_path = os.path.join(self.templates_dir, item)
                if os.path.isdir(template_path) and not item.startswith('.'):
                    # Load metadata for this template
                    metadata = self._load_template_metadata(item)
                    
                    # Check if image.png exists
                    image_path = os.path.join(template_path, "image.png")
                    has_image = os.path.exists(image_path)
                    
                    template_info = {
                        "id": item,
                        "name": item,  # Use folder name directly
                        "has_image": has_image
                    }
                    templates.append(template_info)
            
            if not templates:
                return self.success_response({
                    "message": "No templates found",
                    "templates": []
                })
            
            # Sort templates by name
            templates.sort(key=lambda x: x["name"])
            
            return self.success_response({
                "message": f"Found {len(templates)} template(s)",
                "templates": templates,
                "note": "Use load_template_design with a template id to get the complete design reference. If you don't like any of these templates, you can choose a custom theme instead."
            })
            
        except Exception as e:
            return self.fail_response(f"Failed to list templates: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "load_template_design",
            "description": "Load complete design reference from a presentation template including all slide HTML and extracted style patterns (colors, fonts, layouts). If presentation_name is provided, the template will initialize a themed presentation in /workspace/presentations/{presentation_name}/ by copying its visual assets and hidden reference slides, but the active deck remains empty until you create real slides with create_slide. Otherwise, use this template as DESIGN INSPIRATION ONLY - study the visual styling, CSS patterns, and layout structure to create your own original slides with similar aesthetics but completely different content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": "Name of the template to load (e.g., 'textbook')"
                    },
                    "presentation_name": {
                        "type": "string",
                        "description": "Optional: Name for the presentation. If provided, the entire template will be copied to /workspace/presentations/{presentation_name}/ so you can edit the slides directly. All files from the template (including HTML slides, images, and subdirectories) will be copied."
                    }
                },
                "required": ["template_name"]
            }
        }
    })
    async def load_template_design(self, template_name: str, presentation_name: Optional[str] = None) -> ToolResult:
        """Load complete template design including all slides HTML and extracted style patterns.
        
        If presentation_name is provided, copies the entire template to workspace for editing.
        """
        try:
            template_name = self._resolve_template_name(template_name)
            template_path = os.path.join(self.templates_dir, template_name)
            
            if not os.path.exists(template_path):
                return self.fail_response(f"Template '{template_name}' not found")
            
            # If presentation_name is provided, copy template to workspace
            presentation_path = None
            if presentation_name:
                try:
                    presentation_path = await self._copy_template_to_workspace(template_name, presentation_name)
                except Exception as e:
                    return self.fail_response(f"Failed to copy template to workspace: {str(e)}")
            
            # Load template metadata
            metadata = self._load_template_metadata(template_name)
            
            if not metadata or "slides" not in metadata:
                return self.fail_response(f"Template '{template_name}' has no metadata or slides")
            
            # Extract all slides HTML
            slides = []
            all_fonts = set()
            all_colors = set()
            all_layout_patterns = set()
            all_css_classes = set()
            
            for slide_num, slide_data in sorted(metadata["slides"].items(), key=lambda x: int(x[0])):
                slide_filename = slide_data.get("filename", f"slide_{int(slide_num):02d}.html")
                html_content = self._read_template_slide(template_name, slide_filename)
                
                if html_content:
                    # Add slide info
                    slides.append({
                        "slide_number": int(slide_num),
                        "title": slide_data.get("title", f"Slide {slide_num}"),
                        "filename": slide_filename,
                        "html_content": html_content,
                        "html_length": len(html_content)
                    })
                    
                    # Extract style information from this slide
                    style_info = self._extract_style_from_html(html_content)
                    all_fonts.update(style_info["fonts"])
                    all_colors.update(style_info["colors"])
                    all_layout_patterns.update(style_info["layout_patterns"])
                    all_css_classes.update(style_info["key_css_classes"])
            
            if not slides:
                return self.fail_response(f"Could not load any slides from template '{template_name}'")
            
            # Build response
            response_data = {
                "template_name": template_name,
                "template_title": metadata.get("title", template_name),
                "description": metadata.get("description", ""),
                "total_slides": len(slides),
                "slides": slides,
                "design_system": {
                    "fonts": list(all_fonts)[:10],  # Top 10 fonts
                    "color_palette": list(all_colors)[:20],  # Top 20 colors
                    "layout_patterns": list(all_layout_patterns),
                    "common_css_classes": list(all_css_classes)[:30]  # Top 30 classes
                }
            }
            
            # Add workspace path info if template was copied
            if presentation_path:
                safe_name = self._sanitize_filename(presentation_name)
                response_data["presentation_path"] = f"{self.presentations_dir}/{safe_name}"
                # Always return the actual workspace folder name to avoid
                # downstream path mismatches when the original name had spaces/symbols.
                response_data["presentation_name"] = safe_name
                response_data["copied_to_workspace"] = True
                response_data["requires_follow_up_edit"] = True
                response_data["required_next_tool"] = "create_slide"
                response_data["note"] = f"Template initialized at /workspace/{self.presentations_dir}/{safe_name}/. **CRITICAL**: The active deck starts empty on purpose so template placeholder slides do not leak into the result. Use create_slide for the actual deck output. The initialized presentation carries the template's design system, copied assets, and hidden reference slides so create_slide can render researched content with the template's visual direction. Use populate_template_slide only for advanced exact-template surgery."
                response_data["usage_instructions"] = {
                    "purpose": "TEMPLATE INITIALIZED - Use create_slide to render researched slides with inherited template styling",
                    "do": [
                        "Use create_slide on this same presentation_name to create the real slides with researched content",
                        "Let create_slide inherit the template colors, fonts, and background assets from the initialized deck",
                        "Use local workspace images such as ../images/... or let the slide renderer generate a premium visual when needed",
                        "Use populate_template_slide only when you specifically need exact DOM-preserving text swaps"
                    ],
                    "dont": [
                        "Do not end the workflow right after template copy",
                        "Do not expect copied demo slides to be the final deck",
                        "Do not keep template placeholder text or example labels",
                        "Do not rely on exact text-matching surgery unless you intentionally need populate_template_slide",
                        "Do not use create_file for slide HTML"
                    ]
                }
            else:
                response_data["copied_to_workspace"] = False
                response_data["usage_instructions"] = {
                    "purpose": "DESIGN REFERENCE ONLY - Use for visual inspiration",
                    "do": [
                        "Study the HTML structure and CSS styling patterns",
                        "Learn the layout techniques and visual hierarchy",
                        "Understand the color scheme and typography usage",
                        "Analyze how elements are positioned and styled",
                        "Create NEW slides with similar design but ORIGINAL content"
                    ],
                    "dont": [
                        "Copy template content directly",
                        "Use template text, data, or information",
                        "Duplicate slides without modification",
                        "Treat templates as final deliverables"
                    ]
                }
                response_data["note"] = "This template provides ALL slides and extracted design patterns in one response. Study the HTML and CSS to understand the design system, then create your own original slides with similar visual styling. To edit this template directly, provide a presentation_name parameter."
            
            if presentation_path:
                presentation_lock = await self._get_metadata_lock(presentation_path)
                async with presentation_lock:
                    copied_metadata = await self._load_presentation_metadata(presentation_path)
                    copied_metadata["template_source"] = template_name
                    copied_metadata["template_design_system"] = response_data["design_system"]
                    copied_metadata["template_assets"] = self._list_template_assets(template_name)
                    await self._save_presentation_metadata(presentation_path, copied_metadata)

            return self.success_response(response_data)
            
        except Exception as e:
            return self.fail_response(f"Failed to load template design: {str(e)}")

    def _replace_template_text(self, soup: BeautifulSoup, find_text: str, replace_with: str, replace_all: bool = False) -> int:
        if not find_text:
            return 0

        replacements = 0
        needle = find_text.strip()

        for node in soup.find_all(string=True):
            if not isinstance(node, NavigableString):
                continue

            parent = node.parent
            if parent and parent.name in {"script", "style", "title", "head"}:
                continue

            original = str(node)
            original_stripped = original.strip()
            if not original_stripped:
                continue

            updated = None
            if needle in original:
                updated = original.replace(needle, replace_with, -1 if replace_all else 1)
            elif original_stripped == needle:
                updated = replace_with

            if updated is None or updated == original:
                continue

            node.replace_with(updated)
            replacements += 1
            if not replace_all:
                break

        return replacements

    def _replace_template_image(self, soup: BeautifulSoup, replacement: Dict[str, str]) -> int:
        find_src = (replacement.get("find_src") or "").strip()
        find_alt = (replacement.get("find_alt") or "").strip().lower()
        replace_with = (replacement.get("replace_with") or "").strip()
        alt_text = (replacement.get("alt") or "").strip()

        if not replace_with:
            return 0

        applied = 0
        images = soup.find_all("img")
        for image in images:
            current_src = (image.get("src") or "").strip()
            current_alt = (image.get("alt") or "").strip().lower()

            matches = False
            if find_src and current_src == find_src:
                matches = True
            elif find_alt and find_alt in current_alt:
                matches = True
            elif not find_src and not find_alt and len(images) == 1:
                matches = True

            if not matches:
                continue

            image["src"] = replace_with
            if alt_text:
                image["alt"] = alt_text
            applied += 1
            break

        return applied

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "populate_template_slide",
            "description": "Safely replace visible text and image sources inside a copied template slide while preserving the template DOM, CSS, classes, layout, and visual styling. Use this after load_template_design with presentation_name only when you explicitly need exact DOM-preserving edits. For most template-based presentations, use create_slide after load_template_design so the renderer can inherit the template design system without brittle text matching. **🚨 PARAMETER NAMES**: Use EXACTLY these parameter names: `presentation_name` (REQUIRED), `slide_number` (REQUIRED), `slide_title` (REQUIRED), `text_replacements` (optional), `image_replacements` (optional), `presentation_title` (optional).",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_name": {
                        "type": "string",
                        "description": "Name of the copied presentation folder created by load_template_design."
                    },
                    "slide_number": {
                        "type": "integer",
                        "description": "Slide number to update inside the copied template deck."
                    },
                    "slide_title": {
                        "type": "string",
                        "description": "Human-friendly title for this slide. Used for presentation metadata."
                    },
                    "text_replacements": {
                        "type": "array",
                        "description": "List of exact visible text replacements to apply. Use strings that already exist in the copied template slide and replace them with researched content.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "find_text": {
                                    "type": "string",
                                    "description": "Exact visible text currently present in the template slide."
                                },
                                "replace_with": {
                                    "type": "string",
                                    "description": "New researched content to display in place of the existing text."
                                },
                                "replace_all": {
                                    "type": "boolean",
                                    "description": "Optional. Replace every matching occurrence instead of only the first.",
                                    "default": False
                                }
                            },
                            "required": ["find_text", "replace_with"],
                            "additionalProperties": False
                        }
                    },
                    "image_replacements": {
                        "type": "array",
                        "description": "Optional list of image source replacements. Match by find_src or find_alt and replace with a workspace image path such as ../images/slide1.jpg.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "find_src": {
                                    "type": "string",
                                    "description": "Optional exact image src currently present in the template slide."
                                },
                                "find_alt": {
                                    "type": "string",
                                    "description": "Optional alt text fragment to identify the image when src is not convenient."
                                },
                                "replace_with": {
                                    "type": "string",
                                    "description": "New image path to use. Prefer workspace-relative paths such as ../images/brand-hero.jpg."
                                },
                                "alt": {
                                    "type": "string",
                                    "description": "Optional replacement alt text."
                                }
                            },
                            "required": ["replace_with"],
                            "additionalProperties": False
                        }
                    },
                    "presentation_title": {
                        "type": "string",
                        "description": "Optional overall title for the full presentation deck."
                    }
                },
                "required": ["presentation_name", "slide_number", "slide_title"],
                "additionalProperties": False
            }
        }
    })
    async def populate_template_slide(
        self,
        presentation_name: str,
        slide_number: int,
        slide_title: str,
        text_replacements: Optional[List[Dict[str, Union[str, bool]]]] = None,
        image_replacements: Optional[List[Dict[str, str]]] = None,
        presentation_title: Optional[str] = None,
    ) -> ToolResult:
        try:
            await self._ensure_sandbox()
            await self._ensure_presentations_dir()

            if not presentation_name:
                return self.fail_response("Presentation name is required.")

            if slide_number is None:
                return self.fail_response("Slide number is required.")

            try:
                slide_number = int(slide_number)
            except (TypeError, ValueError):
                return self.fail_response(f"Slide number must be an integer, got: {type(slide_number).__name__}")

            if slide_number < 1:
                return self.fail_response("Slide number must be 1 or greater.")

            if not slide_title:
                return self.fail_response("Slide title is required.")

            if not text_replacements and not image_replacements:
                return self.fail_response("At least one text or image replacement is required.")

            safe_name, presentation_path = await self._ensure_presentation_dir(presentation_name)
            slide_filename = f"slide_{slide_number:02d}.html"
            slide_path = f"{presentation_path}/{slide_filename}"

            try:
                existing_html_raw = await self.sandbox.fs.download_file(slide_path)
            except Exception:
                reference_slide_path = f"{presentation_path}/.template_reference/{slide_filename}"
                try:
                    existing_html_raw = await self.sandbox.fs.download_file(reference_slide_path)
                except Exception as exc:
                    return self.fail_response(f"Template slide not found: {slide_filename} ({exc})")

            existing_html = existing_html_raw.decode() if isinstance(existing_html_raw, bytes) else str(existing_html_raw)
            soup = BeautifulSoup(existing_html, "html.parser")

            text_updates_applied = 0
            unmatched_text = []
            for replacement in text_replacements or []:
                find_text = str(replacement.get("find_text") or "").strip()
                replace_with = str(replacement.get("replace_with") or "").strip()
                replace_all = bool(replacement.get("replace_all", False))

                applied = self._replace_template_text(soup, find_text, replace_with, replace_all=replace_all)
                if applied == 0:
                    unmatched_text.append(find_text)
                text_updates_applied += applied

            image_updates_applied = 0
            unmatched_images = []
            for replacement in image_replacements or []:
                applied = self._replace_template_image(soup, replacement)
                if applied == 0:
                    unmatched_images.append(replacement.get("find_src") or replacement.get("find_alt") or "(first image)")
                image_updates_applied += applied

            if unmatched_text or unmatched_images:
                details: List[str] = []
                if unmatched_text:
                    details.append(f"unmatched text: {', '.join(unmatched_text[:4])}")
                if unmatched_images:
                    details.append(f"unmatched images: {', '.join(str(item) for item in unmatched_images[:4])}")
                return self.fail_response(
                    "Failed to populate template slide because some requested replacements did not match the copied slide. "
                    + "; ".join(details)
                )

            if soup.title:
                deck_title = presentation_title or presentation_name
                soup.title.string = f"{deck_title} - Slide {slide_number}"

            updated_html = str(soup)
            await self.sandbox.fs.upload_file(updated_html.encode(), slide_path)

            presentation_lock = await self._get_metadata_lock(presentation_path)
            async with presentation_lock:
                metadata = await self._load_presentation_metadata(presentation_path)
                metadata["presentation_name"] = presentation_name
                if presentation_title:
                    metadata["title"] = presentation_title
                if "slides" not in metadata:
                    metadata["slides"] = {}
                metadata["slides"][str(slide_number)] = {
                    "title": slide_title,
                    "filename": slide_filename,
                    "file_path": f"{self.presentations_dir}/{safe_name}/{slide_filename}",
                    "preview_url": f"/workspace/{self.presentations_dir}/{safe_name}/{slide_filename}",
                    "created_at": metadata.get("slides", {}).get(str(slide_number), {}).get("created_at", datetime.now().isoformat()),
                }
                await self._save_presentation_metadata(presentation_path, metadata)

            return self.success_response({
                "message": f"Template slide {slide_number} populated successfully",
                "presentation_name": presentation_name,
                "presentation_path": f"{self.presentations_dir}/{safe_name}",
                "slide_number": slide_number,
                "slide_title": slide_title,
                "slide_file": f"{self.presentations_dir}/{safe_name}/{slide_filename}",
                "preview_url": f"/workspace/{self.presentations_dir}/{safe_name}/{slide_filename}",
                "text_updates_applied": text_updates_applied,
                "image_updates_applied": image_updates_applied,
                "note": "Template structure preserved while visible content was replaced"
            })

        except Exception as e:
            return self.fail_response(f"Failed to populate template slide: {str(e)}")


    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_slide",
            "description": "Create or update a single slide in a presentation. **WHEN TO USE**: Use this for both custom-theme decks and template-initialized decks. If a template was initialized via load_template_design with presentation_name, this tool should preserve the copied template's framework/layout while replacing the content with researched slide material. **WHEN TO SKIP**: Only skip this if you explicitly need exact DOM-preserving edits inside the copied template, in which case use populate_template_slide. **PARALLEL EXECUTION**: This function supports parallel execution - create ALL slides simultaneously by using create_slide multiple times in parallel for much faster completion. Each slide is saved as a standalone HTML file with 1920x1080 dimensions (16:9 aspect ratio). Slides are automatically validated to ensure both width (≤1920px) and height (≤1080px) limits are met. Use `box-sizing: border-box` on containers with padding to prevent dimension overflow. **CRITICAL**: You MUST have completed research, outline, and visual planning before using this tool. All styling MUST be derived from the custom color scheme/design elements or the initialized template design system. **IMAGE RULE**: Do not hotlink public internet image URLs directly in slide HTML - download them into presentations/images/ first. If the user asks for no images, create the slide without visuals instead of calling canvas tools. **PRESENTATION DESIGN NOT WEBSITE**: Use fixed pixel dimensions, absolute positioning, and fixed layouts - NO responsive design patterns. **BEST INPUT FORMAT**: Prefer a research-backed slide brief with a clear thesis, 3-5 evidence bullets, 1-3 metrics/facts, and a visual brief; the tool can auto-render that into a polished slide. **🚨 PARAMETER NAMES**: Use EXACTLY these parameter names: `presentation_name` (REQUIRED), `slide_number` (REQUIRED), `slide_title` (REQUIRED), `content` (REQUIRED), `presentation_title` (optional). **❌ DO NOT USE**: `file_path` - this parameter does NOT exist!",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_name": {
                        "type": "string",
                        "description": "**REQUIRED** - Name of the presentation folder (creates folder if doesn't exist). This is the folder name where slides will be stored. Example: 'my_presentation' or 'marko_kraemer_presentation'. **CRITICAL**: Use this exact parameter name - do NOT use 'file_path' or any other name."
                    },
                    "slide_number": {
                        "type": "integer",
                        "description": "**REQUIRED** - Slide number (1-based integer). If slide exists, it will be updated. Example: 1, 2, 3, etc."
                    },
                    "slide_title": {
                        "type": "string",
                        "description": "**REQUIRED** - Title of this specific slide (for reference and navigation). Example: 'Introduction', 'Early Beginnings', 'Company Overview'."
                    },
                    "content": {
                        "type": "string",
                        "description": """**REQUIRED** - Either (A) HTML body content only (DO NOT include <!DOCTYPE>, <html>, <head>, or <body> tags - these are added automatically), or (B) a structured research-backed slide brief in plain text/markdown. Best results come from briefs that include: a thesis sentence, 3-5 evidence bullets, 1-3 metrics/facts, and a visual brief tied to the subject. The tool can auto-render those briefs into polished slides. If you do provide HTML, include your content with inline CSS or <style> blocks. Design for 1920x1080 resolution. Google Fonts (Inter) is pre-loaded for typography. D3.js and Chart.js are available asynchronously (won't block page load) - use them if needed, but pure CSS/HTML is recommended for static presentations. For icons, use emoji (📊 📈 💡 🚀 ⚡ 🎯) or Unicode symbols instead of icon libraries.
                        
                        **🚨 IMPORTANT - Pre-configured Body Styles**: The slide template ALREADY includes base body styling in the <head>:
                        ```
                        body {
                            height: 1080px;
                            width: 1920px;
                            margin: 0;
                            padding: 0;
                        }
                        ```
                        **DO NOT** add conflicting body styles (like `height: 100vh`, `margin`, or `padding` on body) in your content - this will override the fixed dimensions and cause validation failures. Style your content containers instead.
                        
                        ## 📐 **Critical Dimension Requirements**

                        ### **Strict Limits**
                        *   **Slide Size**: MUST fit within 1920px width × 1080px height
                        *   **Validation**: Slides are automatically validated - both width AND height must not exceed limits
                        *   **Box-Sizing**: ALWAYS use `box-sizing: border-box` on containers with padding/margin to prevent overflow
                        
                        ### **Common Overflow Issues**
                        *   **Body Style Conflicts**: NEVER add `body { height: 100vh }` or other body styles in your content - the template already sets `body { height: 1080px; width: 1920px }`. Adding conflicting styles will break dimensions!
                        *   **Padding/Margin**: With default `box-sizing: content-box`, padding adds to total dimensions
                        *   **Example Problem**: `width: 100%` (1920px) + `padding: 80px` = 2080px total (exceeds limit!)
                        *   **Solution**: Use `box-sizing: border-box` so padding is included in the width/height
                        *   **CRITICAL HEIGHT ISSUE**: Containers with `height: 100%` (1080px) + `padding: 50px` top/bottom WILL cause ~100px overflow during validation! The scrollHeight measurement includes all content rendering, and flex centering with padding can push total height beyond 1080px. Use `max-height: 1080px` and reduce padding to 40px or less, OR ensure your content + padding stays well under 1080px.
                        
                        ### **Dimensions & Spacing**
                        *   **Slide Size**: 1920x1080 pixels (16:9)
                        *   **Container Padding**: Maximum 40px on all edges (avoid 50px+ to prevent height overflow) - ALWAYS use `box-sizing: border-box`!
                        *   **Section Gaps**: 40-60px between major sections  
                        *   **Element Gaps**: 20-30px between related items
                        *   **List Spacing**: Use `gap: 25px` in flex/grid layouts
                        *   **Line Height**: 1.5-1.8 for readability

                        ### **Typography**
                        Use `font_family` from **Theme Object**:
                        *   **Titles**: 48-72px (bold)
                        *   **Subtitles**: 32-42px (semi-bold)  
                        *   **Headings**: 28-36px (semi-bold)
                        *   **Body**: 20-24px (normal)
                        *   **Small**: 16-18px (light)

                        ### **Color Usage**
                        Use ONLY **Theme Object** colors:
                        *   **Primary**: Backgrounds, main elements
                        *   **Secondary**: Subtle backgrounds
                        *   **Accent**: Highlights, CTAs
                        *   **Text**: All text content

                        ### **Layout Principles**
                        *   Focus on 1-2 main ideas per slide
                        *   Limit to 3-5 bullet points max
                        *   Use `overflow: hidden` on containers
                        *   Grid columns: Use `gap: 50-60px`
                        *   Embrace whitespace - don't fill every pixel
                        *   **CRITICAL**: Always use `box-sizing: border-box` on main containers to prevent dimension overflow
                        
                        ### **🚨 PRESENTATION DESIGN vs WEBSITE DESIGN - CRITICAL**
                        **THIS IS A PRESENTATION SLIDE, NOT A WEBSITE:**
                        
                        **❌ FORBIDDEN - Website-like Patterns:**
                        *   **FORBIDDEN**: Multi-column grid layouts with cards/boxes (like 2x3, 3x2 grids of feature cards)
                        *   **FORBIDDEN**: Card-based layouts that look like website feature sections
                        *   **FORBIDDEN**: Responsive design patterns (`width: 100%`, `max-width`, `vw/vh` units, media queries, responsive breakpoints)
                        *   **FORBIDDEN**: Website navigation patterns (menus, headers, footers, sidebars)
                        *   **FORBIDDEN**: Scrolling content - everything must fit in 1920x1080 viewport
                        *   **FORBIDDEN**: CSS Grid with multiple columns/rows creating card grids
                        *   **FORBIDDEN**: Flexbox layouts that create website-like card sections
                        
                        **✅ REQUIRED - Presentation-style Layouts:**
                        *   **REQUIRED**: Centered, focused content - one main idea per slide
                        *   **REQUIRED**: Large, prominent titles (48-72px) centered or left-aligned at top
                        *   **REQUIRED**: Fixed pixel dimensions (e.g., `width: 800px`, `height: 400px`)
                        *   **REQUIRED**: Absolute or fixed positioning for precise layout control
                        *   **REQUIRED**: Fixed layouts that don't adapt to screen size
                        *   **REQUIRED**: Simple, clean layouts - think PowerPoint slide, not website
                        *   **REQUIRED**: If showing multiple items, use simple vertical lists or 2-3 large items side-by-side (NOT grid of 6+ cards)
                        
                        **Presentation Layout Examples:**
                        *   ✅ **GOOD**: Large centered title, single large image below, 3-5 bullet points
                        *   ✅ **GOOD**: Title at top, 2-3 large content sections side-by-side (each 500-600px wide)
                        *   ✅ **GOOD**: Title, large quote/testimonial, author name
                        *   ❌ **BAD**: Grid of 6 feature cards in 2x3 layout (looks like website)
                        *   ❌ **BAD**: Multiple small cards with icons and descriptions in grid
                        *   ❌ **BAD**: Website-style sections with headers and multiple columns
                        
                        **Think**: PowerPoint slide with centered/large content, NOT a responsive website with card grids
                        """
                    },
                    "presentation_title": {
                        "type": "string",
                        "description": "**OPTIONAL** - Main title of the presentation (used in HTML title and navigation). Defaults to 'Presentation' if not provided.",
                        "default": "Presentation"
                    }
                },
                "required": ["presentation_name", "slide_number", "slide_title", "content"],
                "additionalProperties": False
            }
        }
    })
    async def create_slide(
        self,
        presentation_name: str = None,
        slide_number: int = None,
        slide_title: str = None,
        content: str = None,
        presentation_title: str = "Presentation",
        **kwargs
    ) -> ToolResult:
        logger.info(f"[create_slide] Received params: presentation_name={repr(presentation_name)}, "
                    f"slide_number={repr(slide_number)}, slide_title={repr(slide_title)[:50] if slide_title else repr(slide_title)}, "
                    f"content_length={len(content) if content else 0}, kwargs={list(kwargs.keys())}")
        
        try:
            await self._ensure_sandbox()
            await self._ensure_presentations_dir()
                        
            # Log warning for any other unexpected arguments
            if kwargs:
                logger.warning(f"create_slide received unexpected arguments: {list(kwargs.keys())}. These will be ignored.")
            
            # Validation
            if not presentation_name:
                return self.fail_response("Presentation name is required.")
            
            if slide_number is None:
                return self.fail_response("Slide number is required.")
            
            try:
                slide_number = int(slide_number)
            except (TypeError, ValueError):
                return self.fail_response(f"Slide number must be an integer, got: {type(slide_number).__name__}")
            
            if slide_number < 1:
                return self.fail_response("Slide number must be 1 or greater.")
            
            if not slide_title:
                return self.fail_response("Slide title is required.")
            
            if not content:
                return self.fail_response("Slide content is required.")

            workflow_error = self._validate_slide_content_workflow(content)
            if workflow_error:
                return self.fail_response(workflow_error)

            asset_error = self._validate_slide_assets(content)
            if asset_error:
                return self.fail_response(asset_error)
            
            # Ensure presentation directory exists
            safe_name, presentation_path = await self._ensure_presentation_dir(presentation_name)
            theme_context = await self._load_presentation_theme_context(
                presentation_path=presentation_path,
                presentation_name=presentation_name,
                presentation_title=presentation_title,
            )
            effective_presentation_title = presentation_title
            if effective_presentation_title == "Presentation":
                effective_presentation_title = str(theme_context.get("deck_title") or presentation_name or "Presentation")
            
            # Auto-apply a curated visual shell when the model returns low-structure slide fragments.
            final_content = content
            semantics = self._extract_slide_semantics(content, slide_title)
            omit_visual = self._should_omit_slide_visual(content, semantics)
            should_auto_render = self._is_plain_slide_content(content) or self._should_auto_design_slide(content)
            if should_auto_render:
                if theme_context.get("template_source"):
                    rendered_template_content = await self._render_template_reference_slide(
                        presentation_path=presentation_path,
                        slide_content=content,
                        semantics=semantics,
                        theme_context=theme_context,
                        slide_number=slide_number,
                        slide_title=slide_title,
                        presentation_title=effective_presentation_title,
                        omit_visual=omit_visual,
                    )
                    if rendered_template_content:
                        final_content = rendered_template_content
                    else:
                        final_content = await self._apply_visual_baseline(
                            slide_content=content,
                            slide_title=slide_title,
                            presentation_name=presentation_name,
                            presentation_title=effective_presentation_title,
                            slide_number=slide_number,
                            theme_context=theme_context,
                            semantics=semantics,
                            omit_visual=omit_visual,
                        )
                else:
                    final_content = await self._apply_visual_baseline(
                        slide_content=content,
                        slide_title=slide_title,
                        presentation_name=presentation_name,
                        presentation_title=effective_presentation_title,
                        slide_number=slide_number,
                        theme_context=theme_context,
                        semantics=semantics,
                        omit_visual=omit_visual,
                    )

            # Parallel create_slide calls can race and overwrite metadata.
            # Serialize write operations per presentation to keep all slide entries.
            presentation_lock = await self._get_metadata_lock(presentation_path)
            async with presentation_lock:
                # Load latest metadata inside lock
                metadata = await self._load_presentation_metadata(presentation_path)
                metadata["presentation_name"] = presentation_name
                if presentation_title != "Presentation":  # Only update if explicitly provided
                    metadata["title"] = presentation_title
                elif not metadata.get("title") or metadata.get("title") == "Presentation":
                    metadata["title"] = presentation_name

                # Create slide HTML
                slide_html = self._create_slide_html(
                    slide_content=final_content,
                    slide_number=slide_number,
                    total_slides=0,  # Will be updated when regenerating navigation
                    presentation_title=effective_presentation_title
                )

                # Save slide file
                slide_filename = f"slide_{slide_number:02d}.html"
                slide_path = f"{presentation_path}/{slide_filename}"
                await self.sandbox.fs.upload_file(slide_html.encode(), slide_path)

                # Update metadata
                if "slides" not in metadata:
                    metadata["slides"] = {}

                metadata["slides"][str(slide_number)] = {
                    "title": slide_title,
                    "filename": slide_filename,
                    "file_path": f"{self.presentations_dir}/{safe_name}/{slide_filename}",
                    "preview_url": f"/workspace/{self.presentations_dir}/{safe_name}/{slide_filename}",
                    "created_at": datetime.now().isoformat()
                }

                # Save updated metadata
                await self._save_presentation_metadata(presentation_path, metadata)
            
            response_data = {
                "message": f"Slide {slide_number} '{slide_title}' created/updated successfully",
                "presentation_name": presentation_name,
                "presentation_path": f"{self.presentations_dir}/{safe_name}",
                "slide_number": slide_number,
                "slide_title": slide_title,
                "slide_file": f"{self.presentations_dir}/{safe_name}/{slide_filename}",
                "preview_url": f"/workspace/{self.presentations_dir}/{safe_name}/{slide_filename}",
                "total_slides": len(metadata["slides"]),
                "note": "Professional slide created with custom styling - designed for 1920x1080 resolution"
            }
            
            # Auto-validate slide dimensions
            # COMMENTED OUT: Height validation disabled
            # try:
            #     validation_result = await self.validate_slide(presentation_name, slide_number)
            #     
            #     # Append validation message to response
            #     if validation_result.success and validation_result.output:
            #         # output can be a dict or string
            #         if isinstance(validation_result.output, dict):
            #             validation_message = validation_result.output.get("message", "")
            #             if validation_message:
            #                 response_data["message"] += f"\n\n{validation_message}"
            #                 response_data["validation"] = {
            #                     "passed": validation_result.output.get("validation_passed", False),
            #                     "content_height": validation_result.output.get("actual_content_height", 0)
            #                 }
            #         elif isinstance(validation_result.output, str):
            #             response_data["message"] += f"\n\n{validation_result.output}"
            #     elif not validation_result.success:
            #         # If validation failed to run, append a warning
            #         logger.warning(f"Slide validation failed to execute: {validation_result.output}")
            #         response_data["message"] += f"\n\n⚠️ Note: Slide validation could not be completed."
            #         
            # except Exception as e:
            #     # Log the error but don't fail the slide creation
            #     logger.warning(f"Failed to auto-validate slide: {str(e)}")
            #     response_data["message"] += f"\n\n⚠️ Note: Slide validation could not be completed."
            
            return self.success_response(response_data)
            
        except Exception as e:
            return self.fail_response(f"Failed to create slide: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "list_slides",
            "description": "List all slides in a presentation, showing their titles and order",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_name": {
                        "type": "string",
                        "description": "Name of the presentation to list slides for"
                    }
                },
                "required": ["presentation_name"]
            }
        }
    })
    async def list_slides(self, presentation_name: str) -> ToolResult:
        """List all slides in a presentation"""
        try:
            await self._ensure_sandbox()
            
            if not presentation_name:
                return self.fail_response("Presentation name is required.")
            
            safe_name = self._sanitize_filename(presentation_name)
            presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
            
            # Load metadata
            metadata = await self._load_presentation_metadata(presentation_path)
            
            if not metadata.get("slides"):
                return self.success_response({
                    "message": f"No slides found in presentation '{presentation_name}'",
                    "presentation_name": presentation_name,
                    "slides": [],
                    "total_slides": 0
                })
            
            # Sort slides by number
            slides_info = []
            for slide_num_str, slide_data in metadata["slides"].items():
                slides_info.append({
                    "slide_number": int(slide_num_str),
                    "title": slide_data["title"],
                    "filename": slide_data["filename"],
                    "preview_url": slide_data["preview_url"],
                    "created_at": slide_data.get("created_at", "Unknown")
                })
            
            slides_info.sort(key=lambda x: x["slide_number"])
            
            return self.success_response({
                "message": f"Found {len(slides_info)} slides in presentation '{presentation_name}'",
                "presentation_name": presentation_name,
                "presentation_title": metadata.get("title", "Presentation"),
                "slides": slides_info,
                "total_slides": len(slides_info),
                "presentation_path": f"{self.presentations_dir}/{safe_name}"
            })
            
        except Exception as e:
            return self.fail_response(f"Failed to list slides: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "delete_slide",
            "description": "Delete a specific slide from a presentation",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_name": {
                        "type": "string",
                        "description": "Name of the presentation"
                    },
                    "slide_number": {
                        "type": "integer",
                        "description": "Slide number to delete (1-based)"
                    }
                },
                "required": ["presentation_name", "slide_number"]
            }
        }
    })
    async def delete_slide(self, presentation_name: str, slide_number: int) -> ToolResult:
        """Delete a specific slide from a presentation"""
        try:
            await self._ensure_sandbox()
            
            if not presentation_name:
                return self.fail_response("Presentation name is required.")
            
            if slide_number < 1:
                return self.fail_response("Slide number must be 1 or greater.")
            
            safe_name = self._sanitize_filename(presentation_name)
            presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
            
            # Load metadata
            metadata = await self._load_presentation_metadata(presentation_path)
            
            if not metadata.get("slides") or str(slide_number) not in metadata["slides"]:
                return self.fail_response(f"Slide {slide_number} not found in presentation '{presentation_name}'")
            
            # Get slide info before deletion
            slide_info = metadata["slides"][str(slide_number)]
            slide_filename = slide_info["filename"]
            
            # Delete slide file
            slide_path = f"{presentation_path}/{slide_filename}"
            try:
                await self.sandbox.fs.delete_file(slide_path)
            except:
                pass  # File might not exist
            
            # Remove from metadata
            del metadata["slides"][str(slide_number)]
            
            # Save updated metadata
            await self._save_presentation_metadata(presentation_path, metadata)
            
            return self.success_response({
                "message": f"Slide {slide_number} '{slide_info['title']}' deleted successfully",
                "presentation_name": presentation_name,
                "deleted_slide": slide_number,
                "deleted_title": slide_info['title'],
                "remaining_slides": len(metadata["slides"])
            })
            
        except Exception as e:
            return self.fail_response(f"Failed to delete slide: {str(e)}")




    @openapi_schema({
        "type": "function",
        "function": {
            "name": "list_presentations",
            "description": "List all available presentations in the workspace",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    async def list_presentations(self) -> ToolResult:
        """List all presentations in the workspace"""
        try:
            await self._ensure_sandbox()
            
            # Ensure presentations directory exists
            await self._ensure_presentations_dir()
            
            presentations_path = f"{self.workspace_path}/{self.presentations_dir}"
            presentations = []
            
            try:
                files = await self.sandbox.fs.list_files(presentations_path)
                
                for file_info in files:
                    # Use is_dir (correct attribute name) with fallback to is_directory for compatibility
                    is_dir = getattr(file_info, 'is_dir', False) or getattr(file_info, 'is_directory', False)
                    
                    if is_dir:
                        try:
                            # Skip hidden directories and special directories
                            if file_info.name.startswith('.'):
                                continue
                            
                            presentation_folder_path = f"{presentations_path}/{file_info.name}"
                            metadata = await self._load_presentation_metadata(presentation_folder_path)
                            
                            presentations.append({
                                "folder": file_info.name,
                                "title": metadata.get("title", file_info.name),
                                "description": metadata.get("description", ""),
                                "total_slides": len(metadata.get("slides", {})),
                                "created_at": metadata.get("created_at", "Unknown"),
                                "updated_at": metadata.get("updated_at", "Unknown")
                            })
                        except Exception as e:
                            # Log error but continue processing other presentations
                            logger.warning(f"Failed to load metadata for presentation '{file_info.name}': {str(e)}")
                            continue
                
                if presentations:
                    return self.success_response({
                        "message": f"Found {len(presentations)} presentation(s)",
                        "presentations": presentations,
                        "presentations_directory": f"{self.workspace_path}/{self.presentations_dir}",
                        "total_count": len(presentations)
                    })
                else:
                    return self.success_response({
                        "message": "No presentations found",
                        "presentations": [],
                        "presentations_directory": f"{self.workspace_path}/{self.presentations_dir}",
                        "note": "Create your first slide using create_slide"
                    })
                
            except Exception as e:
                # Check if it's a "not found" or "doesn't exist" error
                error_msg = str(e).lower()
                if any(phrase in error_msg for phrase in ['not found', 'no such file', 'does not exist', 'doesn\'t exist']):
                    # Directory doesn't exist yet - return empty list
                    return self.success_response({
                        "message": "No presentations found",
                        "presentations": [],
                        "presentations_directory": f"{self.workspace_path}/{self.presentations_dir}",
                        "note": "Create your first slide using create_slide"
                    })
                else:
                    # Log the actual error for debugging
                    logger.error(f"Error listing presentations in {presentations_path}: {str(e)}", exc_info=True)
                    return self.fail_response(f"Failed to list presentations: {str(e)}")
                
        except Exception as e:
            logger.error(f"Failed to list presentations: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to list presentations: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "delete_presentation",
            "description": "Delete an entire presentation and all its files",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_name": {
                        "type": "string",
                        "description": "Name of the presentation to delete"
                    }
                },
                "required": ["presentation_name"]
            }
        }
    })
    async def delete_presentation(self, presentation_name: str) -> ToolResult:
        """Delete a presentation and all its files"""
        try:
            await self._ensure_sandbox()
            
            if not presentation_name:
                return self.fail_response("Presentation name is required.")
            
            safe_name = self._sanitize_filename(presentation_name)
            presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
            
            try:
                await self.sandbox.fs.delete_folder(presentation_path)
                return self.success_response({
                    "message": f"Presentation '{presentation_name}' deleted successfully",
                    "deleted_path": f"{self.presentations_dir}/{safe_name}"
                })
            except Exception as e:
                return self.fail_response(f"Presentation '{presentation_name}' not found or could not be deleted: {str(e)}")
                
        except Exception as e:
            return self.fail_response(f"Failed to delete presentation: {str(e)}")


    # COMMENTED OUT: Height validation disabled
    # @openapi_schema({
    #     "type": "function",
    #     "function": {
    #         "name": "validate_slide",
    #         "description": "Validate a slide by reading its HTML code and checking if the content height exceeds 1080px. Use this tool to ensure slides fit within the standard presentation dimensions before finalizing them. This helps maintain proper slide formatting and prevents content overflow issues.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "presentation_name": {
    #                     "type": "string",
    #                     "description": "Name of the presentation containing the slide to validate"
    #                 },
    #                 "slide_number": {
    #                     "type": "integer",
    #                     "description": "Slide number to validate (1-based)"
    #                 }
    #             },
    #             "required": ["presentation_name", "slide_number"]
    #         }
    #     }
    # })
    # async def validate_slide(self, presentation_name: str, slide_number: int) -> ToolResult:
    #     """Validate a slide by rendering it in a browser and measuring actual content height"""
    #     try:
    #         await self._ensure_sandbox()
    #         
    #         if not presentation_name:
    #             return self.fail_response("Presentation name is required.")
    #         
    #         if slide_number < 1:
    #             return self.fail_response("Slide number must be 1 or greater.")
    #         
    #         safe_name = self._sanitize_filename(presentation_name)
    #         presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
    #         
    #         # Load metadata to verify slide exists
    #         metadata = await self._load_presentation_metadata(presentation_path)
    #         
    #         if not metadata.get("slides") or str(slide_number) not in metadata["slides"]:
    #             return self.fail_response(f"Slide {slide_number} not found in presentation '{presentation_name}'")
    #         
    #         # Get slide info
    #         slide_info = metadata["slides"][str(slide_number)]
    #         slide_filename = slide_info["filename"]
    #         
    #         # Create a Python script to measure the actual rendered height using Playwright
    #         measurement_script = f'''
    # import asyncio
    # import json
    # from playwright.async_api import async_playwright
    # 
    # async def measure_slide_height():
    #     async with async_playwright() as p:
    #         browser = await p.chromium.launch(
    #             headless=True,
    #             args=['--no-sandbox', '--disable-setuid-sandbox']
    #         )
    #         page = await browser.new_page(viewport={{"width": 1920, "height": 1080}})
    #         
    #         # Load the HTML file
    #         await page.goto('file:///workspace/{self.presentations_dir}/{safe_name}/{slide_filename}')
    #         
    #         # Wait for page to load
    #         await page.wait_for_load_state('networkidle')
    #         
    #         # Measure the actual content height
    #         dimensions = await page.evaluate("""
    #             () => {{
    #                 const body = document.body;
    #                 const html = document.documentElement;
    #                 
    #                 // Get the actual scroll height (total content height)
    #                 const scrollHeight = Math.max(
    #                     body.scrollHeight, body.offsetHeight,
    #                     html.clientHeight, html.scrollHeight, html.offsetHeight
    #                 );
    #                 
    #                 // Get viewport height
    #                 const viewportHeight = window.innerHeight;
    #                 
    #                 // Check if content overflows
    #                 const overflows = scrollHeight > 1080;
    #                 
    #                 return {{
    #                     scrollHeight: scrollHeight,
    #                     viewportHeight: viewportHeight,
    #                     overflows: overflows,
    #                     excessHeight: scrollHeight - 1080
    #                 }};
    #             }}
    #         """)
    #         
    #         await browser.close()
    #         return dimensions
    # 
    # result = asyncio.run(measure_slide_height())
    # print(json.dumps(result))
    # '''
    #         
    #         # Write the script to a temporary file in the sandbox
    #         script_path = f"{self.workspace_path}/.validate_slide_temp.py"
    #         await self.sandbox.fs.upload_file(measurement_script.encode(), script_path)
    #         
    #         # Execute the script
    #         try:
    #             result = await self.sandbox.process.exec(
    #                 f"/bin/sh -c 'cd {self.workspace_path} && python3 .validate_slide_temp.py'",
    #                 timeout=30
    #             )
    #             
    #             # Parse the result
    #             output = (getattr(result, "result", None) or getattr(result, "output", "") or "").strip()
    #             if not output:
    #                 raise Exception("No output from validation script")
    #             
    #             dimensions = json.loads(output)
    #             
    #             # Clean up the temporary script
    #             try:
    #                 await self.sandbox.fs.delete_file(script_path)
    #             except:
    #                 pass
    #             
    #         except Exception as e:
    #             # Clean up on error
    #             try:
    #                 await self.sandbox.fs.delete_file(script_path)
    #             except:
    #                 pass
    #             return self.fail_response(f"Failed to measure slide dimensions: {str(e)}")
    #         
    #         # Analyze results - simple pass/fail
    #         validation_passed = not dimensions["overflows"]
    #         
    #         validation_results = {
    #             "presentation_name": presentation_name,
    #             "presentation_path": presentation_path,
    #             "slide_number": slide_number,
    #             "slide_title": slide_info["title"],
    #             "actual_content_height": dimensions["scrollHeight"],
    #             "target_height": 1080,
    #             "validation_passed": validation_passed
    #         }
    #         
    #         # Add pass/fail message
    #         if validation_passed:
    #             validation_results["message"] = f"✓ Slide {slide_number} '{slide_info['title']}' validation passed. Content height: {dimensions['scrollHeight']}px"
    #         else:
    #             validation_results["message"] = f"✗ Slide {slide_number} '{slide_info['title']}' validation failed. Content height: {dimensions['scrollHeight']}px exceeds 1080px limit by {dimensions['excessHeight']}px"
    #             validation_results["excess_height"] = dimensions["excessHeight"]
    #         
    #         return self.success_response(validation_results)
    #         
    #     except Exception as e:
    #         return self.fail_response(f"Failed to validate slide: {str(e)}")

    async def _export_to_format(
        self, 
        presentation_name: str, 
        safe_name: str, 
        presentation_path: str, 
        format_type: str,
        store_locally: bool,
        client: "httpx.AsyncClient"
    ) -> Dict:
        """Internal helper to export to a specific format (pptx or pdf)"""
        try:
            convert_response = await client.post(
                f"{self.sandbox_url}/presentation/convert-to-{format_type}",
                json={
                    "presentation_path": presentation_path,
                    "download": not store_locally
                },
                timeout=180.0
            )
            
            if not convert_response.is_success:
                error_detail = convert_response.json().get("detail", "Unknown error") if convert_response.headers.get("content-type", "").startswith("application/json") else convert_response.text
                return {"success": False, "format": format_type, "error": f"{format_type.upper()} conversion failed: {error_detail}"}
                
        except Exception as e:
            return {"success": False, "format": format_type, "error": str(e)}
        
        # Process successful response
        try:
            
            if store_locally:
                result = convert_response.json()
                filename = result.get("filename")
                downloads_path = f"{self.workspace_path}/downloads/{filename}"
                presentation_file_path = f"{presentation_path}/{safe_name}.{format_type}"
                
                try:
                    file_content = await self.sandbox.fs.download_file(downloads_path)
                    await self.sandbox.fs.upload_file(file_content, presentation_file_path)
                except Exception:
                    pass
                
                return {
                    "success": True,
                    "format": format_type,
                    "file": f"{self.presentations_dir}/{safe_name}/{safe_name}.{format_type}",
                    "download_url": f"{self.workspace_path}/downloads/{filename}",
                    "total_slides": result.get("total_slides"),
                    "stored_locally": True
                }
            else:
                file_content = convert_response.content
                filename = f"{safe_name}.{format_type}"
                
                content_disposition = convert_response.headers.get("Content-Disposition", "")
                if "filename*=UTF-8''" in content_disposition:
                    encoded_name = content_disposition.split("filename*=UTF-8''")[1].split(';')[0]
                    filename = unquote(encoded_name)
                elif 'filename="' in content_disposition:
                    filename = content_disposition.split('filename="')[1].split('"')[0]
                
                return {
                    "success": True,
                    "format": format_type,
                    "filename": filename,
                    "file_size": len(file_content),
                    "stored_locally": False
                }
        except Exception as e:
            return {"success": False, "format": format_type, "error": str(e)}

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "export_presentation",
            "description": "Export a presentation to both PPTX and PDF formats simultaneously. Both exports run in parallel for faster completion. Files can be stored locally in the sandbox for repeated downloads, or returned directly. Use store_locally=True to enable the download button in the UI for repeated downloads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_name": {
                        "type": "string",
                        "description": "Name of the presentation to export"
                    },
                    "store_locally": {
                        "type": "boolean",
                        "description": "If True, stores the files in the sandbox at /workspace/downloads/ for repeated downloads. If False, returns the file content directly without storing.",
                        "default": True
                    }
                },
                "required": ["presentation_name"]
            }
        }
    })
    async def export_presentation(self, presentation_name: str, store_locally: bool = True) -> ToolResult:
        """Export presentation to both PPTX and PDF formats in parallel"""
        try:
            await self._ensure_sandbox()
            
            if not presentation_name:
                return self.fail_response("Presentation name is required.")
            
            safe_name = self._sanitize_filename(presentation_name)
            presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
            
            # Verify presentation exists
            metadata = await self._load_presentation_metadata(presentation_path)
            if not metadata.get("slides"):
                return self.fail_response(f"Presentation '{presentation_name}' not found or has no slides")
            
            total_slides = len(metadata.get("slides", {}))
            
            # Run both exports in parallel
            async with get_http_client() as client:
                pptx_task = self._export_to_format(
                    presentation_name, safe_name, presentation_path, "pptx", store_locally, client
                )
                pdf_task = self._export_to_format(
                    presentation_name, safe_name, presentation_path, "pdf", store_locally, client
                )
                
                pptx_result, pdf_result = await asyncio.gather(pptx_task, pdf_task)
            
            # Build response
            response_data = {
                "presentation_name": presentation_name,
                "total_slides": total_slides,
                "exports": {}
            }
            
            errors = []
            successes = []
            
            # Process PPTX result
            if pptx_result.get("success"):
                response_data["exports"]["pptx"] = {
                    "file": pptx_result.get("file"),
                    "download_url": pptx_result.get("download_url"),
                    "stored_locally": pptx_result.get("stored_locally")
                }
                successes.append("PPTX")
            else:
                errors.append(f"PPTX: {pptx_result.get('error')}")
            
            # Process PDF result
            if pdf_result.get("success"):
                response_data["exports"]["pdf"] = {
                    "file": pdf_result.get("file"),
                    "download_url": pdf_result.get("download_url"),
                    "stored_locally": pdf_result.get("stored_locally")
                }
                successes.append("PDF")
            else:
                errors.append(f"PDF: {pdf_result.get('error')}")
            
            # Set message based on results
            if len(successes) == 2:
                response_data["message"] = f"Presentation '{presentation_name}' exported to PPTX and PDF successfully"
                response_data["note"] = "Both files are stored in /workspace/downloads/ and can be downloaded repeatedly"
            elif len(successes) == 1:
                response_data["message"] = f"Presentation '{presentation_name}' exported to {successes[0]} successfully. {errors[0] if errors else ''}"
                response_data["partial_success"] = True
            else:
                return self.fail_response(f"Failed to export presentation: {'; '.join(errors)}")
            
            return self.success_response(response_data)
        
        except Exception as e:
            return self.fail_response(f"Failed to export presentation: {str(e)}")
