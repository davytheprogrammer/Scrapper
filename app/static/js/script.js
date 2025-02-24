document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scrape-form');
    const urlInput = document.getElementById('url-input');
    const scrapeImagesCheckbox = document.getElementById('scrape-images');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress');
    const progressText = document.getElementById('progress-text');
    const resultContainer = document.getElementById('result');
    const resultMessage = document.getElementById('result-message');
    const downloadLink = document.getElementById('download-link');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const url = urlInput.value.trim();
        const scrapeImages = scrapeImagesCheckbox.checked;
        
        if (!url) {
            alert('Please enter a valid URL.');
            return;
        }

        progressContainer.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        progressBar.style.width = '0%';
        progressText.textContent = 'Starting scrape...';

        const eventSource = new EventSource(`/scrape?url=${encodeURIComponent(url)}&scrape_images=${scrapeImages}`);
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.status === 'progress') {
                progressBar.style.width = `${data.progress}%`;
                progressText.textContent = data.message;
            } else if (data.status === 'success') {
                progressBar.style.width = '100%';
                progressText.textContent = data.message;
                resultMessage.textContent = data.message;
                downloadLink.href = `/static/scraped_data/${data.merged_pdf_path.split('/').pop()}`;
                downloadLink.classList.remove('hidden');
                resultContainer.classList.remove('hidden');
                eventSource.close();
            } else if (data.status === 'error') {
                progressBar.style.width = '100%';
                progressText.textContent = data.message;
                resultMessage.textContent = data.message;
                resultContainer.classList.remove('hidden');
                eventSource.close();
            }
        };

        eventSource.onerror = (err) => {
            progressBar.style.width = '100%';
            progressText.textContent = 'Error occurred during scraping.';
            resultMessage.textContent = 'An error occurred during scraping. Please try again.';
            resultContainer.classList.remove('hidden');
            eventSource.close();
        };
    });
});
