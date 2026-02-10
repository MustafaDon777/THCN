import asyncio
import json
import os
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright



# --- 1. The Corrected CCNY Scraper ---

async def scrape_ccny(soup):
    """
    Targets the 'listing-item' grid structure from CCNY's news page.
    """
    news_data = []
    # Use the exact class from your HTML snippet
    items = soup.find_all("div", class_="listing-item")
    
    for item in items:
        # Title & Link (Inside h3.listing-item__title)
        title_tag = item.find("h3", class_="listing-item__title")
        if not title_tag: continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag: continue
        
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"https://www.ccny.cuny.edu{link}"

        # Image (Inside listing-item__image thumbnail)
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"https://www.ccny.cuny.edu{img_src}"

        # Description (Inside listing-item__teaser)
        desc_tag = item.find("div", class_="listing-item__teaser")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_bmcc(soup):
    """
    Targets the 'pl-blogcnt' structure found on the BMCC news page.
    """
    news_data = []
    # Each news entry is wrapped in this class
    items = soup.find_all("div", class_="pl-blogcnt")
    
    for item in items:
        # --- TITLE & LINK ---
        # Found inside h4.pl-title
        title_tag = item.find("h4", class_="pl-title")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # --- IMAGE ---
        # Found inside div.pl-thumbcnt
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # BMCC uses direct cloud storage links for images
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DESCRIPTION ---
        # Found in p.pl-text
        desc_tag = item.find("p", class_="pl-text")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # --- DATE (Optional Extra) ---
        # BMCC includes a date span inside the H4
        date_tag = title_tag.find("span", class_="pl-date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        if title:
            news_data.append({
                "title": title,
                "date": date_str,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })
    
    return news_data

async def scrape_csi(soup):
    """
    Targets the 'article' structure used by the Extra theme on CSIToday.
    """
    news_data = []
    # CSI uses <article> tags for almost all news items across different modules
    articles = soup.find_all("article")
    
    for article in articles:
        # --- TITLE & LINK ---
        title_tag = article.find(["h2", "h3"], class_="entry-title")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # --- IMAGE ---
        # CSI images are often in an <img> tag or a background-image style attribute
        img_src = ""
        img_tag = article.find("img")
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
        elif 'style' in article.attrs and 'background-image' in article['style']:
            # Fallback for slider items with background images
            style = article['style']
            start = style.find('url("') + 5
            end = style.find('")', start)
            img_src = style[start:end]

        # --- DESCRIPTION ---
        desc_tag = article.find("div", class_="excerpt")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # --- DATE ---
        date_tag = article.find("span", class_="updated")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # Avoid duplicates within the same page (slider + list often repeat)
        if not any(item['read_more_link'] == link for item in news_data):
            news_data.append({
                "title": title,
                "date": date_str,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })
    
    return news_data

async def scrape_guttman(soup):
    """
    Targets the 'entry-archive' structure used by Guttman Community College.
    """
    news_data = []
    # Articles are wrapped in <article> tags with specific classes
    articles = soup.find_all("article", class_="entry-archive")
    
    for article in articles:
        # --- TITLE & LINK ---
        # Guttman provides a direct link class 'entry-title-link'
        title_tag = article.find("a", class_="entry-title-link")
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        link = title_tag['href']

        # --- IMAGE ---
        # Guttman uses <picture> tags; we'll grab the primary <img> src
        img_src = ""
        img_tag = article.find("img", class_="entry-image")
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DATE ---
        # Uses <time> tag with a machine-readable datetime attribute
        time_tag = article.find("time", class_="entry-time")
        date_str = time_tag.get_text(strip=True) if time_tag else ""

        # --- DESCRIPTION (OPTIONAL) ---
        # Note: In the archive view, Guttman often relies on titles alone,
        # but check for entry-content just in case it's toggled on.
        desc_tag = article.find("div", class_="entry-summary")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_hunter(soup):
    """
    Targets the 'news-box' structure used by Hunter College.
    """
    news_data = []
    # Articles are wrapped in divs with the class 'news-box'
    articles = soup.find_all("div", class_="news-box")
    
    for article in articles:
        # --- LINK & HOVER BLOCK ---
        # The primary link wraps almost all content in the box
        link_tag = article.find("a", class_="hover-block")
        if not link_tag:
            continue
            
        link = link_tag.get('href', '')

        # --- TITLE ---
        # Hunter uses a div with class 'hed' for the headline
        title_tag = link_tag.find("div", class_="hed")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # --- IMAGE ---
        # Images are inside a div class 'hover-blockbg'
        img_src = ""
        img_tag = link_tag.find("img", class_="hover-blockimg")
        if img_tag:
            # Look for src, or data-src if it's lazy-loaded
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DATE ---
        # Date is in a div with class 'date'
        date_tag = link_tag.find("div", class_="date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # The description is usually a direct <p> tag inside the link_tag
        desc_tag = link_tag.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data


async def scrape_john_jay(soup):
    """
    Targets the 'teaser-card' structure from John Jay's news page.
    """
    news_data = []
    base_url = "https://www.jjay.cuny.edu"
    
    # Each news item is wrapped in a div with these classes
    articles = soup.find_all("div", class_="teaser-card")
    
    for article in articles:
        # --- TITLE & LINK ---
        title_container = article.find("div", class_="card__title")
        title_tag = title_container.find("a") if title_container else None
        
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        link = title_tag.get('href', '')
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # --- IMAGE ---
        img_tag = article.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"{base_url}{img_src}"

        # --- DATE ---
        date_tag = article.find("div", class_="card__meta")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": "" # John Jay overview lacks a teaser paragraph
        })
    
    return news_data

async def scrape_kbcc(soup):
    """
    Targets the 'row card g-0' structure from KBCC's news page.
    Note: Images are stored in CSS inline styles.
    """
    news_data = []
    base_url = "https://www.kbcc.cuny.edu"
    
    # Each news item is a div with these classes
    items = soup.find_all("div", class_="row card g-0")
    
    for item in items:
        # --- TITLE & LINK ---
        # Found inside an <h2> with class 'h3'
        title_tag = item.find("h2", class_="h3")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # --- IMAGE (CSS Background Style) ---
        img_src = ""
        # KBCC uses a div with class 'card-img-top' and an inline style for the image
        img_div = item.find("div", class_="card-img-top")
        if img_div and img_div.has_attr('style'):
            style_str = img_div['style']
            # Regex to find the path inside url('...')
            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_str)
            if match:
                img_src = match.group(1)
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"

        # --- DATE ---
        # Found in a list item with class 'pub-date'
        date_tag = item.find("li", class_="pub-date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # The provided HTML has an empty <p></p> for descriptions
        desc_tag = item.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_cuny_law(soup):
    """
    Targets the 'post-list-container' structure from CUNY Law's newsroom.
    """
    news_data = []
    # Articles are list items inside the post-list-container
    container = soup.find("ul", class_="post-list-container")
    if not container:
        return news_data
        
    items = container.find_all("li")
    
    for item in items:
        # --- TITLE & LINK ---
        # The title is in an <h2> tag
        title_tag = item.find("h2")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a")
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag.get('href', '')

        # --- IMAGE ---
        # CUNY Law uses a div with 'data-bg-image' containing the URL
        img_div = item.find("div", class_="newsroom-post-img")
        img_src = ""
        if img_div:
            # We prioritize data-bg-image as it usually contains the clean URL
            raw_bg = img_div.get('data-bg-image') or img_div.get('style', '')
            # Extract URL if it's wrapped in url('...')
            if "url(" in raw_bg:
                img_src = raw_bg.split("url('")[1].split("')")[0]
            else:
                img_src = raw_bg

        # --- DESCRIPTION ---
        # Descriptions are in a div with class 'entry-content'
        desc_tag = item.find("div", class_="entry-content")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # --- DATE ---
        # Note: The provided HTML snippet for CUNY Law does not 
        # include visible date strings in the list view.
        date_str = ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_lehman(soup):
    """
    Targets the 'course-listing' structure from Lehman College's news search.
    """
    news_data = []
    base_url = "https://www.lehman.cuny.edu"
    
    # Each news item is a div with class "course-listing"
    items = soup.find_all("div", class_="course-listing")
    
    for item in items:
        # --- TITLE & LINK ---
        # Lehman uses a specific class for the title paragraph
        title_tag = item.find("p", class_="newsModuleListing__block__desc__title")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a")
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag.get('href', '')
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # --- IMAGE ---
        # Image is inside newsModuleListing__block__img
        img_container = item.find("div", class_="newsModuleListing__block__img")
        img_src = ""
        if img_container:
            img_tag = img_container.find("img")
            if img_tag:
                img_src = img_tag.get('src', '')
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"

        # --- DATE ---
        # Date is in a paragraph with a specific descriptor class
        date_tag = item.find("p", class_="newsModuleListing__block__desc__date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # Lehman uses 'newsModuleListing__block__desc__text' for the summary
        desc_tag = item.find("p", class_="newsModuleListing__block__desc__text")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_macaulay(soup):
    """
    Targets the 'sub-feature-double__content' grid from Macaulay's news page.
    """
    news_data = []
    # Macaulay news items are inside these specific content divs
    items = soup.find_all("div", class_="sub-feature-double__content")
    
    for item in items:
        # --- TITLE & LINK ---
        # The title is in an <h3> tag
        title_tag = item.find("h3")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        # Macaulay links are usually absolute, but we check just in case
        if link.startswith('/'):
            link = f"https://macaulay.cuny.edu{link}"

        # --- IMAGE ---
        # Image is inside the sub-feature-double__image-figure
        img_tag = item.find("img", class_="sub-feature-double__content--image")
        img_src = ""
        if img_tag:
            # Prioritize 'src', but handle 'data-src' if lazy-loading is active
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"https://macaulay.cuny.edu{img_src}"

        # --- DATE ---
        # Macaulay uses the <time> tag for publication dates
        date_tag = item.find("time", class_="calendar-event__time--small")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # Found in the <p> tag within the content div
        desc_tag = item.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data


async def scrape_medgar_evers(soup):
    """
    Targets the 'card' structure from Medgar Evers College's news archive.
    """
    news_data = []
    
    # Each news item is contained within a div with class 'card'
    # These are usually wrapped in col-md-4 or similar grid columns
    items = soup.find_all("div", class_="card")
    
    for item in items:
        # --- TITLE & LINK ---
        # The title is in an <h2>, and the link uses the 'stretched-link' class
        title_tag = item.find("h2")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # --- IMAGE ---
        # MEC images are siblings to the card-body inside the card
        img_tag = item.find("img", class_="wp-post-image")
        img_src = ""
        if img_tag:
            # MEC uses standard src, but we check for data-src as a fallback
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DATE ---
        # Date is located in a <small> tag with class 'text-muted'
        date_tag = item.find("small", class_="text-muted")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # MEC puts the summary in a <p> with class 'card-text'
        # Note: Sometimes there are nested <p> tags here
        desc_container = item.find("p", class_="card-text")
        if desc_container:
            # Get text from the container or the first paragraph inside it
            inner_p = desc_container.find("p")
            description = inner_p.get_text(strip=True) if inner_p else desc_container.get_text(strip=True)
        else:
            description = ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_qcc(soup):
    """
    Targets the 'newsSection' structure from QCC's news page.
    """
    news_data = []
    base_url = "https://www.qcc.cuny.edu/news/"
    
    # Each news item is wrapped in a section with class 'newsSection'
    items = soup.find_all("section", class_="newsSection")
    
    for item in items:
        # 1. Title & Link (Found inside <p class="article"><a>)
        p_tag = item.find("p", class_="article")
        if not p_tag:
            continue
            
        a_tag = p_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # Absolute Link Formatting
        if not link.startswith(('http://', 'https://')):
            link = f"{base_url}{link}"

        # 2. Date Extraction
        # The date is usually text after a <br> tag inside the p.article
        date_text = ""
        if p_tag:
            # We get the text but exclude the text that was inside the <a> tag
            full_text = p_tag.get_text("|", strip=True)
            parts = full_text.split("|")
            if len(parts) > 1:
                date_text = parts[-1] # Usually the last part after the title

        # 3. Image Extraction
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src', '')
            # Handle relative image paths like "images/..." or "../images/..."
            if img_src and not img_src.startswith(('http://', 'https://')):
                # Simple join for QCC structure
                img_src = f"https://www.qcc.cuny.edu/news/{img_src.replace('../', '')}"

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "date": date_text,
            "description": "" # QCC news listing doesn't provide a teaser/summary text
        })
    
    return news_data

async def scrape_sps(soup):
    """
    Targets the 'listing-item' structure from CUNY SPS news page.
    """
    news_data = []
    base_url = "https://sps.cuny.edu"
    
    # Find all news row containers
    items = soup.find_all("div", class_="listing-item")
    
    for item in items:
        # 1. Title & Link
        title_tag = item.find("h3", class_="listing-item__title")
        if not title_tag: 
            continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag: 
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Date (Unique to the SPS snippet)
        date_tag = item.find("span", class_="date-display-single")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # 3. Image
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # SPS uses standard 'src', but we check data-src just in case of lazy loading
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"{base_url}{img_src}"

        # 4. Description (Deeply nested in SPS)
        # It's inside listing-item__teaser -> field__item
        desc_tag = item.find("div", class_="listing-item__teaser")
        description = ""
        if desc_tag:
            # get_text() will pull from the nested 'body' div automatically
            description = desc_tag.get_text(strip=True)

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_laguardia(soup):
    """
    Targets the Elementor grid structure from LaGuardia's news page.
    """
    news_data = []
    # In your HTML, each news item is contained within an <article> tag 
    # with the class 'elementor-post'
    items = soup.find_all("article", class_="elementor-post")
    
    for item in items:
        # 1. Title & Link (Inside p.elementor-post__title)
        title_container = item.find("p", class_="elementor-post__title")
        if not title_container:
            continue
        
        a_tag = title_container.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # 2. Image (Elementor usually puts the image in a div called 'elementor-post__thumbnail')
        # Even if not present in your snippet, this handles 'has-post-thumbnail' cases.
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Check for standard src or lazy-loaded data-src
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            
        # 3. Date (Inside span.elementor-post-date)
        date_tag = item.find("span", class_="elementor-post-date")
        date_text = date_tag.get_text(strip=True) if date_tag else ""

        # 4. Description (Elementor uses 'elementor-post__excerpt')
        # Note: Your snippet didn't show excerpts, but they often appear in this class.
        desc_tag = item.find("div", class_="elementor-post__excerpt")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date_text  # Added date as it's prominent in LaGuardia's layout
        })
    
    return news_data

async def scrape_cuny_sph(soup):
    """
    Targets the 'list-view-container' structure from CUNY SPH news page.
    """
    news_data = []
    # Each news entry is wrapped in this container
    items = soup.find_all("div", class_="list-view-container")
    
    for item in items:
        # 1. Title & Link (Inside div.news-title)
        title_container = item.find("div", class_="news-title")
        if not title_container:
            continue
            
        a_tag = title_container.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # 2. Image (Inside div.news-img)
        img_container = item.find("div", class_="news-img")
        img_src = ""
        if img_container:
            img_tag = img_container.find("img")
            if img_tag:
                # Use src, or data-src for lazy-loaded images
                img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # 3. Description (Inside div.news-des-indent_inner)
        desc_tag = item.find("div", class_="news-des-indent_inner")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 4. Date (Optional, but available in this specific HTML)
        date_tag = item.find("div", class_="news-date")
        date = date_tag.get_text(strip=True) if date_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date
        })
    
    return news_data


async def scrape_york(soup):
    """
    Targets the 'advanced-item' structure from York College's news page.
    """
    news_data = []
    base_url = "https://www.york.cuny.edu"
    
    # Each news entry is contained within an 'advanced-item' div
    items = soup.find_all("div", class_="advanced-item")
    
    for item in items:
        # 1. Title & Link (Inside h3.threelines)
        title_tag = item.find("h3", class_="threelines")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Image (Inside advancedImage div)
        img_src = ""
        img_container = item.find("div", class_="advancedImage")
        if img_container:
            img_tag = img_container.find("img")
            if img_tag:
                # Prefer src, but check data-src if they use lazy loading
                img_src = img_tag.get('src') or img_tag.get('data-src', '')
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"

        # 3. Date (Inside p.effectiveDate)
        date_tag = item.find("p", class_="effectiveDate")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # 4. Description (The paragraph after the date)
        # It's usually a generic <p> tag without a specific class in this layout
        desc_tag = item.find("div", class_="nine wide column")
        description = ""
        if desc_tag:
            # Find the paragraph that is NOT the effectiveDate
            p_tags = desc_tag.find_all("p")
            for p in p_tags:
                if "effectiveDate" not in p.get("class", []):
                    description = p.get_text(strip=True)
                    break

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_hostos(soup):
    """
    Targets the 'event-info' structure from Hostos news page.
    """
    news_data = []
    base_url = "https://www.hostos.cuny.edu"
    
    # Each news entry is contained within an <li> inside the event-box
    items = soup.find_all("li")
    
    for item in items:
        # Check if this <li> actually contains news (look for event-info)
        info_div = item.find("div", class_="event-info")
        if not info_div:
            continue
            
        # 1. Title & Link
        a_tag = info_div.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Date (Optional but useful for Hostos)
        time_tag = item.find("time")
        date_str = time_tag.get('datetime') if time_tag else ""

        # 3. Description & Image (Both are inside the 'location' span)
        desc_container = info_div.find("span", class_="location")
        description = ""
        img_src = ""
        
        if desc_container:
            # Find image if it exists
            img_tag = desc_container.find("img")
            if img_tag:
                img_src = img_tag.get('src', '')
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"
                if len(img_src)>400:
                    img_src =""
            
            # Get text description (excluding the text inside the <h3> if it leaked in)
            # We strip whitespace and common &nbsp; artifacts
            description = desc_container.get_text(" ", strip=True)
            
        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_brooklyn_college(soup):
    """
    Targets the 'news-item' structure from Brooklyn College's news page.
    """
    news_data = []
    # Each news entry is contained within a div with class 'news-item'
    items = soup.find_all("div", class_="news-item")
    
    for item in items:
        # Title & Link (Inside the h3 tag)
        title_tag = item.find("h3")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # Image extraction (Inside the picture/img tag)
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Prefer src, fallback to data-src if they use lazy loading later
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # Description (Inside the <p> tag within the text column)
        desc_tag = item.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_bcc(soup):
    """
    Targets the 'mk-blog-thumbnail-item' structure from BCC's news page.
    """
    news_data = []
    # BCC uses article tags for each news item
    items = soup.find_all("article", class_="mk-blog-thumbnail-item")
    
    for item in items:
        # Title & Link (Inside h3.the-title)
        title_tag = item.find("h3", class_="the-title")
        if not title_tag: 
            continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag: 
            continue
        
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # Image (Inside div.featured-image)
        # Note: BCC uses a specific 'blog-image' class
        img_tag = item.find("img", class_="blog-image")
        img_src = ""
        if img_tag:
            # Prioritize the main src, fallback to data-mk-image-src-set if needed
            img_src = img_tag.get('src', '')

        # Description (Inside div.the-excerpt)
        desc_tag = item.find("div", class_="the-excerpt")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_baruch(soup):
    """
    Targets the 'post-item' structure from Baruch College's news page.
    """
    news_data = []
    # Baruch uses 'post-item' for both the main featured story and supporting stories
    items = soup.find_all("div", class_="post-item")
    
    for item in items:
        # 1. Title & Link (Inside a.post-title-link)
        title_tag = item.find("a", class_="post-title-link")
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        link = title_tag.get('href', '')

        # 2. Image (Inside image-container -> img)
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Prioritize src, fallback to data-src
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # 3. Description 
        # In the provided HTML, description text is inside a <div> within body-content, 
        # but it doesn't have a unique class. It follows the title link.
        description = ""
        body_content = item.find("div", class_="body-content")
        if body_content:
            # Find the div that contains the summary text (usually after the title <a> tag)
            desc_tag = body_content.find("div")
            if desc_tag:
                description = desc_tag.get_text(strip=True)

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data


async def scrape_graduate_center(soup):
    """
    Targets the 'card--news' article structure from CUNY Graduate Center's news page.
    """
    news_data = []
    base_url = "https://www.gc.cuny.edu"
    
    # Each news item is contained within an <article> tag with these classes
    items = soup.find_all("article", class_="card--news")
    
    for item in items:
        # 1. Title & Link (Inside h3.card__title)
        title_tag = item.find("h3", class_="card__title")
        if not title_tag:
            continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
        
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Image (Inside the <picture> tag)
        # We prioritize the 'src' of the <img> tag inside the <picture> element
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Check for src, then fallback to data-src
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"{base_url}{img_src}"

        # 3. Description (Inside p.card__summary)
        desc_tag = item.find("p", class_="card__summary")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 4. Date (Inside span.date)
        date_tag = item.find("span", class_="date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date_str
        })
    
    return news_data

async def scrape_citytech(soup):
    """
    Targets the AngularJS-based news structure from City Tech's news page.
    """
    news_data = []
    base_url = "https://www.citytech.cuny.edu"
    
    # Each news item is contained within this class
    # Note: Using lambda to find classes that contain 'c-margin-b-10' as they are repeat items
    items = soup.find_all("div", class_=lambda x: x and "c-margin-b-10" in x)

    for item in items:
        # 1. Title & Link
        # Titles are inside h1 with specific font classes
        title_tag = item.find("h1", class_="c-title")
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        
        # Link logic: Usually found in an <a> around the image or title
        # In the provided HTML, the <a> might be higher up or dynamic.
        # If the tag isn't explicitly in the snippet, we look for any link in the container.
        a_tag = item.find("a", href=True)
        link = a_tag['href'] if a_tag else ""
        if link and link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Image (Extracted from inline style background-image)
        img_src = ""
        img_div = item.find("div", class_="c-bg-img-center")
        if img_div and img_div.get('style'):
            style_str = img_div['style']
            # Regex to extract the URL from: background-image: url("...")
            match = re.search(r'url\("?(.+?)"?\)', style_str)
            if match:
                img_src = match.group(1)
                # If it's a relative path starting with 'dashboard'
                if not img_src.startswith('http'):
                    img_src = f"{base_url}/{img_src.lstrip('/')}"

        # 3. Description
        desc_tag = item.find("div", class_="c-desc")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Avoid appending empty entries if title is missing
        if title:
            news_data.append({
                "title": title,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })

    return news_data

async def scrape_qc(soup):
    """
    Targets the accordion 'et_pb_toggle' structure from Queens College's news page.
    """
    news_data = []
    
    # 1. Find all monthly accordion/toggle sections
    toggles = soup.find_all("div", class_="et_pb_toggle")
    
    for toggle in toggles:
        # Get the month/year from the toggle title if needed
        # month_text = toggle.find("h5", class_="et_pb_toggle_title").get_text(strip=True)
        
        # 2. Find the content area where the links live
        content_area = toggle.find("div", class_="et_pb_toggle_content")
        if not content_area:
            continue
            
        # 3. Find all <a> tags within the toggle
        # Each link usually represents a news item
        links = content_area.find_all("a", href=True)
        
        for a_tag in links:
            title = a_tag.get_text(strip=True)
            link = a_tag['href']
            
            # Basic validation: ignore very short text or empty links
            if not title or len(title) < 5:
                continue

            # Queens College often uses absolute URLs, but we handle relative just in case
            if link.startswith('/'):
                link = f"https://www.qc.cuny.edu{link}"

            # 4. Extract Description
            # In this HTML, the date is often in a <p> or <span> tag immediately 
            # preceding the <a> tag or its parent.
            parent_p = a_tag.find_parent("p")
            description = ""
            if parent_p:
                # Try to find the date/teaser text in the paragraph preceding this one
                prev_p = parent_p.find_previous_sibling("p")
                if prev_p:
                    description = prev_p.get_text(strip=True)

            # 5. Image (Note: The QC archive list usually doesn't have thumbnails)
            img_src = ""
            
            news_data.append({
                "title": title,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })
    
    return news_data

async def scrape_newmark_j_school(soup):
    """
    Targets the 'item-loop--card' structure from the CUNY Journalism news page.
    """
    news_data = []
    # The main container for each news item
    items = soup.find_all("article", class_="item-loop")

    for item in items:
        # Link & Title
        # The <a> tag wraps the entire card
        a_tag = item.find("a", class_="item-loop--card__link")
        if not a_tag:
            continue
            
        link = a_tag.get('href', '')
        
        # Title (Inside h2.card__title)
        title_tag = item.find("h2", class_="card__title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # Image (Handled via inline style background-image)
        img_src = ""
        img_div = item.find("div", class_="card__img")
        if img_div and img_div.get('style'):
            style_str = img_div['style']
            # Regex to extract the URL inside url('...')
            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_str)
            if match:
                img_src = match.group(1)

        # Description (Inside p.card__desc)
        desc_tag = item.find("p", class_="card__desc")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Meta/Date (Optional, but useful for this site)
        meta_tag = item.find("span", class_="card__meta")
        date = meta_tag.get_text(strip=True) if meta_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date
        })

    return news_data

async def scrape_slu(soup):
    """
    Targets the 'vc_grid-item' structure from SLU CUNY's news page.
    """
    news_data = []
    # Each news card is contained within this class
    items = soup.find_all("div", class_="vc_grid-item")
    
    for item in items:
        # 1. Extract Title and Link
        # Found inside the 'vc_gitem-post-data-source-post_title' container
        title_container = item.find("div", class_="vc_gitem-post-data-source-post_title")
        if not title_container:
            continue
            
        a_tag = title_container.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        # Ensure absolute URL
        if link.startswith('/'):
            link = f"https://slu.cuny.edu{link}"

        # 2. Extract Image Reference
        # Images are often inside a figure or the wpb_single_image container
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
        
        # If no <img> exists, SLU sometimes uses background-images on the link
        if not img_src:
            img_container = item.find("a", class_="vc_gitem-link")
            if img_container and 'style' in img_container.attrs:
                # Basic parse for background-image: url(...)
                style = img_container['style']
                if 'url(' in style:
                    img_src = style.split('url(')[1].split(')')[0].replace('"', '').replace("'", "")

        if img_src and img_src.startswith('/'):
            img_src = f"https://slu.cuny.edu{img_src}"

        # 3. Extract Description
        # Found inside the 'vc_gitem-post-data-source-post_excerpt' container
        desc_container = item.find("div", class_="vc_gitem-post-data-source-post_excerpt")
        description = ""
        if desc_container:
            # Get text and clean up whitespace/newlines
            description = desc_container.get_text(strip=True)

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

# -------------------------------------------------------------
#
#
# -------------------------------------------------------------
# [Include scrape_ccny and scrape_bmcc functions here]

async def run_college_scraper(college_urls, use_keywords=True):
    html_folder = "colleges_htmls"
    os.makedirs(html_folder, exist_ok=True)
    
    json_file = 'colleges_data.json'

    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                final_output = json.load(f)
            except json.JSONDecodeError:
                final_output = {}
    else:
        final_output = {}

    scraper_dispatch = {
        "ccny": scrape_ccny, "bmcc": scrape_bmcc, "csi": scrape_csi,
        "guttman": scrape_guttman, "hunter": scrape_hunter, "jjay": scrape_john_jay,
        "kbcc": scrape_kbcc, "law": scrape_cuny_law, "lehman": scrape_lehman,
        "macaly": scrape_macaulay, "mec": scrape_medgar_evers, "qcc": scrape_qcc,
        "sps": scrape_sps, "lagrdia": scrape_laguardia, "sph": scrape_cuny_sph,
        "york": scrape_york, "hostos": scrape_hostos, "broklyn": scrape_brooklyn_college,
        "bcc": scrape_bcc, "baruc": scrape_baruch, "gc": scrape_graduate_center,
        "ct": scrape_citytech, "qc": scrape_qc, "soj": scrape_newmark_j_school,
        "slu": scrape_slu
    }
    
    KEYWORDS = ["student", "research", "opportunity", "program", "event", "hackathon", "stem", "arts", "internship", "workshop"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        await context.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,pdf}", lambda route: route.abort())
        
        page = await context.new_page()
        numOfNews = 20

        for college_id, urls in college_urls.items():
            session_college_data = []
            seen_descriptions = set()
            
            for index, url in enumerate(urls):
                if len(session_college_data) >= 50:
                    break

                for attempt in range(3):
                    try:
                        print(f"Scraping {college_id} | Page {index + 1} (Attempt {attempt + 1})...")
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000) 
                        
                        html_content = await page.content()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        if college_id in scraper_dispatch:
                            new_items = await scraper_dispatch[college_id](soup)
                            for item in new_items:
                                if len(session_college_data) >= numOfNews:
                                    break
                                
                                desc = item.get('description', '').lower().strip()
                                title = item.get('title', '').lower().strip()
                                combined_text = f"{title} {desc}"
                                
                                if not desc or desc in seen_descriptions:
                                    continue
                                    
                                if not use_keywords or any(kw in combined_text for kw in KEYWORDS):
                                    session_college_data.append(item)
                                    seen_descriptions.add(desc)
                        break 
                    except Exception as e:
                        if attempt < 2: continue
                        print(f"   -> Final Error on {url}: {e}")
                        break 

            # --- UPDATED MERGING LOGIC ---
            existing_data = final_output.get(college_id, [])
            
            if len(session_college_data) > len(existing_data):
                # Scenario 1: New scrape is strictly better/longer
                final_output[college_id] = session_college_data
                print(f"   -> REPLACED {college_id}: Found more news ({len(session_college_data)} items).")
            
            elif session_college_data:
                # Scenario 2: New news is less, but we want to prepend the new ones to the old ones
                # We use a set of existing titles or descriptions to ensure we don't add duplicates
                existing_titles = {i.get('title', '').lower().strip() for i in existing_data}
                
                # Filter session data to only include items not already in the JSON
                fresh_items = [item for item in session_college_data 
                               if item.get('title', '').lower().strip() not in existing_titles]
                
                if fresh_items:
                    # Prepend fresh items to the beginning of the old data
                    updated_list = fresh_items + existing_data
                    # Truncate to the top 10 (or whatever your "top number" limit is)
                    final_output[college_id] = updated_list[:numOfNews]
                    print(f"   -> MERGED {college_id}: Added {len(fresh_items)} new items to top of list.")
                else:
                    print(f"   -> NO CHANGE {college_id}: No strictly new news found.")
            else:
                print(f"   -> SKIPPED {college_id}: No data found in this session.")

        await browser.close()

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4)

    print(f"\nScraping Complete. Results saved to {json_file}")

if __name__ == "__main__":
    # Example showing multiple pages for BMCC
    target_urls = {
        "slu":[
            "https://slu.cuny.edu/news/"
        ],
        "soj":[
            "https://www.journalism.cuny.edu/category/news/"
        ],
        "bcc": [
            "https://www.bcc.cuny.edu/about-bcc/news-publications/more-news/"
        ],
        "baruc": [
            "https://newscenter.baruch.cuny.edu/"
        ],
        "gc": [
            "https://www.gc.cuny.edu/news?category=879"
        ],
        "ct": [
            "https://www.citytech.cuny.edu/news/"
        ],
        "qc": [
            "https://www.qc.cuny.edu/communications/press-release-archive/"
        ],
        "broklyn": [
            "https://www.brooklyn.edu/news-events/"
        ],
        "sph": [
            "https://sph.cuny.edu/life-at-sph/news/"
        ],
        "hostos": [
            "https://www.hostos.cuny.edu/News"
        ],
        "york": [
            "https://www.york.cuny.edu/news/",
            "https://www.york.cuny.edu/news/?page_bf1fcfc0_fe36_412f_93a1_19e596b5d96c=2"
        ],
        "lagrdia": [
            "https://www.laguardia.edu/news/results/?_sft_lg_news_section=news"
        ],
        "sps": [
            "https://sps.cuny.edu/about/news?page=0",
            "https://sps.cuny.edu/about/news?page=1",
            "https://sps.cuny.edu/about/news?page=2",
            "https://sps.cuny.edu/about/news?page=3"
        ],
        "qcc": [
            "https://www.qcc.cuny.edu/news/"
        ],
        "mec": [
            "https://www.mec.cuny.edu/category/campus-news/",
            "https://www.mec.cuny.edu/category/campus-news/page/2/"
        ],
        "macaly": [
            "https://macaulay.cuny.edu/news-events/"
        ],
        "lehman": [
            "https://www.lehman.cuny.edu/news/search/",
            "https://www.lehman.cuny.edu/news/search/?page=2"
        ],
        "law": [
            "https://www.law.cuny.edu/newsroom-articles/",
            "https://www.law.cuny.edu/newsroom-articles/page/2/"
        ],
        "ccny": [
            "https://www.ccny.cuny.edu/news",
            "https://www.ccny.cuny.edu/news?page=1" 
        ],
        "bmcc": [
            "https://www.bmcc.cuny.edu/bmcc-news/"
        ],
        "csi": [
            "https://csitoday.com/"
        ],
        "guttman": [
            "https://guttman.cuny.edu/category/news/"
        ],
        "hunter": [
            "https://hunter.cuny.edu/news/"
        ],
        "jjay": [
            "https://www.jjay.cuny.edu/news-events/news"
        ],
        "kbcc": [
            "https://www.kbcc.cuny.edu/news/index.html?page=",
            "https://www.kbcc.cuny.edu/news/index.html?page=2",
            "https://www.kbcc.cuny.edu/news/index.html?page=3"
        ]

    }
    asyncio.run(run_college_scraper(target_urls,False))






import asyncio
import json
import os
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright



# --- 1. The Corrected CCNY Scraper ---

async def scrape_ccny(soup):
    """
    Targets the 'listing-item' grid structure from CCNY's news page.
    """
    news_data = []
    # Use the exact class from your HTML snippet
    items = soup.find_all("div", class_="listing-item")
    
    for item in items:
        # Title & Link (Inside h3.listing-item__title)
        title_tag = item.find("h3", class_="listing-item__title")
        if not title_tag: continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag: continue
        
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"https://www.ccny.cuny.edu{link}"

        # Image (Inside listing-item__image thumbnail)
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"https://www.ccny.cuny.edu{img_src}"

        # Description (Inside listing-item__teaser)
        desc_tag = item.find("div", class_="listing-item__teaser")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_bmcc(soup):
    """
    Targets the 'pl-blogcnt' structure found on the BMCC news page.
    """
    news_data = []
    # Each news entry is wrapped in this class
    items = soup.find_all("div", class_="pl-blogcnt")
    
    for item in items:
        # --- TITLE & LINK ---
        # Found inside h4.pl-title
        title_tag = item.find("h4", class_="pl-title")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # --- IMAGE ---
        # Found inside div.pl-thumbcnt
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # BMCC uses direct cloud storage links for images
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DESCRIPTION ---
        # Found in p.pl-text
        desc_tag = item.find("p", class_="pl-text")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # --- DATE (Optional Extra) ---
        # BMCC includes a date span inside the H4
        date_tag = title_tag.find("span", class_="pl-date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        if title:
            news_data.append({
                "title": title,
                "date": date_str,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })
    
    return news_data

async def scrape_csi(soup):
    """
    Targets the 'article' structure used by the Extra theme on CSIToday.
    """
    news_data = []
    # CSI uses <article> tags for almost all news items across different modules
    articles = soup.find_all("article")
    
    for article in articles:
        # --- TITLE & LINK ---
        title_tag = article.find(["h2", "h3"], class_="entry-title")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # --- IMAGE ---
        # CSI images are often in an <img> tag or a background-image style attribute
        img_src = ""
        img_tag = article.find("img")
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
        elif 'style' in article.attrs and 'background-image' in article['style']:
            # Fallback for slider items with background images
            style = article['style']
            start = style.find('url("') + 5
            end = style.find('")', start)
            img_src = style[start:end]

        # --- DESCRIPTION ---
        desc_tag = article.find("div", class_="excerpt")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # --- DATE ---
        date_tag = article.find("span", class_="updated")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # Avoid duplicates within the same page (slider + list often repeat)
        if not any(item['read_more_link'] == link for item in news_data):
            news_data.append({
                "title": title,
                "date": date_str,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })
    
    return news_data

async def scrape_guttman(soup):
    """
    Targets the 'entry-archive' structure used by Guttman Community College.
    """
    news_data = []
    # Articles are wrapped in <article> tags with specific classes
    articles = soup.find_all("article", class_="entry-archive")
    
    for article in articles:
        # --- TITLE & LINK ---
        # Guttman provides a direct link class 'entry-title-link'
        title_tag = article.find("a", class_="entry-title-link")
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        link = title_tag['href']

        # --- IMAGE ---
        # Guttman uses <picture> tags; we'll grab the primary <img> src
        img_src = ""
        img_tag = article.find("img", class_="entry-image")
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DATE ---
        # Uses <time> tag with a machine-readable datetime attribute
        time_tag = article.find("time", class_="entry-time")
        date_str = time_tag.get_text(strip=True) if time_tag else ""

        # --- DESCRIPTION (OPTIONAL) ---
        # Note: In the archive view, Guttman often relies on titles alone,
        # but check for entry-content just in case it's toggled on.
        desc_tag = article.find("div", class_="entry-summary")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_hunter(soup):
    """
    Targets the 'news-box' structure used by Hunter College.
    """
    news_data = []
    # Articles are wrapped in divs with the class 'news-box'
    articles = soup.find_all("div", class_="news-box")
    
    for article in articles:
        # --- LINK & HOVER BLOCK ---
        # The primary link wraps almost all content in the box
        link_tag = article.find("a", class_="hover-block")
        if not link_tag:
            continue
            
        link = link_tag.get('href', '')

        # --- TITLE ---
        # Hunter uses a div with class 'hed' for the headline
        title_tag = link_tag.find("div", class_="hed")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # --- IMAGE ---
        # Images are inside a div class 'hover-blockbg'
        img_src = ""
        img_tag = link_tag.find("img", class_="hover-blockimg")
        if img_tag:
            # Look for src, or data-src if it's lazy-loaded
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DATE ---
        # Date is in a div with class 'date'
        date_tag = link_tag.find("div", class_="date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # The description is usually a direct <p> tag inside the link_tag
        desc_tag = link_tag.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data


async def scrape_john_jay(soup):
    """
    Targets the 'teaser-card' structure from John Jay's news page.
    """
    news_data = []
    base_url = "https://www.jjay.cuny.edu"
    
    # Each news item is wrapped in a div with these classes
    articles = soup.find_all("div", class_="teaser-card")
    
    for article in articles:
        # --- TITLE & LINK ---
        title_container = article.find("div", class_="card__title")
        title_tag = title_container.find("a") if title_container else None
        
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        link = title_tag.get('href', '')
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # --- IMAGE ---
        img_tag = article.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"{base_url}{img_src}"

        # --- DATE ---
        date_tag = article.find("div", class_="card__meta")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": "" # John Jay overview lacks a teaser paragraph
        })
    
    return news_data

async def scrape_kbcc(soup):
    """
    Targets the 'row card g-0' structure from KBCC's news page.
    Note: Images are stored in CSS inline styles.
    """
    news_data = []
    base_url = "https://www.kbcc.cuny.edu"
    
    # Each news item is a div with these classes
    items = soup.find_all("div", class_="row card g-0")
    
    for item in items:
        # --- TITLE & LINK ---
        # Found inside an <h2> with class 'h3'
        title_tag = item.find("h2", class_="h3")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # --- IMAGE (CSS Background Style) ---
        img_src = ""
        # KBCC uses a div with class 'card-img-top' and an inline style for the image
        img_div = item.find("div", class_="card-img-top")
        if img_div and img_div.has_attr('style'):
            style_str = img_div['style']
            # Regex to find the path inside url('...')
            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_str)
            if match:
                img_src = match.group(1)
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"

        # --- DATE ---
        # Found in a list item with class 'pub-date'
        date_tag = item.find("li", class_="pub-date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # The provided HTML has an empty <p></p> for descriptions
        desc_tag = item.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_cuny_law(soup):
    """
    Targets the 'post-list-container' structure from CUNY Law's newsroom.
    """
    news_data = []
    # Articles are list items inside the post-list-container
    container = soup.find("ul", class_="post-list-container")
    if not container:
        return news_data
        
    items = container.find_all("li")
    
    for item in items:
        # --- TITLE & LINK ---
        # The title is in an <h2> tag
        title_tag = item.find("h2")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a")
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag.get('href', '')

        # --- IMAGE ---
        # CUNY Law uses a div with 'data-bg-image' containing the URL
        img_div = item.find("div", class_="newsroom-post-img")
        img_src = ""
        if img_div:
            # We prioritize data-bg-image as it usually contains the clean URL
            raw_bg = img_div.get('data-bg-image') or img_div.get('style', '')
            # Extract URL if it's wrapped in url('...')
            if "url(" in raw_bg:
                img_src = raw_bg.split("url('")[1].split("')")[0]
            else:
                img_src = raw_bg

        # --- DESCRIPTION ---
        # Descriptions are in a div with class 'entry-content'
        desc_tag = item.find("div", class_="entry-content")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # --- DATE ---
        # Note: The provided HTML snippet for CUNY Law does not 
        # include visible date strings in the list view.
        date_str = ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_lehman(soup):
    """
    Targets the 'course-listing' structure from Lehman College's news search.
    """
    news_data = []
    base_url = "https://www.lehman.cuny.edu"
    
    # Each news item is a div with class "course-listing"
    items = soup.find_all("div", class_="course-listing")
    
    for item in items:
        # --- TITLE & LINK ---
        # Lehman uses a specific class for the title paragraph
        title_tag = item.find("p", class_="newsModuleListing__block__desc__title")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a")
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag.get('href', '')
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # --- IMAGE ---
        # Image is inside newsModuleListing__block__img
        img_container = item.find("div", class_="newsModuleListing__block__img")
        img_src = ""
        if img_container:
            img_tag = img_container.find("img")
            if img_tag:
                img_src = img_tag.get('src', '')
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"

        # --- DATE ---
        # Date is in a paragraph with a specific descriptor class
        date_tag = item.find("p", class_="newsModuleListing__block__desc__date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # Lehman uses 'newsModuleListing__block__desc__text' for the summary
        desc_tag = item.find("p", class_="newsModuleListing__block__desc__text")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_macaulay(soup):
    """
    Targets the 'sub-feature-double__content' grid from Macaulay's news page.
    """
    news_data = []
    # Macaulay news items are inside these specific content divs
    items = soup.find_all("div", class_="sub-feature-double__content")
    
    for item in items:
        # --- TITLE & LINK ---
        # The title is in an <h3> tag
        title_tag = item.find("h3")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        # Macaulay links are usually absolute, but we check just in case
        if link.startswith('/'):
            link = f"https://macaulay.cuny.edu{link}"

        # --- IMAGE ---
        # Image is inside the sub-feature-double__image-figure
        img_tag = item.find("img", class_="sub-feature-double__content--image")
        img_src = ""
        if img_tag:
            # Prioritize 'src', but handle 'data-src' if lazy-loading is active
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"https://macaulay.cuny.edu{img_src}"

        # --- DATE ---
        # Macaulay uses the <time> tag for publication dates
        date_tag = item.find("time", class_="calendar-event__time--small")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # Found in the <p> tag within the content div
        desc_tag = item.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data


async def scrape_medgar_evers(soup):
    """
    Targets the 'card' structure from Medgar Evers College's news archive.
    """
    news_data = []
    
    # Each news item is contained within a div with class 'card'
    # These are usually wrapped in col-md-4 or similar grid columns
    items = soup.find_all("div", class_="card")
    
    for item in items:
        # --- TITLE & LINK ---
        # The title is in an <h2>, and the link uses the 'stretched-link' class
        title_tag = item.find("h2")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # --- IMAGE ---
        # MEC images are siblings to the card-body inside the card
        img_tag = item.find("img", class_="wp-post-image")
        img_src = ""
        if img_tag:
            # MEC uses standard src, but we check for data-src as a fallback
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # --- DATE ---
        # Date is located in a <small> tag with class 'text-muted'
        date_tag = item.find("small", class_="text-muted")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # --- DESCRIPTION ---
        # MEC puts the summary in a <p> with class 'card-text'
        # Note: Sometimes there are nested <p> tags here
        desc_container = item.find("p", class_="card-text")
        if desc_container:
            # Get text from the container or the first paragraph inside it
            inner_p = desc_container.find("p")
            description = inner_p.get_text(strip=True) if inner_p else desc_container.get_text(strip=True)
        else:
            description = ""

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_qcc(soup):
    """
    Targets the 'newsSection' structure from QCC's news page.
    """
    news_data = []
    base_url = "https://www.qcc.cuny.edu/news/"
    
    # Each news item is wrapped in a section with class 'newsSection'
    items = soup.find_all("section", class_="newsSection")
    
    for item in items:
        # 1. Title & Link (Found inside <p class="article"><a>)
        p_tag = item.find("p", class_="article")
        if not p_tag:
            continue
            
        a_tag = p_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # Absolute Link Formatting
        if not link.startswith(('http://', 'https://')):
            link = f"{base_url}{link}"

        # 2. Date Extraction
        # The date is usually text after a <br> tag inside the p.article
        date_text = ""
        if p_tag:
            # We get the text but exclude the text that was inside the <a> tag
            full_text = p_tag.get_text("|", strip=True)
            parts = full_text.split("|")
            if len(parts) > 1:
                date_text = parts[-1] # Usually the last part after the title

        # 3. Image Extraction
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src', '')
            # Handle relative image paths like "images/..." or "../images/..."
            if img_src and not img_src.startswith(('http://', 'https://')):
                # Simple join for QCC structure
                img_src = f"https://www.qcc.cuny.edu/news/{img_src.replace('../', '')}"

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "date": date_text,
            "description": "" # QCC news listing doesn't provide a teaser/summary text
        })
    
    return news_data

async def scrape_sps(soup):
    """
    Targets the 'listing-item' structure from CUNY SPS news page.
    """
    news_data = []
    base_url = "https://sps.cuny.edu"
    
    # Find all news row containers
    items = soup.find_all("div", class_="listing-item")
    
    for item in items:
        # 1. Title & Link
        title_tag = item.find("h3", class_="listing-item__title")
        if not title_tag: 
            continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag: 
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Date (Unique to the SPS snippet)
        date_tag = item.find("span", class_="date-display-single")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # 3. Image
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # SPS uses standard 'src', but we check data-src just in case of lazy loading
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"{base_url}{img_src}"

        # 4. Description (Deeply nested in SPS)
        # It's inside listing-item__teaser -> field__item
        desc_tag = item.find("div", class_="listing-item__teaser")
        description = ""
        if desc_tag:
            # get_text() will pull from the nested 'body' div automatically
            description = desc_tag.get_text(strip=True)

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_laguardia(soup):
    """
    Targets the Elementor grid structure from LaGuardia's news page.
    """
    news_data = []
    # In your HTML, each news item is contained within an <article> tag 
    # with the class 'elementor-post'
    items = soup.find_all("article", class_="elementor-post")
    
    for item in items:
        # 1. Title & Link (Inside p.elementor-post__title)
        title_container = item.find("p", class_="elementor-post__title")
        if not title_container:
            continue
        
        a_tag = title_container.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # 2. Image (Elementor usually puts the image in a div called 'elementor-post__thumbnail')
        # Even if not present in your snippet, this handles 'has-post-thumbnail' cases.
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Check for standard src or lazy-loaded data-src
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            
        # 3. Date (Inside span.elementor-post-date)
        date_tag = item.find("span", class_="elementor-post-date")
        date_text = date_tag.get_text(strip=True) if date_tag else ""

        # 4. Description (Elementor uses 'elementor-post__excerpt')
        # Note: Your snippet didn't show excerpts, but they often appear in this class.
        desc_tag = item.find("div", class_="elementor-post__excerpt")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date_text  # Added date as it's prominent in LaGuardia's layout
        })
    
    return news_data

async def scrape_cuny_sph(soup):
    """
    Targets the 'list-view-container' structure from CUNY SPH news page.
    """
    news_data = []
    # Each news entry is wrapped in this container
    items = soup.find_all("div", class_="list-view-container")
    
    for item in items:
        # 1. Title & Link (Inside div.news-title)
        title_container = item.find("div", class_="news-title")
        if not title_container:
            continue
            
        a_tag = title_container.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # 2. Image (Inside div.news-img)
        img_container = item.find("div", class_="news-img")
        img_src = ""
        if img_container:
            img_tag = img_container.find("img")
            if img_tag:
                # Use src, or data-src for lazy-loaded images
                img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # 3. Description (Inside div.news-des-indent_inner)
        desc_tag = item.find("div", class_="news-des-indent_inner")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 4. Date (Optional, but available in this specific HTML)
        date_tag = item.find("div", class_="news-date")
        date = date_tag.get_text(strip=True) if date_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date
        })
    
    return news_data


async def scrape_york(soup):
    """
    Targets the 'advanced-item' structure from York College's news page.
    """
    news_data = []
    base_url = "https://www.york.cuny.edu"
    
    # Each news entry is contained within an 'advanced-item' div
    items = soup.find_all("div", class_="advanced-item")
    
    for item in items:
        # 1. Title & Link (Inside h3.threelines)
        title_tag = item.find("h3", class_="threelines")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Image (Inside advancedImage div)
        img_src = ""
        img_container = item.find("div", class_="advancedImage")
        if img_container:
            img_tag = img_container.find("img")
            if img_tag:
                # Prefer src, but check data-src if they use lazy loading
                img_src = img_tag.get('src') or img_tag.get('data-src', '')
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"

        # 3. Date (Inside p.effectiveDate)
        date_tag = item.find("p", class_="effectiveDate")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # 4. Description (The paragraph after the date)
        # It's usually a generic <p> tag without a specific class in this layout
        desc_tag = item.find("div", class_="nine wide column")
        description = ""
        if desc_tag:
            # Find the paragraph that is NOT the effectiveDate
            p_tags = desc_tag.find_all("p")
            for p in p_tags:
                if "effectiveDate" not in p.get("class", []):
                    description = p.get_text(strip=True)
                    break

        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_hostos(soup):
    """
    Targets the 'event-info' structure from Hostos news page.
    """
    news_data = []
    base_url = "https://www.hostos.cuny.edu"
    
    # Each news entry is contained within an <li> inside the event-box
    items = soup.find_all("li")
    
    for item in items:
        # Check if this <li> actually contains news (look for event-info)
        info_div = item.find("div", class_="event-info")
        if not info_div:
            continue
            
        # 1. Title & Link
        a_tag = info_div.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Date (Optional but useful for Hostos)
        time_tag = item.find("time")
        date_str = time_tag.get('datetime') if time_tag else ""

        # 3. Description & Image (Both are inside the 'location' span)
        desc_container = info_div.find("span", class_="location")
        description = ""
        img_src = ""
        
        if desc_container:
            # Find image if it exists
            img_tag = desc_container.find("img")
            if img_tag:
                img_src = img_tag.get('src', '')
                if img_src.startswith('/'):
                    img_src = f"{base_url}{img_src}"
                if len(img_src)>400:
                    img_src =""
            
            # Get text description (excluding the text inside the <h3> if it leaked in)
            # We strip whitespace and common &nbsp; artifacts
            description = desc_container.get_text(" ", strip=True)
            
        news_data.append({
            "title": title,
            "date": date_str,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_brooklyn_college(soup):
    """
    Targets the 'news-item' structure from Brooklyn College's news page.
    """
    news_data = []
    # Each news entry is contained within a div with class 'news-item'
    items = soup.find_all("div", class_="news-item")
    
    for item in items:
        # Title & Link (Inside the h3 tag)
        title_tag = item.find("h3")
        if not title_tag:
            continue
            
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # Image extraction (Inside the picture/img tag)
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Prefer src, fallback to data-src if they use lazy loading later
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # Description (Inside the <p> tag within the text column)
        desc_tag = item.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_bcc(soup):
    """
    Targets the 'mk-blog-thumbnail-item' structure from BCC's news page.
    """
    news_data = []
    # BCC uses article tags for each news item
    items = soup.find_all("article", class_="mk-blog-thumbnail-item")
    
    for item in items:
        # Title & Link (Inside h3.the-title)
        title_tag = item.find("h3", class_="the-title")
        if not title_tag: 
            continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag: 
            continue
        
        title = a_tag.get_text(strip=True)
        link = a_tag['href']

        # Image (Inside div.featured-image)
        # Note: BCC uses a specific 'blog-image' class
        img_tag = item.find("img", class_="blog-image")
        img_src = ""
        if img_tag:
            # Prioritize the main src, fallback to data-mk-image-src-set if needed
            img_src = img_tag.get('src', '')

        # Description (Inside div.the-excerpt)
        desc_tag = item.find("div", class_="the-excerpt")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

async def scrape_baruch(soup):
    """
    Targets the 'post-item' structure from Baruch College's news page.
    """
    news_data = []
    # Baruch uses 'post-item' for both the main featured story and supporting stories
    items = soup.find_all("div", class_="post-item")
    
    for item in items:
        # 1. Title & Link (Inside a.post-title-link)
        title_tag = item.find("a", class_="post-title-link")
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        link = title_tag.get('href', '')

        # 2. Image (Inside image-container -> img)
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Prioritize src, fallback to data-src
            img_src = img_tag.get('src') or img_tag.get('data-src', '')

        # 3. Description 
        # In the provided HTML, description text is inside a <div> within body-content, 
        # but it doesn't have a unique class. It follows the title link.
        description = ""
        body_content = item.find("div", class_="body-content")
        if body_content:
            # Find the div that contains the summary text (usually after the title <a> tag)
            desc_tag = body_content.find("div")
            if desc_tag:
                description = desc_tag.get_text(strip=True)

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data


async def scrape_graduate_center(soup):
    """
    Targets the 'card--news' article structure from CUNY Graduate Center's news page.
    """
    news_data = []
    base_url = "https://www.gc.cuny.edu"
    
    # Each news item is contained within an <article> tag with these classes
    items = soup.find_all("article", class_="card--news")
    
    for item in items:
        # 1. Title & Link (Inside h3.card__title)
        title_tag = item.find("h3", class_="card__title")
        if not title_tag:
            continue
        
        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue
        
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Image (Inside the <picture> tag)
        # We prioritize the 'src' of the <img> tag inside the <picture> element
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            # Check for src, then fallback to data-src
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
            if img_src.startswith('/'):
                img_src = f"{base_url}{img_src}"

        # 3. Description (Inside p.card__summary)
        desc_tag = item.find("p", class_="card__summary")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 4. Date (Inside span.date)
        date_tag = item.find("span", class_="date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date_str
        })
    
    return news_data

async def scrape_citytech(soup):
    """
    Targets the AngularJS-based news structure from City Tech's news page.
    """
    news_data = []
    base_url = "https://www.citytech.cuny.edu"
    
    # Each news item is contained within this class
    # Note: Using lambda to find classes that contain 'c-margin-b-10' as they are repeat items
    items = soup.find_all("div", class_=lambda x: x and "c-margin-b-10" in x)

    for item in items:
        # 1. Title & Link
        # Titles are inside h1 with specific font classes
        title_tag = item.find("h1", class_="c-title")
        if not title_tag:
            continue
            
        title = title_tag.get_text(strip=True)
        
        # Link logic: Usually found in an <a> around the image or title
        # In the provided HTML, the <a> might be higher up or dynamic.
        # If the tag isn't explicitly in the snippet, we look for any link in the container.
        a_tag = item.find("a", href=True)
        link = a_tag['href'] if a_tag else ""
        if link and link.startswith('/'):
            link = f"{base_url}{link}"

        # 2. Image (Extracted from inline style background-image)
        img_src = ""
        img_div = item.find("div", class_="c-bg-img-center")
        if img_div and img_div.get('style'):
            style_str = img_div['style']
            # Regex to extract the URL from: background-image: url("...")
            match = re.search(r'url\("?(.+?)"?\)', style_str)
            if match:
                img_src = match.group(1)
                # If it's a relative path starting with 'dashboard'
                if not img_src.startswith('http'):
                    img_src = f"{base_url}/{img_src.lstrip('/')}"

        # 3. Description
        desc_tag = item.find("div", class_="c-desc")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Avoid appending empty entries if title is missing
        if title:
            news_data.append({
                "title": title,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })

    return news_data

async def scrape_qc(soup):
    """
    Targets the accordion 'et_pb_toggle' structure from Queens College's news page.
    """
    news_data = []
    
    # 1. Find all monthly accordion/toggle sections
    toggles = soup.find_all("div", class_="et_pb_toggle")
    
    for toggle in toggles:
        # Get the month/year from the toggle title if needed
        # month_text = toggle.find("h5", class_="et_pb_toggle_title").get_text(strip=True)
        
        # 2. Find the content area where the links live
        content_area = toggle.find("div", class_="et_pb_toggle_content")
        if not content_area:
            continue
            
        # 3. Find all <a> tags within the toggle
        # Each link usually represents a news item
        links = content_area.find_all("a", href=True)
        
        for a_tag in links:
            title = a_tag.get_text(strip=True)
            link = a_tag['href']
            
            # Basic validation: ignore very short text or empty links
            if not title or len(title) < 5:
                continue

            # Queens College often uses absolute URLs, but we handle relative just in case
            if link.startswith('/'):
                link = f"https://www.qc.cuny.edu{link}"

            # 4. Extract Description
            # In this HTML, the date is often in a <p> or <span> tag immediately 
            # preceding the <a> tag or its parent.
            parent_p = a_tag.find_parent("p")
            description = ""
            if parent_p:
                # Try to find the date/teaser text in the paragraph preceding this one
                prev_p = parent_p.find_previous_sibling("p")
                if prev_p:
                    description = prev_p.get_text(strip=True)

            # 5. Image (Note: The QC archive list usually doesn't have thumbnails)
            img_src = ""
            
            news_data.append({
                "title": title,
                "read_more_link": link,
                "image_reference": img_src,
                "description": description
            })
    
    return news_data

async def scrape_newmark_j_school(soup):
    """
    Targets the 'item-loop--card' structure from the CUNY Journalism news page.
    """
    news_data = []
    # The main container for each news item
    items = soup.find_all("article", class_="item-loop")

    for item in items:
        # Link & Title
        # The <a> tag wraps the entire card
        a_tag = item.find("a", class_="item-loop--card__link")
        if not a_tag:
            continue
            
        link = a_tag.get('href', '')
        
        # Title (Inside h2.card__title)
        title_tag = item.find("h2", class_="card__title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # Image (Handled via inline style background-image)
        img_src = ""
        img_div = item.find("div", class_="card__img")
        if img_div and img_div.get('style'):
            style_str = img_div['style']
            # Regex to extract the URL inside url('...')
            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_str)
            if match:
                img_src = match.group(1)

        # Description (Inside p.card__desc)
        desc_tag = item.find("p", class_="card__desc")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Meta/Date (Optional, but useful for this site)
        meta_tag = item.find("span", class_="card__meta")
        date = meta_tag.get_text(strip=True) if meta_tag else ""

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description,
            "date": date
        })

    return news_data

async def scrape_slu(soup):
    """
    Targets the 'vc_grid-item' structure from SLU CUNY's news page.
    """
    news_data = []
    # Each news card is contained within this class
    items = soup.find_all("div", class_="vc_grid-item")
    
    for item in items:
        # 1. Extract Title and Link
        # Found inside the 'vc_gitem-post-data-source-post_title' container
        title_container = item.find("div", class_="vc_gitem-post-data-source-post_title")
        if not title_container:
            continue
            
        a_tag = title_container.find("a", href=True)
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        # Ensure absolute URL
        if link.startswith('/'):
            link = f"https://slu.cuny.edu{link}"

        # 2. Extract Image Reference
        # Images are often inside a figure or the wpb_single_image container
        img_tag = item.find("img")
        img_src = ""
        if img_tag:
            img_src = img_tag.get('src') or img_tag.get('data-src', '')
        
        # If no <img> exists, SLU sometimes uses background-images on the link
        if not img_src:
            img_container = item.find("a", class_="vc_gitem-link")
            if img_container and 'style' in img_container.attrs:
                # Basic parse for background-image: url(...)
                style = img_container['style']
                if 'url(' in style:
                    img_src = style.split('url(')[1].split(')')[0].replace('"', '').replace("'", "")

        if img_src and img_src.startswith('/'):
            img_src = f"https://slu.cuny.edu{img_src}"

        # 3. Extract Description
        # Found inside the 'vc_gitem-post-data-source-post_excerpt' container
        desc_container = item.find("div", class_="vc_gitem-post-data-source-post_excerpt")
        description = ""
        if desc_container:
            # Get text and clean up whitespace/newlines
            description = desc_container.get_text(strip=True)

        news_data.append({
            "title": title,
            "read_more_link": link,
            "image_reference": img_src,
            "description": description
        })
    
    return news_data

# -------------------------------------------------------------
#
#
# -------------------------------------------------------------
# [Include scrape_ccny and scrape_bmcc functions here]

async def run_college_scraper(college_urls, use_keywords=True):
    html_folder = "colleges_htmls"
    os.makedirs(html_folder, exist_ok=True)
    
    json_file = 'colleges_data.json'

    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                final_output = json.load(f)
            except json.JSONDecodeError:
                final_output = {}
    else:
        final_output = {}

    scraper_dispatch = {
        "ccny": scrape_ccny, "bmcc": scrape_bmcc, "csi": scrape_csi,
        "guttman": scrape_guttman, "hunter": scrape_hunter, "jjay": scrape_john_jay,
        "kbcc": scrape_kbcc, "law": scrape_cuny_law, "lehman": scrape_lehman,
        "macaly": scrape_macaulay, "mec": scrape_medgar_evers, "qcc": scrape_qcc,
        "sps": scrape_sps, "lagrdia": scrape_laguardia, "sph": scrape_cuny_sph,
        "york": scrape_york, "hostos": scrape_hostos, "broklyn": scrape_brooklyn_college,
        "bcc": scrape_bcc, "baruc": scrape_baruch, "gc": scrape_graduate_center,
        "ct": scrape_citytech, "qc": scrape_qc, "soj": scrape_newmark_j_school,
        "slu": scrape_slu
    }
    
    KEYWORDS = ["student", "research", "opportunity", "program", "event", "hackathon", "stem", "arts", "internship", "workshop"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        await context.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,pdf}", lambda route: route.abort())
        
        page = await context.new_page()
        numOfNews = 20

        for college_id, urls in college_urls.items():
            session_college_data = []
            seen_descriptions = set()
            
            for index, url in enumerate(urls):
                if len(session_college_data) >= 50:
                    break

                for attempt in range(3):
                    try:
                        print(f"Scraping {college_id} | Page {index + 1} (Attempt {attempt + 1})...")
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000) 
                        
                        html_content = await page.content()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        if college_id in scraper_dispatch:
                            new_items = await scraper_dispatch[college_id](soup)
                            for item in new_items:
                                if len(session_college_data) >= numOfNews:
                                    break
                                
                                desc = item.get('description', '').lower().strip()
                                title = item.get('title', '').lower().strip()
                                combined_text = f"{title} {desc}"
                                
                                if not desc or desc in seen_descriptions:
                                    continue
                                    
                                if not use_keywords or any(kw in combined_text for kw in KEYWORDS):
                                    session_college_data.append(item)
                                    seen_descriptions.add(desc)
                        break 
                    except Exception as e:
                        if attempt < 2: continue
                        print(f"   -> Final Error on {url}: {e}")
                        break 

            # --- UPDATED MERGING LOGIC ---
            existing_data = final_output.get(college_id, [])
            
            if len(session_college_data) > len(existing_data):
                # Scenario 1: New scrape is strictly better/longer
                final_output[college_id] = session_college_data
                print(f"   -> REPLACED {college_id}: Found more news ({len(session_college_data)} items).")
            
            elif session_college_data:
                # Scenario 2: New news is less, but we want to prepend the new ones to the old ones
                # We use a set of existing titles or descriptions to ensure we don't add duplicates
                existing_titles = {i.get('title', '').lower().strip() for i in existing_data}
                
                # Filter session data to only include items not already in the JSON
                fresh_items = [item for item in session_college_data 
                               if item.get('title', '').lower().strip() not in existing_titles]
                
                if fresh_items:
                    # Prepend fresh items to the beginning of the old data
                    updated_list = fresh_items + existing_data
                    # Truncate to the top 10 (or whatever your "top number" limit is)
                    final_output[college_id] = updated_list[:numOfNews]
                    print(f"   -> MERGED {college_id}: Added {len(fresh_items)} new items to top of list.")
                else:
                    print(f"   -> NO CHANGE {college_id}: No strictly new news found.")
            else:
                print(f"   -> SKIPPED {college_id}: No data found in this session.")

        await browser.close()

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4)

    print(f"\nScraping Complete. Results saved to {json_file}")

if __name__ == "__main__":
    # Example showing multiple pages for BMCC
    target_urls = {
        "slu":[
            "https://slu.cuny.edu/news/"
        ],
        "soj":[
            "https://www.journalism.cuny.edu/category/news/"
        ],
        "bcc": [
            "https://www.bcc.cuny.edu/about-bcc/news-publications/more-news/"
        ],
        "baruc": [
            "https://newscenter.baruch.cuny.edu/"
        ],
        "gc": [
            "https://www.gc.cuny.edu/news?category=879"
        ],
        "ct": [
            "https://www.citytech.cuny.edu/news/"
        ],
        "qc": [
            "https://www.qc.cuny.edu/communications/press-release-archive/"
        ],
        "broklyn": [
            "https://www.brooklyn.edu/news-events/"
        ],
        "sph": [
            "https://sph.cuny.edu/life-at-sph/news/"
        ],
        "hostos": [
            "https://www.hostos.cuny.edu/News"
        ],
        "york": [
            "https://www.york.cuny.edu/news/",
            "https://www.york.cuny.edu/news/?page_bf1fcfc0_fe36_412f_93a1_19e596b5d96c=2"
        ],
        "lagrdia": [
            "https://www.laguardia.edu/news/results/?_sft_lg_news_section=news"
        ],
        "sps": [
            "https://sps.cuny.edu/about/news?page=0",
            "https://sps.cuny.edu/about/news?page=1",
            "https://sps.cuny.edu/about/news?page=2",
            "https://sps.cuny.edu/about/news?page=3"
        ],
        "qcc": [
            "https://www.qcc.cuny.edu/news/"
        ],
        "mec": [
            "https://www.mec.cuny.edu/category/campus-news/",
            "https://www.mec.cuny.edu/category/campus-news/page/2/"
        ],
        "macaly": [
            "https://macaulay.cuny.edu/news-events/"
        ],
        "lehman": [
            "https://www.lehman.cuny.edu/news/search/",
            "https://www.lehman.cuny.edu/news/search/?page=2"
        ],
        "law": [
            "https://www.law.cuny.edu/newsroom-articles/",
            "https://www.law.cuny.edu/newsroom-articles/page/2/"
        ],
        "ccny": [
            "https://www.ccny.cuny.edu/news",
            "https://www.ccny.cuny.edu/news?page=1" 
        ],
        "bmcc": [
            "https://www.bmcc.cuny.edu/bmcc-news/"
        ],
        "csi": [
            "https://csitoday.com/"
        ],
        "guttman": [
            "https://guttman.cuny.edu/category/news/"
        ],
        "hunter": [
            "https://hunter.cuny.edu/news/"
        ],
        "jjay": [
            "https://www.jjay.cuny.edu/news-events/news"
        ],
        "kbcc": [
            "https://www.kbcc.cuny.edu/news/index.html?page=",
            "https://www.kbcc.cuny.edu/news/index.html?page=2",
            "https://www.kbcc.cuny.edu/news/index.html?page=3"
        ]

    }
    asyncio.run(run_college_scraper(target_urls,False))
