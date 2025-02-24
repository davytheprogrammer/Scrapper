from flask import Blueprint, render_template, request, jsonify, Response
from app.scraper import scrape_website
import os
import json

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/scrape', methods=['GET', 'POST'])
def scrape():
    url = request.args.get('url') if request.method == 'GET' else request.form.get('url')
    scrape_images = request.args.get('scrape_images', 'false').lower() == 'true'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    output_dir = os.path.join(os.getcwd(), 'scraped_data')
    
    def generate():
        try:
            for progress in scrape_website(url, output_dir, scrape_images):
                yield f"data: {json.dumps(progress)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')
