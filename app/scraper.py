import requests
from bs4 import BeautifulSoup
from weasyprint import HTML
import os
import logging
import validators
from PyPDF2 import PdfMerger
from readability import Document
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import json
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Load configuration settings
with open('config/config.json') as config_file:
    config = json.load(config_file)

def clean_html(html_content, scrape_images=False, base_url=''):
    try:
        doc = Document(html_content)
        readable_html = doc.summary()
        soup = BeautifulSoup(readable_html, 'html.parser')
        
        for element in config['elements_to_remove']:
            for tag in soup.find_all(element):
                tag.decompose()

        if not scrape_images:
            for img in soup.find_all('img'):
                img.decompose()
        else:
            # If scraping images, update image src to absolute URLs
            for img in soup.find_all('img'):
                if img.get('src'):
                    img['src'] = urljoin(base_url, img['src'])
        
        custom_css = config['css_styles']
        formatted_html = custom_css + str(soup)
        
        return formatted_html
    except Exception as e:
        logging.error(f"Error cleaning HTML content: {e}")
        return html_content

def is_valid_url(url):
    return validators.url(url)

def fetch_and_convert_to_pdf(url, output_dir, scrape_images):
    try:
        if not is_valid_url(url):
            logging.warning(f"Invalid URL: {url}")
            return None
        
        response = requests.get(url)
        if response.status_code == 200:
            cleaned_html = clean_html(response.content, scrape_images, url)
            pdf_path = os.path.join(output_dir, f"{url.split('//')[1].replace('/', '_')}.pdf")
            
            # Use WeasyPrint instead of pdfkit
            HTML(string=cleaned_html).write_pdf(pdf_path)
            logging.info(f"Successfully converted {url} to PDF")

            if os.path.getsize(pdf_path) <= 2150:
                logging.info(f"Deleting {pdf_path} as it is 2.1 KB or less")
                os.remove(pdf_path)
                return None

            return pdf_path
        else:
            logging.warning(f"Failed to fetch {url}, status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching or converting {url} to PDF: {e}")
        return None

def get_all_links(base_url):
    links = set()
    to_visit = [base_url]
    visited = set()

    while to_visit:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            if not is_valid_url(current_url):
                logging.warning(f"Invalid URL: {current_url}")
                continue

            response = requests.get(current_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            page_links = [a['href'] for a in soup.find_all('a', href=True)]

            for link in page_links:
                full_url = requests.compat.urljoin(base_url, link)
                links.add(full_url)
                if soup.select_one(config['pagination_selector']):
                    next_page = soup.select_one(config['pagination_selector'])['href']
                    full_next_page_url = requests.compat.urljoin(base_url, next_page)
                    to_visit.append(full_next_page_url)
        except Exception as e:
            logging.error(f"Error getting links from {current_url}: {e}")

    return list(links)

def scrape_website(base_url, output_dir, scrape_images):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    links = get_all_links(base_url)
    total_links = len(links)

    yield {'status': 'info', 'message': f'Found {total_links} links to scrape', 'progress': 0}

    pdf_files = []
    with ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(fetch_and_convert_to_pdf, link, output_dir, scrape_images): link for link in links}
        completed = 0
        for future in concurrent.futures.as_completed(future_to_url):
            pdf_file = future.result()
            completed += 1
            progress = (completed / total_links) * 100
            if pdf_file:
                pdf_files.append(pdf_file)
            yield {'status': 'progress', 'message': f'Processed {completed}/{total_links} links', 'progress': progress}

    if pdf_files:
        try:
            yield {'status': 'info', 'message': 'Merging PDFs...', 'progress': 95}
            merger = PdfMerger()
            for pdf in pdf_files:
                merger.append(pdf)
            merged_pdf_path = os.path.join(output_dir, "merged.pdf")
            merger.write(merged_pdf_path)
            merger.close()
            logging.info("PDFs created and merged successfully.")

            # Delete individual PDF files
            for pdf in pdf_files:
                os.remove(pdf)
            logging.info("Individual PDF files deleted.")

            yield {
                'status': 'success',
                'message': 'Website scraped and PDFs merged successfully.',
                'merged_pdf_path': merged_pdf_path,
                'progress': 100
            }
        except Exception as e:
            logging.error(f"Error merging PDFs: {e}")
            yield {'status': 'error', 'message': str(e), 'progress': 100}
    else:
        yield {'status': 'error', 'message': 'No valid PDFs were generated.', 'progress': 100}
