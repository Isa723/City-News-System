// Google Maps Global Objects
let map;
let allNewsData = [];
let mapMarkers = [];
let infoWindow;

// Center of Kocaeli (İzmit)
const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };

// Initialize Google Map
function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 11,
        center: KOCAELI_CENTER,
        mapId: "DEMO_MAP_ID", // Required for some advanced features if needed
        styles: [
            { "featureType": "poi", "stylers": [{ "visibility": "off" }] } // Clean map
        ]
    });

    infoWindow = new google.maps.InfoWindow();
    
    // Once map is ready, load the news
    loadNews();
}

// Icon mapping for FontAwesome symbols
const categoryIcons = {
    "Trafik Kazası": "fa-car-burst",
    "Yangın": "fa-fire",
    "Elektrik Kesintisi": "fa-bolt",
    "Hırsızlık": "fa-user-secret",
    "Kültürel Etkinlikler": "fa-masks-theater",
    "Diğer": "fa-circle-info"
};

const categoryColors = {
    "Trafik Kazası": "#ff5e5e",
    "Yangın": "#ffaa00",
    "Elektrik Kesintisi": "#00bcd4",
    "Hırsızlık": "#9c27b0",
    "Kültürel Etkinlikler": "#4caf50",
    "Diğer": "#707070"
};

// SVG Paths for symbols (Simple versions of FontAwesome icons)
const categoryPaths = {
    "Trafik Kazası": "M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z", // Car
    "Yangın": "M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8c0-6-4-10.74-4-10.74l-2.5-2.59zM11.89 19.74c-2.32 0-4.2-1.88-4.2-4.2 0-1.2.5-2.29 1.3-3.07.06-.06.27-.24.27-.24l1.37-1.3s1.26 1.13 1.26 3.58c0 1.05.85 1.91 1.91 1.91s1.91-.85 1.91-1.91c0-2-1-3.6-1-3.6s2.5 1.6 2.5 5.56c.01 2.32-1.87 4.27-4.19 4.27z", // Fire
    "Elektrik Kesintisi": "M7 2v11h3v9l7-12h-4l4-8z", // Bolt
    "Hırsızlık": "M17 12c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zm0 8c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zM12 17c0-2.76-2.24-5-5-5s-5 2.24-5 5 2.24 5 5 5 5-2.24 5-5zm-5 3c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm15-4v-1c0-4.42-3.58-8-8-8s-8 3.58-8 8v1c-1.1 0-2 .9-2 2v3c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2v-3c0-1.1-.9-2-2-2z", // Secret/Mask
    "Kültürel Etkinlikler": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm4.5-9c.83 0 1.5-.67 1.5-1.5S17.33 8 16.5 8s-1.5.67-1.5 1.5.67 1.5 1.5 1.5zm-9 0c.83 0 1.5-.67 1.5-1.5S8.33 8 7.5 8s-1.5.67-1.5 1.5.67 1.5 1.5 1.5zm4.5 4.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z", // Smile
    "Diğer": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" // Info
};

const categoryClasses = {
    "Trafik Kazası": "cat-trafik",
    "Yangın": "cat-yangin",
    "Elektrik Kesintisi": "cat-elektrik",
    "Hırsızlık": "cat-hirsizlik",
    "Kültürel Etkinlikler": "cat-kulturel",
    "Diğer": "cat-other"
};

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

// Render markers on the map using Google Maps
function renderMarkers(filteredData) {
    // Clear old markers first
    mapMarkers.forEach(marker => marker.setMap(null));
    mapMarkers = [];
    
    // Update Stats
    document.getElementById('totalNewsStat').innerText = filteredData.length;
    
    filteredData.forEach(news => {
        if (!news.latitude || !news.longitude) return;
        
        const catColor = categoryColors[news.category] || categoryColors["Diğer"];
        const iconClass = categoryIcons[news.category] || categoryIcons["Diğer"];
        const pathData = categoryPaths[news.category] || categoryPaths["Diğer"];
        
        // Creating a Marker with a Custom Symbol (Section 8 requirement: Symbol and Color must differ)
        const marker = new google.maps.Marker({
            position: { lat: news.latitude, lng: news.longitude },
            map: map,
            title: news.title,
            icon: {
                path: pathData,
                fillColor: catColor,
                fillOpacity: 1,
                strokeColor: '#FFFFFF',
                strokeWeight: 1.5,
                scale: 1.2,
                anchor: new google.maps.Point(12, 12)
            }
        });

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
            sourcesHtml = `
                <div class="source-item">
                    <span class="source-name">${news.source}</span>
                    <a href="${news.url}" target="_blank" class="go-to-btn">Habere Git <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>`;
        }
        
        // Popup Content Template (Google Maps uses InfoWindow)
        const popupContent = `
            <div class="g-popup-wrap">
                <div class="popup-header">
                    <span class="popup-category ${catClass}"><i class="fa-solid ${iconClass}"></i> ${news.category}</span>
                    <div class="popup-title">${news.title}</div>
                </div>
                <div class="popup-meta">
                    <div style="color:#8b949e; font-size:12px; margin-bottom:4px;"><i class="fa-solid fa-clock"></i> ${dateString}</div>
                    <div style="color:#8b949e; font-size:12px; margin-bottom:8px;"><i class="fa-solid fa-location-crosshairs"></i> ${news.location_text}</div>
                </div>
                <div class="sources-list" style="margin-top:10px; border-top:1px solid #30363d; padding-top:10px;">
                    <div class="sources-label" style="font-size:11px; font-weight:bold; color:#8b949e; margin-bottom:5px;">KAYNAKLAR:</div>
                    ${sourcesHtml}
                </div>
                <div class="popup-footer" style="margin-top:10px;">
                    <p class="popup-snippet" style="font-size:12px; font-style:italic; color:#8b949e;">${news.content.substring(0, 100)}...</p>
                </div>
            </div>
        `;
        
        marker.addListener("click", () => {
            infoWindow.setContent(popupContent);
            infoWindow.open(map, marker);
        });
            
        mapMarkers.push(marker);
    });
}

// Implement Filtering Logic
function applyFilters() {
    const category = document.getElementById('categoryFilter').value;
    const district = document.getElementById('locationFilter').value;
    const dateRange = document.getElementById('dateFilter').value;
    
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterdayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    
    const filteredData = allNewsData.filter(news => {
        if (category !== 'all' && news.category !== category) return false;
        if (district !== 'all') {
            if (!news.location_text || !news.location_text.includes(district)) return false;
        }
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
    if (mapMarkers.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        mapMarkers.forEach(m => bounds.extend(m.getPosition()));
        map.fitBounds(bounds);
    }
});

// Theme Toggler Logic
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
});

const themeBtn = document.getElementById('themeToggleBtn');
themeBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
});

// Scraper Trigger Logic
const triggerScraperBtn = document.getElementById('triggerScraperBtn');
triggerScraperBtn.addEventListener('click', async () => {
    const icon = triggerScraperBtn.querySelector('i');
    icon.classList.add('fa-spin');
    triggerScraperBtn.disabled = true;
    
    try {
        const response = await fetch('/api/scrape', { method: 'POST' });
        const result = await response.json();
        
        setTimeout(() => {
            icon.classList.remove('fa-spin');
            triggerScraperBtn.disabled = false;
            loadNews();
        }, 3000);
        
    } catch (error) {
        console.error("Error triggering scraper:", error);
        icon.classList.remove('fa-spin');
        triggerScraperBtn.disabled = false;
    }
});
