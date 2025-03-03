document.addEventListener('DOMContentLoaded', () => {
    const youtubeUrlInput = document.getElementById('youtube-url');
    const notesStyleSelect = document.getElementById('notes-style');
    const generateBtn = document.getElementById('generate-btn');
    const loader = document.getElementById('loader');
    const notesOutput = document.getElementById('notes-output');
    const copyBtn = document.getElementById('copy-btn');

    let isGenerating = false;

    generateBtn.addEventListener('click', async () => {
        if (isGenerating) return;

        const youtubeUrl = youtubeUrlInput.value.trim();
        const style = notesStyleSelect.value;

        if (!youtubeUrl) {
            showError('Please enter a YouTube URL');
            return;
        }

        // Show loader and hide previous notes
        isGenerating = true;
        loader.style.display = 'block';
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
        notesOutput.innerHTML = '';

        try {
            const response = await fetch('/generate_notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    style: style
                })
            });

            const data = await response.json();

            if (response.ok) {
                if (data.notes.startsWith('Error:')) {
                    showError(data.notes);
                } else {
                    // Convert markdown to HTML (basic conversion)
                    const formattedNotes = data.notes
                        .replace(/\n/g, '<br>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\*(.*?)\*/g, '<em>$1</em>')
                        .replace(/^- (.*)/gm, '• $1');

                    notesOutput.innerHTML = formattedNotes;
                    copyBtn.style.display = 'block';
                }
            } else {
                throw new Error(data.error || 'Failed to generate notes');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            loader.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Notes';
            isGenerating = false;
        }
    });

    function showError(message) {
        notesOutput.innerHTML = `<div class="error-message">${message}</div>`;
        copyBtn.style.display = 'none';
    }

    copyBtn.addEventListener('click', () => {
        const notesText = notesOutput.innerText;
        
        if (notesText && !notesText.includes('Your generated notes will appear here...')) {
            navigator.clipboard.writeText(notesText)
                .then(() => {
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => {
                        copyBtn.textContent = originalText;
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy text:', err);
                    showError('Failed to copy text to clipboard');
                });
        }
    });

    // Add input validation and URL formatting
    youtubeUrlInput.addEventListener('input', (e) => {
        const url = e.target.value.trim();
        if (url.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/)) {
            youtubeUrlInput.classList.add('valid');
            youtubeUrlInput.classList.remove('invalid');
        } else if (url) {
            youtubeUrlInput.classList.add('invalid');
            youtubeUrlInput.classList.remove('valid');
        } else {
            youtubeUrlInput.classList.remove('valid', 'invalid');
        }
    });
}); 