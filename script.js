// Global variables
let player;
let isPlayerReady = false;
let progressInterval;
let currentVideoId = null;
let songQueue = [];
let currentSongIndex = 0;

// YouTube API initialization
function onYouTubeIframeAPIReady() {
    player = new YT.Player('youtube-player', {
        height: '1',
        width: '1',
        videoId: '',
        playerVars: {
            'playsinline': 1,
            'controls': 0,
            'enablejsapi': 1,
            'origin': window.location.origin,
            'rel': 0,
            'modestbranding': 1,
            'autoplay': 1  // Enable autoplay
        },
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange,
            'onError': onPlayerError
        }
    });
}

function onPlayerReady(event) {
    isPlayerReady = true;
    initializePlayerControls();
    player.setVolume(100);
    // Try playing the first song if queue is loaded
    if (songQueue.length > 0) {
        playSong(songQueue[0]);
    }
}

function onPlayerStateChange(event) {
    switch(event.data) {
        case YT.PlayerState.PLAYING:
            $('#play-pause-button').html('<i class="fas fa-pause"></i>');
            startProgressUpdate();
            break;
        case YT.PlayerState.PAUSED:
            $('#play-pause-button').html('<i class="fas fa-play"></i>');
            stopProgressUpdate();
            break;
        case YT.PlayerState.ENDED:
            $('#play-pause-button').html('<i class="fas fa-play"></i>');
            stopProgressUpdate();
            $('#progress-bar').css('width', '100%');
            playNextSong();
            break;
        case YT.PlayerState.UNSTARTED:
            // Force play if unstarted
            setTimeout(() => player.playVideo(), 500);
            break;
    }
}

function onPlayerError(event) {
    console.error('YouTube Player Error:', event.data);
    let errorMessage = 'Error playing song.';
    switch (event.data) {
        case 2: errorMessage += ' (Invalid video ID)'; break;
        case 5: errorMessage += ' (Video not playable)'; break;
        case 100: errorMessage += ' (Video not found)'; break;
        case 101:
        case 150: errorMessage += ' (Embed not allowed)'; break;
    }
    showError(errorMessage);
    // Automatically try next song
    setTimeout(playNextSong, 1000);
}

// Player Controls
function initializePlayerControls() {
    $('#play-pause-button').off('click').on('click', function() {
        if (!player || !isPlayerReady) return;
        try {
            const state = player.getPlayerState();
            if (state === YT.PlayerState.PLAYING) {
                player.pauseVideo();
            } else {
                player.playVideo();
            }
        } catch (error) {
            console.error('Playback error:', error);
            showError('Error controlling playback');
        }
    });

    $('#volume-slider').off('input').on('input', function() {
        if (!player || !isPlayerReady) return;
        const volume = $(this).val();
        player.setVolume(volume);
        updateVolumeIcon(volume);
    });

    $('#progress-container').off('click').on('click', function(e) {
        if (!player || !isPlayerReady) return;
        try {
            const duration = player.getDuration();
            if (duration) {
                const percent = (e.pageX - $(this).offset().left) / $(this).width();
                player.seekTo(duration * percent);
            }
        } catch (error) {
            console.error('Seeking error:', error);
        }
    });

    $('#prev-button').off('click').on('click', playPreviousSong);
    $('#next-button').off('click').on('click', playNextSong);
}

function playNextSong() {
    if (songQueue.length > 0 && currentSongIndex < songQueue.length - 1) {
        currentSongIndex++;
        playSong(songQueue[currentSongIndex]);
    }
}

function playPreviousSong() {
    if (songQueue.length > 0 && currentSongIndex > 0) {
        currentSongIndex--;
        playSong(songQueue[currentSongIndex]);
    }
}

function playSong(song) {
    if (!player || !isPlayerReady || !song.youtube_id) {
        console.error('Player not ready or invalid song');
        return;
    }
    
    currentVideoId = song.youtube_id;
    $('#song-name').text(song.name);
    $('#artist-name').text(song.artist);
    
    player.loadVideoById({
        videoId: song.youtube_id,
        startSeconds: 0,
        suggestedQuality: 'default'
    });
    
    // Multiple attempts to ensure playback
    let playAttempts = 0;
    const maxAttempts = 3;
    const tryPlay = () => {
        if (playAttempts >= maxAttempts) {
            showError('Failed to play song');
            playNextSong();
            return;
        }
        
        try {
            player.playVideo();
            const checkPlaying = setInterval(() => {
                if (player.getPlayerState() === YT.PlayerState.PLAYING) {
                    $('#play-pause-button').html('<i class="fas fa-pause"></i>');
                    startProgressUpdate();
                    clearInterval(checkPlaying);
                } else if (player.getPlayerState() === YT.PlayerState.ENDED) {
                    clearInterval(checkPlaying);
                    playNextSong();
                }
            }, 500);
        } catch (error) {
            console.error('Play error:', error);
            playAttempts++;
            setTimeout(tryPlay, 1000);
        }
    };
    
    tryPlay();
}

// Progress and Time Update
function startProgressUpdate() {
    stopProgressUpdate();
    progressInterval = setInterval(updateProgress, 100);
}

function stopProgressUpdate() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgress() {
    if (!player || !isPlayerReady) return;
    try {
        const currentTime = player.getCurrentTime() || 0;
        const duration = player.getDuration() || 0;
        if (duration > 0) {
            const percent = (currentTime / duration) * 100;
            $('#progress-bar').css('width', `${percent}%`);
            $('#current-time').text(formatTime(currentTime));
            $('#duration').text(formatTime(duration));
        }
    } catch (error) {
        console.error('Progress update error:', error);
        stopProgressUpdate();
    }
}

// Utility Functions
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const minutes = Math.floor(seconds / 60);
    seconds = Math.floor(seconds % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function updateVolumeIcon(volume) {
    const volumeIcon = $('.volume-icon').first();
    if (volume == '0') {
        volumeIcon.removeClass().addClass('fas fa-volume-mute volume-icon');
    } else if (volume < 50) {
        volumeIcon.removeClass().addClass('fas fa-volume-down volume-icon');
    } else {
        volumeIcon.removeClass().addClass('fas fa-volume-up volume-icon');
    }
}

// Webcam Functions
async function initWebcam() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('webcam');
        video.srcObject = stream;
    } catch (error) {
        console.error('Webcam error:', error);
        showError('Unable to access webcam');
    }
}

function getImageData(video) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg');
}

// UI State Functions
function showLoading() {
    $('.loading').show();
    $('#result').hide();
    $('#error-message').hide();
}

function hideLoading() {
    $('.loading').hide();
}

function showError(message) {
    $('#error-message').html(`<i class="fas fa-exclamation-circle"></i> ${message}`).show();
    hideLoading();
    setTimeout(() => $('#error-message').hide(), 5000); // Auto-hide after 5 seconds
}

function displayResults(data) {
    hideLoading();
    const resultDiv = $('#result');
    
    if (!data || !data.emotion || !data.songs) {
        showError('Invalid response from server');
        return;
    }

    $('#detected-emotion').text(data.emotion);
    songQueue = data.songs;
    currentSongIndex = 0;

    if (songQueue.length > 0) {
        playSong(songQueue[0]);

        const songList = $('#song-list');
        songList.empty();
        songQueue.slice(1).forEach((song, index) => {
            const listItem = $('<li></li>').text(`${song.name} by ${song.artist}`);
            listItem.click(() => {
                currentSongIndex = index + 1;
                playSong(song);
            });
            songList.append(listItem);
        });

        resultDiv.show();
    } else {
        showError('No songs found');
    }
}

// Initialize
$(document).ready(function() {
    initWebcam();

    $('#capture').click(async () => {
        const video = document.getElementById('webcam');
        const imageData = getImageData(video);
        showLoading();

        try {
            const response = await fetch('/predict_emotion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ image: imageData })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Server error');
            }
            displayResults(data);
        } catch (error) {
            console.error('Capture error:', error);
            showError(error.message || 'Failed to process image');
        }
    });

    $('#analyze-text').click(async () => {
        const text = $('#emotion-text').val().trim();
        if (!text) {
            showError('Please enter some text');
            return;
        }

        showLoading();
        try {
            const response = await fetch('/predict_emotion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ text: text })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Server error');
            }
            displayResults(data);
        } catch (error) {
            console.error('Text analysis error:', error);
            showError(error.message || 'Failed to analyze text');
        }
    });
});