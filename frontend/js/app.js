// Initialize Leaflet Map anchored roughly around Kocaeli, Turkey
// Using Light Mode tiles from CartoDB for a standard Google Maps look
const map = L.map('map').setView([40.7654, 29.9408], 11);

L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// Color mapping for markers based on category
const categoryColors = {
    "Trafik Kazası": "#ff5e5e",
    "Yangın": "#ffaa00",
    "Elektrik Kesintisi": "#00bcd4",
    "Hırsızlık": "#9c27b0",
    "Kültürel Etkinlikler": "#4caf50",
    "Diğer": "#707070"
};

const categoryClasses = {
    "Trafik Kazası": "cat-trafik",
    "Yangın": "cat-yangin",
    "Elektrik Kesintisi": "cat-elektrik",
    "Hırsızlık": "cat-hirsizlik",
    "Kültürel Etkinlikler": "cat-kulturel",
    "Diğer": "cat-other"
};

// Global scope to store markers and data
let allNewsData = [];
let mapMarkers = [];

// Helper function to create custom colored SVG markers
function createCustomIcon(color) {
    const svgMarker = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
            <path fill="${color}" stroke="#ffffff" stroke-width="2" d="M16 0C10.5 0 6 4.5 6 10c0 7.5 10 22 10 22s10-14.5 10-22c0-5.5-4.5-10-10-10z"/>
            <circle fill="#ffffff" cx="16" cy="10" r="4"/>
        </svg>`;
    
    return L.divIcon({
        className: 'custom-div-icon',
        html: svgMarker,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
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
        const customIcon = createCustomIcon(catColor);
        
        // Parse the date
        const dateObj = new Date(news.publish_date);
        const dateString = dateObj.toLocaleDateString('tr-TR', { 
            day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute:'2-digit' 
        });
        
        const catClass = categoryClasses[news.category] || "cat-other";
        
        // Popup Content Template
        const popupContent = `
            <div class="popup-header">
                <span class="popup-category ${catClass}">${news.category}</span>
                <div class="popup-title">${news.title}</div>
            </div>
            <div class="popup-meta">
                <div><i class="fa-solid fa-clock"></i> ${dateString}</div>
                <div><i class="fa-solid fa-newspaper"></i> ${news.source}</div>
                <div><i class="fa-solid fa-location-crosshairs"></i> ${news.location_text}</div>
            </div>
            <a href="${news.url}" target="_blank" class="popup-link">Habere Git <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.75rem; margin-left: 5px;"></i></a>
        `;
        
        // Create marker
        const marker = L.marker([news.latitude, news.longitude], { icon: customIcon })
            .bindPopup(popupContent, { minWidth: 260, maxWidth: 320 });
            
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
