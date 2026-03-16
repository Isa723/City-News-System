// Initialize Leaflet Map anchored roughly around Kocaeli, Turkey
// Using Light Mode tiles from CartoDB for a standard Google Maps look
const map = L.map('map').setView([40.7654, 29.9408], 11);

L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// Icon mapping for FontAwesome symbols
const categoryIcons = {
    "Trafik Kazası": "fa-car-burst",
    "Yangın": "fa-fire",
    "Elektrik Kesintisi": "fa-bolt",
    "Hırsızlık": "fa-user-secret",
    "Kültürel Etkinlikler": "fa-masks-theater",
    "Diğer": "fa-circle-info"
};

// Global scope to store markers and data
let allNewsData = [];
let mapMarkers = [];

// Helper function to create custom colored SVG markers with symbols
function createCustomIcon(color, iconClass) {
    const svgMarker = `
        <div class="custom-marker-wrapper">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="36" height="36">
                <path fill="${color}" stroke="#ffffff" stroke-width="2" d="M16 0C10.5 0 6 4.5 6 10c0 7.5 10 22 10 22s10-14.5 10-22c0-5.5-4.5-10-10-10z"/>
            </svg>
            <i class="fa-solid ${iconClass} marker-symbol"></i>
        </div>`;
    
    return L.divIcon({
        className: 'custom-div-icon',
        html: svgMarker,
        iconSize: [36, 36],
        iconAnchor: [18, 36],
        popupAnchor: [0, -36]
    });
}

// Fetch the data from FastAPI Backend
async function loadNews() {
    try {
        const response = await fetch('/api/news');
        allNewsData = await response.json();
        
        applyFilters(); // Render initial state
    } catch (error) {
        console.error("Error fetching news:", error);
    }
}

// Render markers on the map
function renderMarkers(filteredData) {
    // Clear old markers first
    mapMarkers.forEach(marker => map.removeLayer(marker));
    mapMarkers = [];
    
    // Update Stats
    document.getElementById('totalNewsStat').innerText = filteredData.length;
    
    filteredData.forEach(news => {
        // Skip news with no coordinates (as mandated: "Konum bulunamazsa gösterilmemelidir")
        if (!news.latitude || !news.longitude) return;
        
        const catColor = categoryColors[news.category] || categoryColors["Diğer"];
        const iconClass = categoryIcons[news.category] || categoryIcons["Diğer"];
        const customIcon = createCustomIcon(catColor, iconClass);
        
        // Parse the date
        const dateObj = new Date(news.publish_date);
        const dateString = dateObj.toLocaleDateString('tr-TR', { 
            day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute:'2-digit' 
        });
        
        const catClass = categoryClasses[news.category] || "cat-other";
        
        // Render sources list as "Habere Git" buttons (Mandatory Section 8)
        let sourcesHtml = '';
        if (news.sources && Array.isArray(news.sources)) {
            sourcesHtml = news.sources.map(s => 
                `<div class="source-item">
                    <span class="source-name">${s.name}</span>
                    <a href="${s.url}" target="_blank" class="go-to-btn">Habere Git <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>`
            ).join('');
        } else {
            // Fallback for old schema
            sourcesHtml = `
                <div class="source-item">
                    <span class="source-name">${news.source}</span>
                    <a href="${news.url}" target="_blank" class="go-to-btn">Habere Git <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>`;
        }
        
        // Popup Content Template
        const popupContent = `
            <div class="popup-header">
                <span class="popup-category ${catClass}"><i class="fa-solid ${iconClass}"></i> ${news.category}</span>
                <div class="popup-title">${news.title}</div>
            </div>
            <div class="popup-meta">
                <div><i class="fa-solid fa-clock"></i> ${dateString}</div>
                <div><i class="fa-solid fa-location-crosshairs"></i> ${news.location_text}</div>
            </div>
            <div class="sources-list">
                <div class="sources-label">Kaynaklar:</div>
                ${sourcesHtml}
            </div>
            <div class="popup-footer">
                <p class="popup-snippet">${news.content.substring(0, 100)}...</p>
            </div>
        `;
        
        // Create marker
        const marker = L.marker([news.latitude, news.longitude], { icon: customIcon })
            .bindPopup(popupContent, { minWidth: 280, maxWidth: 320 });
            
        // Add to map and our tracking array
        marker.addTo(map);
        mapMarkers.push(marker);
    });
}

// Implement Filtering Logic
function applyFilters() {
    const category = document.getElementById('categoryFilter').value;
    const district = document.getElementById('locationFilter').value;
    const dateRange = document.getElementById('dateFilter').value;
    
    // Calculate date bounds for filtering
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterdayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    
    const filteredData = allNewsData.filter(news => {
        // Category Filter
        if (category !== 'all' && news.category !== category) return false;
        
        // Location Filter (Text match in the extracted location string)
        if (district !== 'all') {
            if (!news.location_text || !news.location_text.includes(district)) return false;
        }
        
        // Date Filter
        if (dateRange !== 'all') {
            const newsDate = new Date(news.publish_date);
            if (dateRange === 'today' && newsDate < todayStart) return false;
            if (dateRange === 'yesterday' && (newsDate >= todayStart || newsDate < yesterdayStart)) return false;
        }
        
        return true;
    });
    
    renderMarkers(filteredData);
}

// Event Listeners
document.getElementById('applyFiltersBtn').addEventListener('click', () => {
    applyFilters();
    // Re-adjust map bounds to show markers (optional UX enhancement)
    if (mapMarkers.length > 0) {
        const group = new L.featureGroup(mapMarkers);
        map.fitBounds(group.getBounds(), { padding: [50, 50], maxZoom: 13 });
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadNews();
    
    // Check local storage for theme preference
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
});

// Theme Toggler Logic
const themeBtn = document.getElementById('themeToggleBtn');
themeBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    const icon = themeBtn.querySelector('i');
    if (theme === 'light') {
        icon.className = 'fa-solid fa-moon';
        // Optional: Update map tiles to light mode if desired
    } else {
        icon.className = 'fa-solid fa-sun';
    }
}

// Scraper Trigger Logic
const triggerScraperBtn = document.getElementById('triggerScraperBtn');
triggerScraperBtn.addEventListener('click', async () => {
    const icon = triggerScraperBtn.querySelector('i');
    icon.classList.add('fa-spin');
    triggerScraperBtn.disabled = true;
    
    try {
        const response = await fetch('/api/scrape', { method: 'POST' });
        const result = await response.json();
        console.log(result.message);
        
        // Let it spin for a bit to show it's working in the background
        setTimeout(() => {
            icon.classList.remove('fa-spin');
            triggerScraperBtn.disabled = false;
            // Reload the news to show new data
            loadNews();
        }, 3000);
        
    } catch (error) {
        console.error("Error triggering scraper:", error);
        icon.classList.remove('fa-spin');
        triggerScraperBtn.disabled = false;
    }
});
