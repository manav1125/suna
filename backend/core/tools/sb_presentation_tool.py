from core.agentpress.tool import ToolResult, openapi_schema, tool_metadata
from core.sandbox.tool_base import SandboxToolsBase
from core.agentpress.thread_manager import ThreadManager
from core.utils.logger import logger
from core.services.http_client import get_http_client
from typing import List, Dict, Optional, Union, TYPE_CHECKING
from bs4 import BeautifulSoup, NavigableString
from html import escape
import json
import os
from datetime import datetime
import re
import asyncio
from urllib.parse import unquote

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
- If you call `load_template_design` with `presentation_name`, you MUST then use `populate_template_slide` for the copied slides (or `full_file_rewrite` only if you are intentionally doing a full structural rewrite).
- If you are using a built-in template, do NOT use `create_slide`; template workflows must stay in the copied template files.
- Never finish right after template copy; template copy is setup only, not final output.
- Every custom slide must include a clear visual structure (styled layout, chart/table/image/iconography), not plain text-only HTML.
- If using `../images/...` paths, ensure those files actually exist first.
- For custom slides, do NOT hotlink public internet image URLs directly inside `<img src="">`. Download them into `presentations/images/` first or use generated workspace assets.

**🚨 CRITICAL: This tool provides the create_slide function for presentations!**
- **Use create_slide ONLY for custom-theme presentations**
- **For template-based presentations, load the template with `presentation_name` and then use `populate_template_slide`**
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
        ]
        placeholder_hits = [marker for marker in placeholder_markers if marker in lowered]
        if placeholder_hits:
            return (
                "Slide content rejected because template placeholder text is still present "
                f"({', '.join(sorted(set(placeholder_hits)))}). Replace placeholder copy with researched content."
            )

        class_attr_count = len(re.findall(r"\bclass\s*=", slide_content, flags=re.IGNORECASE))
        inline_style_count = len(re.findall(r"\bstyle\s*=", slide_content, flags=re.IGNORECASE))
        has_style_block = "<style" in lowered

        if class_attr_count >= 4 and not has_style_block and inline_style_count < 2:
            return (
                "Slide content rejected because it relies on CSS classes without any accompanying styles. "
                "This usually means template HTML was copied into create_slide. For template-based presentations, "
                "call load_template_design with presentation_name and then update the copied slides with "
                "populate_template_slide. For custom slides, include a <style> block or inline styles so the slide renders correctly."
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

    def _dedupe_text_items(self, values: List[str]) -> List[str]:
        seen = set()
        deduped: List[str] = []
        for value in values:
            normalized = re.sub(r"\s+", " ", (value or "").strip())
            if not normalized:
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
        title_text = headings[0] if headings else clean_text(slide_title) or (fallback_texts[0] if fallback_texts else "Slide")

        narrative_pool = self._dedupe_text_items(paragraphs + quotes + fallback_texts)
        narrative_pool = [item for item in narrative_pool if item.lower() != title_text.lower()]

        lead = narrative_pool[0] if narrative_pool else ""
        supporting = [item for item in narrative_pool[1:] if item.lower() != lead.lower()][:3]

        key_points = bullets[:4]
        if not key_points:
            key_points = [item for item in supporting[:4] if len(item) <= 180]

        if not supporting and lead:
            supporting = [lead]

        kicker = ""
        if len(headings) > 1:
            kicker = headings[1]
        elif slide_title and clean_text(slide_title).lower() != title_text.lower():
            kicker = clean_text(slide_title)

        return {
            "title": title_text,
            "kicker": kicker,
            "lead": lead,
            "supporting": supporting,
            "key_points": key_points,
            "image": images[0] if images else None,
        }

    def _apply_visual_baseline(self, slide_content: str, slide_title: str) -> str:
        """Auto-design simple slide fragments into a polished fixed-layout presentation slide."""
        semantics = self._extract_slide_semantics(slide_content, slide_title)

        title_text = escape(str(semantics.get("title") or slide_title or "Slide"))
        kicker_text = escape(str(semantics.get("kicker") or ""))
        lead_text = escape(str(semantics.get("lead") or ""))
        supporting = [escape(item) for item in semantics.get("supporting", []) if item]
        key_points = [escape(item) for item in semantics.get("key_points", []) if item]
        image = semantics.get("image") if isinstance(semantics.get("image"), dict) else None
        image_src = escape((image or {}).get("src", ""), quote=True) if image else ""
        image_alt = escape((image or {}).get("alt", title_text), quote=True) if image else ""

        insight_cards = "".join(
            f"""
            <div class="vv-insight-card">
              <div class="vv-insight-index">{index:02d}</div>
              <p>{point}</p>
            </div>
            """
            for index, point in enumerate(key_points[:4], start=1)
        )

        supporting_cards = "".join(
            f'<div class="vv-support-card"><p>{paragraph}</p></div>'
            for paragraph in supporting[:2]
        )

        media_markup = ""
        if image_src:
            media_markup = f"""
            <div class="vv-media-column">
              <div class="vv-media-card">
                <img src="{image_src}" alt="{image_alt or title_text}" />
              </div>
            </div>
            """

        return f"""
<style>
  .vv-auto-slide {{
    width: 1920px;
    height: 1080px;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
    background:
      radial-gradient(circle at 12% 18%, rgba(34, 211, 238, 0.22), transparent 34%),
      radial-gradient(circle at 88% 14%, rgba(168, 85, 247, 0.18), transparent 28%),
      linear-gradient(135deg, #0f172a 0%, #111827 45%, #1e293b 100%);
    color: #f8fafc;
    padding: 72px;
  }}
  .vv-auto-slide * {{
    box-sizing: border-box;
  }}
  .vv-auto-slide .vv-frame {{
    position: relative;
    z-index: 2;
    width: 100%;
    height: 100%;
    border-radius: 36px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    background: linear-gradient(160deg, rgba(15, 23, 42, 0.82), rgba(30, 41, 59, 0.78));
    box-shadow: 0 30px 80px rgba(15, 23, 42, 0.32);
    display: grid;
    grid-template-columns: 1.12fr 0.88fr;
    gap: 36px;
    padding: 56px;
  }}
  .vv-auto-slide.no-media .vv-frame {{
    grid-template-columns: 1fr;
  }}
  .vv-auto-slide .vv-decor {{
    position: absolute;
    border-radius: 9999px;
    filter: blur(6px);
    opacity: 0.3;
  }}
  .vv-auto-slide .vv-decor.one {{
    width: 360px;
    height: 360px;
    top: -110px;
    right: -90px;
    background: radial-gradient(circle at 30% 30%, rgba(96, 165, 250, 0.9), rgba(59, 130, 246, 0.15) 72%);
  }}
  .vv-auto-slide .vv-decor.two {{
    width: 320px;
    height: 320px;
    left: -90px;
    bottom: -80px;
    background: radial-gradient(circle at 30% 30%, rgba(52, 211, 153, 0.85), rgba(16, 185, 129, 0.12) 72%);
  }}
  .vv-auto-slide .vv-copy-column {{
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: 24px;
  }}
  .vv-auto-slide .vv-kicker {{
    margin: 0;
    font-size: 16px;
    line-height: 1.2;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #7dd3fc;
    font-weight: 700;
  }}
  .vv-auto-slide h1 {{
    margin: 0;
    font-size: 72px;
    line-height: 0.98;
    letter-spacing: -0.04em;
    color: #f8fafc;
    font-weight: 800;
    max-width: 900px;
  }}
  .vv-auto-slide .vv-lead {{
    margin: 0;
    max-width: 820px;
    font-size: 28px;
    line-height: 1.45;
    color: #dbeafe;
    font-weight: 500;
  }}
  .vv-auto-slide .vv-insights {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-top: 10px;
  }}
  .vv-auto-slide .vv-insight-card,
  .vv-auto-slide .vv-support-card {{
    position: relative;
    min-height: 150px;
    padding: 22px 22px 24px;
    border-radius: 24px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(148, 163, 184, 0.08));
    backdrop-filter: blur(10px);
  }}
  .vv-auto-slide .vv-insight-index {{
    font-size: 14px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #93c5fd;
    margin-bottom: 12px;
    font-weight: 700;
  }}
  .vv-auto-slide .vv-insight-card p,
  .vv-auto-slide .vv-support-card p {{
    margin: 0;
    font-size: 23px;
    line-height: 1.45;
    color: #e2e8f0;
  }}
  .vv-auto-slide .vv-support-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
  }}
  .vv-auto-slide .vv-media-column {{
    min-width: 0;
    display: flex;
    align-items: stretch;
  }}
  .vv-auto-slide .vv-media-card {{
    width: 100%;
    min-height: 100%;
    border-radius: 30px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background:
      linear-gradient(180deg, rgba(30, 41, 59, 0.66), rgba(15, 23, 42, 0.92)),
      linear-gradient(135deg, rgba(34, 211, 238, 0.18), rgba(168, 85, 247, 0.16));
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 18px;
  }}
  .vv-auto-slide .vv-media-card img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 22px;
  }}
  .vv-auto-slide .vv-footer-bar {{
    position: absolute;
    left: 56px;
    right: 56px;
    bottom: 36px;
    height: 6px;
    border-radius: 9999px;
    background: linear-gradient(90deg, #22d3ee, #38bdf8, #34d399);
    opacity: 0.9;
  }}
</style>
<div class="vv-auto-slide {'with-media' if image_src else 'no-media'}">
  <div class="vv-decor one"></div>
  <div class="vv-decor two"></div>
  <div class="vv-frame">
    <div class="vv-copy-column">
      <p class="vv-kicker">{kicker_text or 'Research-backed narrative'}</p>
      <h1>{title_text}</h1>
      <p class="vv-lead">{lead_text or title_text}</p>
      {'<div class="vv-insights">' + insight_cards + '</div>' if insight_cards else ''}
      {'<div class="vv-support-grid">' + supporting_cards + '</div>' if supporting_cards else ''}
    </div>
    {media_markup}
    <div class="vv-footer-bar"></div>
  </div>
</div>
"""

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
        """Copy entire template directory structure to workspace using os.walk
        
        Returns:
            The presentation path in the workspace
        """
        await self._ensure_sandbox()
        await self._ensure_presentations_dir()
        
        template_path = os.path.join(self.templates_dir, template_name)
        safe_name = self._sanitize_filename(presentation_name)
        presentation_path = f"{self.workspace_path}/{self.presentations_dir}/{safe_name}"
        
        # Ensure presentation directory exists
        await self._ensure_presentation_dir(presentation_name)
        
        # Use os.walk to recursively copy all files
        copied_files = []
        for root, dirs, files in os.walk(template_path):
            # Calculate relative path from template root
            rel_path = os.path.relpath(root, template_path)
            
            # Create corresponding directory in workspace (if not root)
            if rel_path != '.':
                target_dir = os.path.join(presentation_path, rel_path)
                target_dir_path = target_dir.replace('\\', '/')  # Normalize path separators
                try:
                    await self.sandbox.fs.create_folder(target_dir_path, "755")
                except:
                    pass  # Directory might already exist
            else:
                target_dir_path = presentation_path
            
            # Copy all files
            for file in files:
                source_file = os.path.join(root, file)
                rel_file_path = os.path.relpath(source_file, template_path)
                target_file = os.path.join(presentation_path, rel_file_path).replace('\\', '/')
                
                try:
                    with open(source_file, 'rb') as f:
                        file_content = f.read()
                    await self.sandbox.fs.upload_file(file_content, target_file)
                    copied_files.append(rel_file_path)
                except Exception as e:
                    # Log error but continue with other files
                    print(f"Error copying {rel_file_path}: {str(e)}")
        
        # Update metadata.json with correct paths for the new presentation
        metadata = await self._load_presentation_metadata(presentation_path)
        template_metadata = self._load_template_metadata(template_name)
        
        # Update presentation name and preserve slides structure
        metadata["presentation_name"] = presentation_name
        metadata["title"] = presentation_name
        metadata["description"] = template_metadata.get("description", "")
        metadata["created_at"] = datetime.now().isoformat()
        metadata["updated_at"] = datetime.now().isoformat()
        
        # Update slide paths to match new presentation name
        if "slides" in template_metadata:
            updated_slides = {}
            for slide_num, slide_data in template_metadata["slides"].items():
                slide_filename = slide_data.get("filename", f"slide_{int(slide_num):02d}.html")
                updated_slides[str(slide_num)] = {
                    "title": f"Slide {slide_num}",
                    "filename": slide_filename,
                    "file_path": f"{self.presentations_dir}/{safe_name}/{slide_filename}",
                    "preview_url": f"{self.workspace_path}/{self.presentations_dir}/{safe_name}/{slide_filename}",
                    "created_at": datetime.now().isoformat()
                }
            metadata["slides"] = updated_slides
        
        # Save updated metadata
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
            "description": "Load complete design reference from a presentation template including all slide HTML and extracted style patterns (colors, fonts, layouts). If presentation_name is provided, the entire template will be copied to /workspace/presentations/{presentation_name}/ so you can preserve the template and then update visible text/image content with populate_template_slide. The visual design must remain identical; only text/data/image sources should change. Otherwise, use this template as DESIGN INSPIRATION ONLY - study the visual styling, CSS patterns, and layout structure to create your own original slides with similar aesthetics but completely different content.",
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
                response_data["required_next_tool"] = "populate_template_slide"
                response_data["note"] = f"Template copied to /workspace/{self.presentations_dir}/{safe_name}/. **CRITICAL**: Prefer populate_template_slide to replace visible text and image sources while preserving the template DOM/CSS. Use full_file_rewrite only if you intentionally need a full structural rewrite. The template's visual design must remain identical."
                response_data["usage_instructions"] = {
                    "purpose": "TEMPLATE COPIED TO WORKSPACE - Replace only content, preserve ALL design/styling",
                    "do": [
                        "Use populate_template_slide to replace visible text strings and image sources on the copied slides",
                        "ONLY modify text content inside HTML elements (headings, paragraphs, list items, data values)",
                        "Replace placeholder/example data with actual presentation content",
                        "Keep ALL <img>, <svg>, icon elements - only update src/alt attributes to point to your images",
                        "Keep the exact same number and type of elements (if template has 3 logo images, keep 3 <img> tags)",
                        "Preserve the content structure - if it's a list, keep it a list; if it's images, keep images",
                        "Use full_file_rewrite only as a fallback when a full slide rewrite is truly necessary"
                    ],
                    "dont": [
                        "NEVER modify <style> blocks or CSS styling - preserve them 100% exactly as-is",
                        "NEVER change class names, colors, fonts, gradients, or any design properties",
                        "NEVER change the HTML structure or layout patterns (flex, grid, positioning)",
                        "NEVER add/remove major structural elements (containers, sections, wrappers)",
                        "NEVER replace images with text - if template has <img> tags, keep them and only update src/alt",
                        "NEVER remove visual elements like images, icons, SVGs, or graphics - only update their content/sources",
                        "NEVER use create_slide tool - it's only for custom themes, NOT templates",
                        "NEVER change the visual design - colors, fonts, spacing, sizes must stay identical"
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
            "description": "Safely replace visible text and image sources inside a copied template slide while preserving the template DOM, CSS, classes, layout, and visual styling. Use this after load_template_design with presentation_name. **WHEN TO USE**: Preferred tool for template-based presentations. **WHEN TO SKIP**: Do not use for custom-theme decks - use create_slide instead. **🚨 PARAMETER NAMES**: Use EXACTLY these parameter names: `presentation_name` (REQUIRED), `slide_number` (REQUIRED), `slide_title` (REQUIRED), `text_replacements` (optional), `image_replacements` (optional), `presentation_title` (optional).",
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
            "description": "Create or update a single slide in a presentation. **WHEN TO USE**: This tool is ONLY for custom theme presentations (when no template is selected). **WHEN TO SKIP**: Do NOT use this tool for template-based presentations - use populate_template_slide on copied template files instead. **PARALLEL EXECUTION**: This function supports parallel execution - create ALL slides simultaneously by using create_slide multiple times in parallel for much faster completion. Each slide is saved as a standalone HTML file with 1920x1080 dimensions (16:9 aspect ratio). Slides are automatically validated to ensure both width (≤1920px) and height (≤1080px) limits are met. Use `box-sizing: border-box` on containers with padding to prevent dimension overflow. **CRITICAL**: For custom theme presentations, you MUST have completed Phase 3 (research, content outline, image search, and ALL image downloads) before using this tool. All styling MUST be derived from the custom color scheme and design elements defined in Phase 2. **IMAGE RULE**: Do not hotlink public internet image URLs directly in slide HTML - download them into presentations/images/ first. **PRESENTATION DESIGN NOT WEBSITE**: Use fixed pixel dimensions, absolute positioning, and fixed layouts - NO responsive design patterns. **🚨 PARAMETER NAMES**: Use EXACTLY these parameter names: `presentation_name` (REQUIRED), `slide_number` (REQUIRED), `slide_title` (REQUIRED), `content` (REQUIRED), `presentation_title` (optional). **❌ DO NOT USE**: `file_path` - this parameter does NOT exist!",
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
                        "description": """**REQUIRED** - HTML body content only (DO NOT include <!DOCTYPE>, <html>, <head>, or <body> tags - these are added automatically). Include your content with inline CSS or <style> blocks. Design for 1920x1080 resolution. Google Fonts (Inter) is pre-loaded for typography. D3.js and Chart.js are available asynchronously (won't block page load) - use them if needed, but pure CSS/HTML is recommended for static presentations. For icons, use emoji (📊 📈 💡 🚀 ⚡ 🎯) or Unicode symbols instead of icon libraries.
                        
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
            
            # Auto-apply a curated visual shell when the model returns low-structure slide fragments.
            final_content = content
            if self._is_plain_slide_content(content) or self._should_auto_design_slide(content):
                final_content = self._apply_visual_baseline(content, slide_title)

            # Parallel create_slide calls can race and overwrite metadata.
            # Serialize write operations per presentation to keep all slide entries.
            presentation_lock = await self._get_metadata_lock(presentation_path)
            async with presentation_lock:
                # Load latest metadata inside lock
                metadata = await self._load_presentation_metadata(presentation_path)
                metadata["presentation_name"] = presentation_name
                if presentation_title != "Presentation":  # Only update if explicitly provided
                    metadata["title"] = presentation_title

                # Create slide HTML
                slide_html = self._create_slide_html(
                    slide_content=final_content,
                    slide_number=slide_number,
                    total_slides=0,  # Will be updated when regenerating navigation
                    presentation_title=presentation_title
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
