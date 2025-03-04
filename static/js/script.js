document.addEventListener('DOMContentLoaded', () => {
    const youtubeUrlInput = document.getElementById('youtube-url');
    const notesStyleSelect = document.getElementById('notes-style');
    const generateBtn = document.getElementById('generate-btn');
    const loader = document.getElementById('loader');
    const notesOutput = document.getElementById('notes-output');
    const copyBtn = document.getElementById('copy-btn');
    const downloadBtn = document.getElementById('download-btn');

    let isGenerating = false;
    let currentNotes = '';

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
        copyBtn.style.display = 'none';
        downloadBtn.style.display = 'none';

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
                    // Store the original notes
                    currentNotes = data.notes;
                    
                    // Format notes for display (remove markdown ** and add HTML formatting)
                    const formattedNotes = data.notes
                        .replace(/\*\*(.*?)\*\*/g, '$1')  // Remove bold markdown
                        .replace(/\*(.*?)\*/g, '$1')      // Remove italic markdown
                        .replace(/\n/g, '<br>')           // Convert newlines to <br>
                        .replace(/^- (.*)/gm, '• $1');    // Convert markdown lists to bullet points

                    notesOutput.innerHTML = formattedNotes;
                    copyBtn.style.display = 'block';
                    downloadBtn.style.display = 'block';
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
        downloadBtn.style.display = 'none';
        currentNotes = '';
    }

    copyBtn.addEventListener('click', () => {
        if (currentNotes) {
            navigator.clipboard.writeText(currentNotes)
                .then(() => {
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = 'Copied!';
                    copyBtn.classList.add('success');
                    setTimeout(() => {
                        copyBtn.textContent = originalText;
                        copyBtn.classList.remove('success');
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy text:', err);
                    showError('Failed to copy text to clipboard');
                });
        }
    });

    downloadBtn.addEventListener('click', () => {
        if (currentNotes) {
            // Create a blob with the notes
            const blob = new Blob([currentNotes], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            
            // Create a temporary link and click it
            const a = document.createElement('a');
            const videoId = youtubeUrlInput.value.match(/(?:v=|\/)([\w-]{11})(?:\?|$|&)/)?.[1] || 'notes';
            a.href = url;
            a.download = `youtube_notes_${videoId}.txt`;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show feedback
            downloadBtn.classList.add('success');
            setTimeout(() => {
                downloadBtn.classList.remove('success');
            }, 2000);
        }
    });

    // Add input validation
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