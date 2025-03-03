document.addEventListener('DOMContentLoaded', () => {
    const youtubeUrlInput = document.getElementById('youtube-url');
    const notesStyleSelect = document.getElementById('notes-style');
    const generateBtn = document.getElementById('generate-btn');
    const loader = document.getElementById('loader');
    const notesOutput = document.getElementById('notes-output');
    const copyBtn = document.getElementById('copy-btn');

    generateBtn.addEventListener('click', async () => {
        const youtubeUrl = youtubeUrlInput.value.trim();
        const style = notesStyleSelect.value;

        if (!youtubeUrl) {
            alert('Please enter a YouTube URL');
            return;
        }

        // Show loader and hide previous notes
        loader.style.display = 'block';
        notesOutput.innerHTML = '';
        generateBtn.disabled = true;

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
                // Convert markdown to HTML (basic conversion)
                const formattedNotes = data.notes
                    .replace(/\n/g, '<br>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/^- (.*)/gm, '• $1');

                notesOutput.innerHTML = formattedNotes;
            } else {
                throw new Error(data.error || 'Failed to generate notes');
            }
        } catch (error) {
            notesOutput.innerHTML = `<div class="error-message">${error.message}</div>`;
        } finally {
            loader.style.display = 'none';
            generateBtn.disabled = false;
        }
    });

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
                    alert('Failed to copy text to clipboard');
                });
        }
    });

    // Add input validation and URL formatting
    youtubeUrlInput.addEventListener('paste', (e) => {
        // Allow paste event to complete
        setTimeout(() => {
            const url = youtubeUrlInput.value;
            // Basic YouTube URL validation
            if (url.includes('youtube.com/watch?v=') || url.includes('youtu.be/')) {
                youtubeUrlInput.classList.add('valid');
                youtubeUrlInput.classList.remove('invalid');
            } else {
                youtubeUrlInput.classList.add('invalid');
                youtubeUrlInput.classList.remove('valid');
            }
        }, 0);
    });
}); 