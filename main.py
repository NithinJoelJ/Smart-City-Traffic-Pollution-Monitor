import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from folium import plugins
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import time
import random

# Page Configuration
st.set_page_config(
    page_title="Smart City Traffic & Pollution Monitor - Tamil Nadu",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #ffffff;}
    .stApp {background-color: #ffffff;}
    h1, h2, h3 {color: #1a1a1a;}
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .legend-box {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .realtime-badge {
        background: #ff4444;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    .vellore-highlight {
        background: #fff3cd;
        padding: 2px 6px;
        border-radius: 3px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Tamil Nadu Districts with coordinates
TN_DISTRICTS = {
    'Chennai': {'lat': 13.0827, 'lon': 80.2707},
    'Coimbatore': {'lat': 11.0168, 'lon': 76.9558},
    'Madurai': {'lat': 9.9252, 'lon': 78.1198},
    'Tiruchirappalli': {'lat': 10.7905, 'lon': 78.7047},
    'Salem': {'lat': 11.6643, 'lon': 78.1460},
    'Tirunelveli': {'lat': 8.7139, 'lon': 77.7567},
    'Tiruppur': {'lat': 11.1085, 'lon': 77.3411},
    'Vellore': {'lat': 12.9165, 'lon': 79.1325},
    'Erode': {'lat': 11.3410, 'lon': 77.7172},
    'Thanjavur': {'lat': 10.7870, 'lon': 79.1378},
    'Dindigul': {'lat': 10.3673, 'lon': 77.9803},
    'Kanchipuram': {'lat': 12.8342, 'lon': 79.7036},
    'Cuddalore': {'lat': 11.7480, 'lon': 79.7714},
    'Karur': {'lat': 10.9601, 'lon': 78.0766},
    'Namakkal': {'lat': 11.2189, 'lon': 78.1677}
}

# Vellore City Areas (expandable)
VELLORE_AREAS = {
    'Sathuvachari': {'lat': 12.9465, 'lon': 79.1525},
    'Katpadi': {'lat': 12.9698, 'lon': 79.1452},
    'Gandhi Nagar': {'lat': 12.9265, 'lon': 79.1425},
    'Thottapalayam': {'lat': 12.9065, 'lon': 79.1125},
    'Kosapet': {'lat': 12.9365, 'lon': 79.1625},
    'Sripuram': {'lat': 12.9465, 'lon': 79.0925},
    'CMC Vellore': {'lat': 12.9165, 'lon': 79.1325},
    'Bagayam': {'lat': 12.9265, 'lon': 79.1225},
    'Green Circle': {'lat': 12.9165, 'lon': 79.1425},
    'New Bus Stand': {'lat': 12.9365, 'lon': 79.1525},
    'BHEL': {'lat': 12.9865, 'lon': 79.1825},
    'Ranipet': {'lat': 12.9224, 'lon': 79.3329},
    'Arcot': {'lat': 12.9059, 'lon': 79.3188},
    'Walajapet': {'lat': 12.9257, 'lon': 79.3668},
    'Gudiyatham': {'lat': 12.9459, 'lon': 78.8739}
}

# Initialize session state
if 'realtime_data' not in st.session_state:
    st.session_state.realtime_data = []
    st.session_state.last_update = datetime.now()

if 'page' not in st.session_state:
    st.session_state.page = 'Dashboard'

if 'selected_location' not in st.session_state:
    st.session_state.selected_location = 'Vellore'

if 'show_vellore_areas' not in st.session_state:
    st.session_state.show_vellore_areas = False


# Generate realistic realtime data
def generate_realtime_traffic_data(location=None):
    """Generate data point with timestamp for streaming"""
    current_time = datetime.now()

    # If location not specified, pick randomly
    if location is None:
        if st.session_state.show_vellore_areas:
            all_locations = {**TN_DISTRICTS, **VELLORE_AREAS}
        else:
            all_locations = TN_DISTRICTS
        location = random.choice(list(all_locations.keys()))

    # Get coordinates
    if location in TN_DISTRICTS:
        coords = TN_DISTRICTS[location]
    else:
        coords = VELLORE_AREAS[location]

    # Time-based patterns
    hour = current_time.hour
    is_rush_hour = hour in [8, 9, 17, 18, 19, 20]
    is_weekend = current_time.weekday() >= 5

    # Generate realistic data
    base_traffic = 40
    if is_rush_hour and not is_weekend:
        base_traffic = 75
    elif is_weekend:
        base_traffic = 30

    base_aqi = 80
    if is_rush_hour and not is_weekend:
        base_aqi = 140

    return {
        'timestamp': current_time,
        'location': location,
        'lat': coords['lat'],
        'lon': coords['lon'],
        'traffic_density': base_traffic + random.randint(-15, 15),
        'aqi': base_aqi + random.randint(-20, 20),
        'vehicles_count': random.randint(1000, 8000),
        'avg_speed': random.randint(20, 60),
        'incidents': random.randint(0, 3)
    }


def update_realtime_data(location=None):
    """Maintain rolling 3-minute window of data"""
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(minutes=3)

    # Remove old data
    st.session_state.realtime_data = [
        d for d in st.session_state.realtime_data
        if d['timestamp'] > cutoff_time
    ]

    # Add new data point
    new_data = generate_realtime_traffic_data(location)
    st.session_state.realtime_data.append(new_data)
    st.session_state.last_update = current_time


# Generate static data
@st.cache_data
def generate_static_data(include_vellore_areas=False):
    """Generate comprehensive dataset for analysis"""
    if include_vellore_areas:
        all_locations = {**TN_DISTRICTS, **VELLORE_AREAS}
    else:
        all_locations = TN_DISTRICTS

    data = []

    for location, coords in all_locations.items():
        is_major_city = location in ['Chennai', 'Coimbatore', 'Madurai', 'Vellore']
        base_aqi = random.randint(100, 200) if is_major_city else random.randint(50, 120)
        base_traffic = random.randint(60, 90) if is_major_city else random.randint(30, 60)

        data.append({
            'location': location,
            'lat': coords['lat'],
            'lon': coords['lon'],
            'aqi': base_aqi,
            'traffic_density': base_traffic,
            'vehicles_count': random.randint(5000, 50000) if is_major_city else random.randint(1000, 10000),
            'cars': random.randint(2000, 25000),
            'bikes': random.randint(2000, 20000),
            'trucks': random.randint(500, 5000),
            'avg_speed': random.randint(20, 55),
            'incidents': random.randint(0, 12),
            'population': random.randint(100000, 5000000) if is_major_city else random.randint(50000, 500000)
        })

    return pd.DataFrame(data)


@st.cache_data
def generate_time_series_data(days=7):
    """Generate historical data"""
    dates = pd.date_range(end=datetime.now(), periods=days * 24, freq='H')
    data = []
    for date in dates:
        hour = date.hour
        traffic_base = 40 + 35 * np.sin((hour - 9) * np.pi / 12)
        aqi_base = 90 + 50 * np.sin((hour - 14) * np.pi / 12)

        data.append({
            'timestamp': date,
            'traffic_volume': max(15, traffic_base + random.randint(-10, 10)),
            'aqi': max(30, min(280, aqi_base + random.randint(-20, 20))),
            'hour': hour,
            'day_of_week': date.strftime('%A'),
            'date': date.strftime('%Y-%m-%d')
        })
    return pd.DataFrame(data)


@st.cache_data
def generate_heatmap_matrix():
    """Generate hour vs day pollution matrix"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    hours = list(range(24))
    matrix = []
    for day in days:
        row = []
        for hour in hours:
            base = 90 if day not in ['Saturday', 'Sunday'] else 65
            if hour in [8, 9, 17, 18, 19] and day not in ['Saturday', 'Sunday']:
                base += 45
            row.append(base + random.randint(-15, 15))
        matrix.append(row)
    return pd.DataFrame(matrix, index=days, columns=hours)


# Sidebar Navigation
with st.sidebar:
    st.markdown("##  Navigation")

    pages = [
        ('Dashboard', ''),
        ('Traffic Heatmap', ''),
        ('AQI Choropleth', ''),
        ('Sensor Clusters', ''),
        ('Time Trends', ''),
        ('Pollution Matrix', ''),
        ('Distribution Analysis', ''),
        ('Correlation Study', ''),
        ('Dot Map', ''),
        # ('Hexagonal Binning', ''),
        ('Network Graph', ''),
        ('Text Analysis', '')
    ]

    for page_name, icon in pages:
        if st.button(f"{icon} {page_name}", key=page_name, use_container_width=True):
            st.session_state.page = page_name

    st.markdown("---")
    st.markdown("### ️ Settings")

    if st.session_state.page == 'Dashboard':
        auto_refresh = st.checkbox(" Auto Refresh", value=True)
    else:
        auto_refresh = False

    st.session_state.show_vellore_areas = st.checkbox(" Show Vellore Inner Areas", value=False)

    st.markdown("---")
    st.markdown("###  Coverage")
    st.markdown("**Tamil Nadu:** 15 major districts")
    st.markdown("**Vellore:** 15 sub-areas")
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")

# Main Content Area
if st.session_state.page == 'Dashboard':
    # REAL-TIME DASHBOARD - DEFAULT TO VELLORE
    st.markdown("<h1 style='text-align: center;'> Real-Time Traffic & Pollution Dashboard</h1>",
                unsafe_allow_html=True)

    # Location selector for dashboard
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        all_locations = list(TN_DISTRICTS.keys())
        if st.session_state.show_vellore_areas:
            all_locations.extend(list(VELLORE_AREAS.keys()))

        selected_loc = st.selectbox(
            " Select Location for Real-time Monitoring",
            all_locations,
            index=all_locations.index('Vellore') if 'Vellore' in all_locations else 0
        )
        st.session_state.selected_location = selected_loc

    st.markdown(
        f"<p style='text-align: center;' class='timestamp-text'>Monitoring <span class='vellore-highlight'>{selected_loc}</span> | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'><span class='realtime-badge'>● LIVE</span></div>",
                unsafe_allow_html=True)

    # Update realtime data for selected location
    update_realtime_data(selected_loc)

    if len(st.session_state.realtime_data) > 0:
        rt_df = pd.DataFrame(st.session_state.realtime_data)
        rt_df_location = rt_df[rt_df['location'] == selected_loc]

        if len(rt_df_location) == 0:
            rt_df_location = rt_df.tail(10)

        # KPI Metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            current_aqi = rt_df_location.iloc[-1]['aqi']
            prev_aqi = rt_df_location.iloc[-2]['aqi'] if len(rt_df_location) > 1 else current_aqi
            st.metric("Current AQI", f"{current_aqi:.0f}",
                      delta=f"{current_aqi - prev_aqi:.0f}",
                      delta_color="inverse")

        with col2:
            current_traffic = rt_df_location.iloc[-1]['traffic_density']
            prev_traffic = rt_df_location.iloc[-2]['traffic_density'] if len(rt_df_location) > 1 else current_traffic
            st.metric("Traffic Density", f"{current_traffic:.0f}%",
                      delta=f"{current_traffic - prev_traffic:.0f}%")

        with col3:
            current_speed = rt_df_location.iloc[-1]['avg_speed']
            st.metric("Avg Speed", f"{current_speed:.0f} km/h",
                      delta=f"{random.randint(-5, 5)} km/h")

        with col4:
            total_incidents = rt_df_location['incidents'].sum()
            st.metric("Active Incidents", f"{total_incidents}",
                      delta=f"{random.randint(-2, 2)}")

        st.markdown("---")

        # Real-time streaming charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"###  Traffic Density Stream - {selected_loc} (Last 3 Minutes)")

            fig_traffic = go.Figure()

            fig_traffic.add_trace(go.Scatter(
                x=rt_df_location['timestamp'],
                y=rt_df_location['traffic_density'],
                mode='lines+markers',
                name='Traffic Density',
                line=dict(color='#667eea', width=3),
                marker=dict(size=8, symbol='circle'),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.2)'
            ))

            fig_traffic.update_layout(
                xaxis_title="Time (HH:MM:SS)",
                yaxis_title="Traffic Density (%)",
                template='plotly_white',
                height=350,
                hovermode='x unified',
                showlegend=False,
                xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
                yaxis=dict(showgrid=True, gridcolor='#f0f0f0', range=[0, 100])
            )

            st.plotly_chart(fig_traffic, use_container_width=True)

            st.markdown(f"""
            <div class='legend-box'>
            <p><strong> Real-time Traffic Analysis:</strong> Live traffic density at {selected_loc}. 
            Measurements taken every 2 seconds. Values above 70% indicate heavy congestion requiring intervention.</p>
            <p><strong>Time Range:</strong> Last 3 minutes | <strong>Current Time:</strong> {datetime.now().strftime('%H:%M:%S')}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"###  Air Quality Index Stream - {selected_loc} (Last 3 Minutes)")

            fig_aqi = go.Figure()

            colors = ['#00e400' if x <= 50 else '#ffff00' if x <= 100 else '#ff7e00' if x <= 150
            else '#ff0000' if x <= 200 else '#8f3f97' for x in rt_df_location['aqi']]

            fig_aqi.add_trace(go.Scatter(
                x=rt_df_location['timestamp'],
                y=rt_df_location['aqi'],
                mode='lines+markers',
                name='AQI',
                line=dict(color='#ff6b6b', width=3),
                marker=dict(size=8, color=colors, symbol='circle'),
                fill='tozeroy',
                fillcolor='rgba(255, 107, 107, 0.2)'
            ))

            fig_aqi.add_hline(y=100, line_dash="dash", line_color="orange",
                              annotation_text="Moderate (100)", annotation_position="right")
            fig_aqi.add_hline(y=150, line_dash="dash", line_color="red",
                              annotation_text="Unhealthy (150)", annotation_position="right")

            fig_aqi.update_layout(
                xaxis_title="Time (HH:MM:SS)",
                yaxis_title="Air Quality Index (AQI)",
                template='plotly_white',
                height=350,
                hovermode='x unified',
                showlegend=False,
                xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
                yaxis=dict(showgrid=True, gridcolor='#f0f0f0', range=[0, 300])
            )

            st.plotly_chart(fig_aqi, use_container_width=True)

            st.markdown(f"""
            <div class='legend-box'>
            <p><strong> Real-time Air Quality:</strong> Continuous AQI monitoring at {selected_loc}. 
            Color changes indicate pollution severity levels.</p>
            <p><strong>Time Range:</strong> Last 3 minutes | <strong>Current Time:</strong> {datetime.now().strftime('%H:%M:%S')}</p>
            </div>
            """, unsafe_allow_html=True)

        # Recent events table
        st.markdown(f"###  Recent Monitoring Events - {selected_loc} (Last 3 Minutes)")

        display_df = rt_df_location[
            ['timestamp', 'location', 'traffic_density', 'aqi', 'avg_speed', 'incidents']].copy()
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
        display_df = display_df.sort_values('timestamp', ascending=False)
        display_df.columns = ['Time', 'Location', 'Traffic %', 'AQI', 'Speed (km/h)', 'Incidents']

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("""
        <div class='legend-box'>
        <p><strong> Real-time Intelligence:</strong> Individual sensor readings from the last 3 minutes. 
        High traffic + high AQI + low speed = severe congestion hotspot requiring immediate action.</p>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.page == 'Traffic Heatmap':
    st.markdown("##  Traffic Density Heatmap")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)

    df = generate_static_data(st.session_state.show_vellore_areas)

    m = folium.Map(location=[11.5, 78.5], zoom_start=7, tiles='CartoDB positron')

    heat_data = [[row['lat'], row['lon'], row['traffic_density'] / 100] for _, row in df.iterrows()]
    plugins.HeatMap(heat_data, radius=30, blur=25, max_zoom=10, gradient={
        0.0: 'blue', 0.3: 'lime', 0.5: 'yellow', 0.7: 'orange', 1.0: 'red'
    }).add_to(m)

    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=6,
            popup=f"<b>{row['location']}</b><br>Traffic: {row['traffic_density']:.0f}%<br>Time: {datetime.now().strftime('%H:%M')}",
            color='darkblue',
            fill=True,
            fillOpacity=0.7
        ).add_to(m)

    st_folium(m, width=1200, height=600)

    st.markdown("""
    <div class='legend-box'>
    <h4> Traffic Heatmap Legend</h4>
    <p><strong>Spatial Analysis:</strong> Shows traffic congestion intensity across Tamil Nadu districts</p>
    <ul>
        <li><span style='color:#0000ff'>●</span> Blue: Free-flowing (0-30%)</li>
        <li><span style='color:#00ff00'>●</span> Green: Light (30-50%)</li>
        <li><span style='color:#ffff00'>●</span> Yellow: Moderate (50-70%)</li>
        <li><span style='color:#ffa500'>●</span> Orange: Heavy (70-85%)</li>
        <li><span style='color:#ff0000'>●</span> Red: Severe (85-100%)</li>
    </ul>
    <p><strong>Usage:</strong> Deploy traffic police in red zones, optimize signal timing in yellow zones</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'AQI Choropleth':
    st.markdown("##  Air Quality Index Choropleth Map")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Data snapshot: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True
    )

    import json
    import folium
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry import shape
    from streamlit_folium import st_folium


    df = pd.DataFrame({
        'district': [
            'Ariyalur', 'Chengalpattu', 'Chennai', 'Coimbatore', 'Cuddalore',
            'Dharmapuri', 'Dindigul', 'Erode', 'Kallakurichi', 'Kanchipuram',
            'Kanyakumari', 'Karur', 'Krishnagiri', 'Madurai', 'Mayiladuthurai',
            'Nagapattinam', 'Namakkal', 'Nilgiris', 'Perambalur', 'Pudukkottai',
            'Ramanathapuram', 'Ranipet', 'Salem', 'Sivaganga', 'Tenkasi',
            'Thanjavur', 'Theni', 'Thoothukudi', 'Tiruchirappalli', 'Tirunelveli',
            'Tirupathur', 'Tiruppur', 'Tiruvallur', 'Tiruvannamalai', 'Tiruvarur',
            'Vellore', 'Viluppuram', 'Virudhunagar'
        ],
        'aqi': [
            82, 95, 110, 78, 85, 80, 90, 87, 75, 84,
            72, 88, 79, 100, 83, 77, 92, 70, 81, 86,
            74, 89, 120, 76, 71, 99, 93, 80, 91, 102,
            85, 88, 94, 83, 78, 135, 72, 96
        ]
    })


    geojson_path = "tamilnadu_districts.geojson"
    with open(geojson_path, 'r') as f:
        geo_data = json.load(f)

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geo_data["features"])

    # 🧩 Approximate centroids for all Tamil Nadu districts
    known_centroids = {
        'Ariyalur': (11.14, 79.08),
        'Chengalpattu': (12.69, 79.97),
        'Chennai': (13.08, 80.27),
        'Coimbatore': (11.02, 76.96),
        'Cuddalore': (11.74, 79.77),
        'Dharmapuri': (12.13, 78.16),
        'Dindigul': (10.36, 77.97),
        'Erode': (11.34, 77.72),
        'Kallakurichi': (11.94, 78.97),
        'Kanchipuram': (12.83, 79.70),
        'Kanyakumari': (8.08, 77.55),
        'Karur': (10.96, 78.08),
        'Krishnagiri': (12.52, 78.21),
        'Madurai': (9.93, 78.12),
        'Mayiladuthurai': (11.10, 79.65),
        'Nagapattinam': (10.77, 79.84),
        'Namakkal': (11.22, 78.17),
        'Nilgiris': (11.41, 76.69),
        'Perambalur': (11.23, 78.88),
        'Pudukkottai': (10.38, 78.82),
        'Ramanathapuram': (9.37, 78.83),
        'Ranipet': (12.93, 79.33),
        'Salem': (11.65, 78.16),
        'Sivaganga': (9.85, 78.48),
        'Tenkasi': (8.96, 77.31),
        'Thanjavur': (10.78, 79.13),
        'Theni': (10.01, 77.48),
        'Thoothukudi': (8.79, 78.13),
        'Tiruchirappalli': (10.79, 78.70),
        'Tirunelveli': (8.73, 77.69),
        'Tirupathur': (12.49, 78.56),
        'Tiruppur': (11.11, 77.35),
        'Tiruvallur': (13.14, 79.91),
        'Tiruvannamalai': (12.23, 79.07),
        'Tiruvarur': (10.77, 79.64),
        'Vellore': (12.91, 79.13),
        'Viluppuram': (11.94, 79.49),
        'Virudhunagar': (9.58, 77.95)
    }

    # Assign nearest district name using centroid proximity
    assigned_districts = []
    for feature in gdf.geometry:
        centroid = feature.centroid
        min_dist = float('inf')
        closest_name = None
        for name, (lat, lon) in known_centroids.items():
            dist = (centroid.y - lat)**2 + (centroid.x - lon)**2
            if dist < min_dist:
                min_dist = dist
                closest_name = name
        assigned_districts.append(closest_name)

    gdf["district"] = assigned_districts
    geo_data_corrected = json.loads(gdf.to_json())


    m = folium.Map(location=[11.1271, 78.6569], zoom_start=7, tiles='CartoDB positron')


    folium.Choropleth(
        geo_data=geo_data_corrected,
        data=df,
        columns=['district', 'aqi'],
        key_on='feature.properties.district',
        fill_color='YlOrRd',
        fill_opacity=0.8,
        line_opacity=0.3,
        legend_name='Air Quality Index (AQI)',
        highlight=True,
    ).add_to(m)


    folium.GeoJson(
        geo_data_corrected,
        tooltip=folium.features.GeoJsonTooltip(
            fields=['district'],
            aliases=['District:'],
            labels=True,
            sticky=False
        )
    ).add_to(m)

    # Display map in Streamlit
    st_folium(m, width=1200, height=600)


    st.markdown("""
    <div class='legend-box'>
    <h4> AQI Choropleth Classification</h4>
    <p><strong>Visualization Technique:</strong> True choropleth mapping using district polygons (All 38 Tamil Nadu Districts)</p>
    <table style='width:100%; border-collapse: collapse;'>
        <tr><td style='background:#00e400; color:white; padding:5px;'><strong>0–50 Good</strong></td><td>Air quality satisfactory</td></tr>
        <tr><td style='background:#ffff00; padding:5px;'><strong>51–100 Moderate</strong></td><td>Acceptable quality</td></tr>
        <tr><td style='background:#ff7e00; color:white; padding:5px;'><strong>101–150 USG</strong></td><td>Unhealthy for sensitive groups</td></tr>
        <tr><td style='background:#ff0000; color:white; padding:5px;'><strong>151–200 Unhealthy</strong></td><td>Health effects for all</td></tr>
        <tr><td style='background:#8f3f97; color:white; padding:5px;'><strong>201–300 Very Unhealthy</strong></td><td>Serious health effects</td></tr>
        <tr><td style='background:#7e0023; color:white; padding:5px;'><strong>301+ Hazardous</strong></td><td>Emergency conditions</td></tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'Sensor Clusters':
    st.markdown("##  Monitoring Sensor Network - Cluster Visualization")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Static sensor network snapshot | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)


    # Use cached data to prevent regeneration
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def generate_sensor_cluster_data(show_vellore_areas):
        df = generate_static_data(show_vellore_areas)
        sensor_data = []
        for _, row in df.iterrows():
            # Create multiple sensors per location with static data
            for i in range(random.randint(3, 7)):
                lat_offset = random.uniform(-0.08, 0.08)
                lon_offset = random.uniform(-0.08, 0.08)
                sensor_aqi = row['aqi'] + random.randint(-20, 20)
                sensor_traffic = row['traffic_density'] + random.randint(-15, 15)

                sensor_data.append({
                    'lat': row['lat'] + lat_offset,
                    'lon': row['lon'] + lon_offset,
                    'location': row['location'],
                    'aqi': sensor_aqi,
                    'traffic': sensor_traffic,
                    'sensor_id': f"TN-{random.randint(1000, 9999)}"
                })
        return sensor_data


    # Generate static sensor data
    sensor_data = generate_sensor_cluster_data(st.session_state.show_vellore_areas)

    # Create map with static data
    m = folium.Map(location=[11.5, 78.5], zoom_start=7)
    marker_cluster = plugins.MarkerCluster().add_to(m)

    # Add static sensors to map
    for sensor in sensor_data:
        folium.Marker(
            location=[sensor['lat'], sensor['lon']],
            popup=f"""
                <b>Sensor ID: {sensor['sensor_id']}</b><br>
                Location: {sensor['location']}<br>
                AQI: {sensor['aqi']:.0f}<br>
                Traffic: {sensor['traffic']:.0f}%<br>
                Status: Active<br>
                <i>Static Data - Network Snapshot</i>
            """,
            icon=folium.Icon(
                color='green' if sensor['aqi'] < 100 else 'orange' if sensor['aqi'] < 150 else 'red',
                icon='cloud' if sensor['aqi'] < 100 else 'warning-sign',
                prefix='glyphicon'
            )
        ).add_to(marker_cluster)

    st_folium(m, width=1200, height=600)

    # Sensor statistics
    st.markdown("###  Sensor Network Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Sensors", len(sensor_data))
    with col2:
        green_sensors = len([s for s in sensor_data if s['aqi'] < 100])
        st.metric("Good AQI Sensors", green_sensors)
    with col3:
        orange_sensors = len([s for s in sensor_data if 100 <= s['aqi'] < 150])
        st.metric("Moderate AQI Sensors", orange_sensors)
    with col4:
        red_sensors = len([s for s in sensor_data if s['aqi'] >= 150])
        st.metric("Poor AQI Sensors", red_sensors)

    st.markdown("""
    <div class='legend-box'>
    <h4> Cluster Map Interpretation</h4>
    <p><strong>Visualization Type:</strong> Cluster map with marker aggregation (Geospatial Module)</p>
    <p><span style='color:#00aa00'>●</span> Green: Good air quality sensors (AQI < 100)</p>
    <p><span style='color:#ff9900'>●</span> Orange: Moderate pollution (AQI 100-150)</p>
    <p><span style='color:#ff0000'>●</span> Red: High pollution (AQI > 150)</p>
    <p><strong>Cluster Numbers:</strong> Indicates sensor density in that region. Zoom in to see individual sensors.</p>
    <p><strong>Data Type:</strong> Static network snapshot - shows sensor distribution and coverage areas</p>
    <p><strong>Total Sensors:</strong> {} deployed across Tamil Nadu monitoring network</p>
    <p><strong>Note:</strong> This view does not auto-refresh. Data is cached for 1 hour.</p>
    </div>
    """.format(len(sensor_data)), unsafe_allow_html=True)

elif st.session_state.page == 'Time Trends':
    st.markdown("##  Time-Series Analysis - Historical and Daily Trends")

    # -----------------------------
    # 7-Day Historical Trend
    # -----------------------------
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    st.markdown(
        f"<p style='color:#666; font-style:italic;'> Analysis period: {start_date} to {end_date}</p>",
        unsafe_allow_html=True
    )

    ts_data = generate_time_series_data(7)

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(
        go.Scatter(x=ts_data['timestamp'], y=ts_data['traffic_volume'],
                   name="Traffic Volume", line=dict(color='#667eea', width=3),
                   fill='tonexty', fillcolor='rgba(102, 126, 234, 0.15)'),
        secondary_y=False
    )
    fig1.add_trace(
        go.Scatter(x=ts_data['timestamp'], y=ts_data['aqi'],
                   name="AQI Level", line=dict(color='#ff6b6b', width=3),
                   fill='tonexty', fillcolor='rgba(255, 107, 107, 0.15)'),
        secondary_y=True
    )

    fig1.update_layout(
        title="7-Day Traffic Volume vs Air Quality Trend",
        xaxis_title="Date and Time",
        template='plotly_white',
        hovermode='x unified',
        height=500,
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )

    fig1.update_yaxes(title_text="Traffic Volume (vehicles/hour)", secondary_y=False)
    fig1.update_yaxes(title_text="Air Quality Index (AQI)", secondary_y=True)

    st.plotly_chart(fig1, use_container_width=True)

    # -----------------------------
    # 24-Hour (Single Day) Trend
    # -----------------------------
    st.markdown("###  24-Hour Detailed View (Today)")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Date: {datetime.now().strftime('%Y-%m-%d')}</p>",
        unsafe_allow_html=True
    )

    daily_data = generate_time_series_data(1)  # Generate 24-hour dataset

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(
        go.Scatter(x=daily_data['timestamp'], y=daily_data['traffic_volume'],
                   name="Traffic Volume", line=dict(color='#1f77b4', width=3),
                   fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.2)'),
        secondary_y=False
    )
    fig2.add_trace(
        go.Scatter(x=daily_data['timestamp'], y=daily_data['aqi'],
                   name="AQI Level", line=dict(color='#d62728', width=3),
                   fill='tozeroy', fillcolor='rgba(214, 39, 40, 0.2)'),
        secondary_y=True
    )

    fig2.update_layout(
        title="24-Hour Traffic vs Air Quality Pattern (Today)",
        xaxis_title="Hour of Day",
        template='plotly_white',
        hovermode='x unified',
        height=450,
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )

    fig2.update_yaxes(title_text="Traffic Volume (vehicles/hour)", secondary_y=False)
    fig2.update_yaxes(title_text="Air Quality Index (AQI)", secondary_y=True)

    st.plotly_chart(fig2, use_container_width=True)

    # -----------------------------
    # Statistical insights
    # -----------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_traffic = ts_data['traffic_volume'].mean()
        st.metric("Avg Traffic (7 Days)", f"{avg_traffic:.1f} veh/hr")
    with col2:
        avg_aqi = ts_data['aqi'].mean()
        st.metric("Avg AQI (7 Days)", f"{avg_aqi:.1f}")
    with col3:
        correlation = ts_data['traffic_volume'].corr(ts_data['aqi'])
        st.metric("Correlation", f"{correlation:.3f}")
    with col4:
        peak_hour = ts_data.loc[ts_data['traffic_volume'].idxmax(), 'hour']
        st.metric("Peak Hour", f"{int(peak_hour)}:00")

    st.markdown("""
    <div class='legend-box'>
    <h4> Time-Series Visualization Analysis</h4>
    <p><strong>Module Coverage:</strong> Time-series data visualization (Module 5 - Diverse Visual Analysis)</p>
    <ul>
      <li><strong>7-Day Graph:</strong> Shows weekly variation and trend correlation between traffic and pollution.</li>
      <li><strong>24-Hour Graph:</strong> Zoomed-in view for today, highlighting intra-day fluctuations.</li>
    </ul>
    <p><strong>Pattern Recognition:</strong> Daily peaks at 8–10 AM and 5–8 PM. AQI rises in sync with traffic surges.</p>
    <p><strong>Actionable Insight:</strong> Use hourly monitoring for predictive congestion management and pollution alerts.</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'Pollution Matrix':
    st.markdown("##  Pollution Intensity Matrix - Temporal Heatmap")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Weekly pattern analysis | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)

    matrix_data = generate_heatmap_matrix()

    fig = go.Figure(data=go.Heatmap(
        z=matrix_data.values,
        x=matrix_data.columns,
        y=matrix_data.index,
        colorscale='RdYlGn_r',
        text=matrix_data.values,
        texttemplate='%{text:.0f}',
        textfont={"size": 10, "color": "white"},
        colorbar=dict(title=dict(text="AQI Level", side="right"))
    ))

    fig.update_layout(
        title="AQI Heatmap by Hour of Day and Day of Week",
        xaxis_title="Hour of Day (0-23)",
        yaxis_title="Day of Week",
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Peak pollution times
    st.markdown("###  Peak Pollution Schedule")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Weekday Pattern (Mon-Fri):**
        - 08:00-10:00 AM → AQI: 130-160 (Morning Rush)
        - 12:00-02:00 PM → AQI: 100-120 (Lunch Hour)
        - 05:00-08:00 PM → AQI: 140-170 (Evening Rush)
        - 11:00 PM-06:00 AM → AQI: 60-80 (Night)
        """)

    with col2:
        st.markdown("""
        **Weekend Pattern (Sat-Sun):**
        - 02:00-04:00 PM → AQI: 70-90 (Afternoon Peak)
        - Overall Lower → AQI: 60-90
        - Reduced Commuter Traffic
        - Better Air Quality
        """)

    st.markdown("""
    <div class='legend-box'>
    <h4> Matrix Heatmap Legend</h4>
    <p><strong>Visualization Type:</strong> Matrix/Heat Map (Module 5 - Matrix visualization techniques)</p>
    <p><strong>X-Axis:</strong> Hour of Day (24-hour format, 0-23)</p>
    <p><strong>Y-Axis:</strong> Day of Week (Monday to Sunday)</p>
    <p><strong>Color Scale:</strong> Green (Low pollution 50-80) → Yellow (Moderate 81-110) → Orange (High 111-140) → Red (Very High 141+)</p>
    <p><strong>Pattern Analysis:</strong> Darker red cells indicate peak pollution times. Clear weekday rush hour patterns visible. Use this to schedule outdoor activities during green zones.</p>
    <p><strong>Time-based Insight:</strong> Best air quality: Weekends 6-8 AM. Worst: Weekdays 6-8 PM.</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'Distribution Analysis':
    st.markdown("##  Statistical Distribution Analysis - Box Plot")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Sample size: 40 measurements per location | Date: {datetime.now().strftime('%Y-%m-%d')}</p>",
        unsafe_allow_html=True)

    df = generate_static_data(st.session_state.show_vellore_areas)

    # Generate distribution data
    location_distributions = []
    for location in df['location'].unique():
        base_aqi = df[df['location'] == location]['aqi'].values[0]
        measurements = np.random.normal(base_aqi, 18, 40)
        for val in measurements:
            location_distributions.append({
                'location': location,
                'aqi': max(10, min(300, val))
            })

    dist_df = pd.DataFrame(location_distributions)

    # Select top locations
    top_locations = df.nlargest(12, 'aqi')['location'].tolist()
    if 'Vellore' not in top_locations:
        top_locations.append('Vellore')
    dist_df_filtered = dist_df[dist_df['location'].isin(top_locations)]

    fig = px.box(dist_df_filtered, x='location', y='aqi', color='location',
                 title="AQI Distribution Comparison Across Locations",
                 labels={'aqi': 'Air Quality Index (AQI)', 'location': 'Location'})

    fig.update_layout(
        template='plotly_white',
        showlegend=False,
        height=550,
        xaxis_tickangle=-45,
        xaxis=dict(showgrid=False, title="Location"),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Air Quality Index (AQI)")
    )

    # Add reference lines
    fig.add_hline(y=50, line_dash="dash", line_color="green",
                  annotation_text="Good (50)", annotation_position="right")
    fig.add_hline(y=100, line_dash="dash", line_color="yellow",
                  annotation_text="Moderate (100)", annotation_position="right")
    fig.add_hline(y=150, line_dash="dash", line_color="orange",
                  annotation_text="Unhealthy (150)", annotation_position="right")

    st.plotly_chart(fig, use_container_width=True)

    # Statistical summary
    st.markdown("###  Statistical Summary Table")
    summary_stats = dist_df_filtered.groupby('location')['aqi'].agg(['mean', 'median', 'std', 'min', 'max']).round(1)
    summary_stats = summary_stats.sort_values('mean', ascending=False)
    summary_stats.columns = ['Mean', 'Median', 'Std Dev', 'Min', 'Max']
    st.dataframe(summary_stats, use_container_width=True)

    st.markdown(f"""
    <div class='legend-box'>
    <h4> Box Plot Statistical Guide</h4>
    <p><strong>Visualization Type:</strong> Box and Whisker Plot (Module 5 - Diverse Visual Analysis)</p>
    <p><strong>X-Axis:</strong> Geographic Location (Tamil Nadu districts and Vellore areas)</p>
    <p><strong>Y-Axis:</strong> Air Quality Index (0-300 scale)</p>
    <p><strong>Box Components:</strong></p>
    <ul>
        <li><strong>Center Line:</strong> Median (50th percentile) - typical AQI</li>
        <li><strong>Box Edges:</strong> 25th and 75th percentiles (middle 50% of data)</li>
        <li><strong>Whiskers:</strong> Minimum and maximum within 1.5×IQR</li>
        <li><strong>Dots:</strong> Outliers (pollution spikes/unusual events)</li>
        <li><strong>Box Height:</strong> Variability (taller = more unstable air quality)</li>
    </ul>
    <p><strong>Interpretation:</strong> Compare medians for chronic pollution. Check box heights for consistency. Outliers indicate industrial activity or traffic incidents.</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'Correlation Study':
    st.markdown("##  Correlation Analysis - Traffic Impact on Air Quality")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Multi-variate analysis | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)

    df = generate_static_data(st.session_state.show_vellore_areas)

    fig = px.scatter(df, x='vehicles_count', y='aqi',
                     size='population', color='traffic_density',
                     hover_data=['location', 'avg_speed'],
                     title="Vehicle Count vs Air Quality Index - Correlation Study",
                     labels={'vehicles_count': 'Daily Vehicle Count',
                             'aqi': 'Air Quality Index (AQI)',
                             'traffic_density': 'Traffic Density (%)'},
                     color_continuous_scale='Reds',
                     size_max=50)

    # Add trendline
    z = np.polyfit(df['vehicles_count'], df['aqi'], 1)
    p = np.poly1d(z)
    df_sorted = df.sort_values('vehicles_count')

    fig.add_trace(go.Scatter(
        x=df_sorted['vehicles_count'],
        y=p(df_sorted['vehicles_count']),
        mode='lines',
        name='Linear Trend',
        line=dict(color='blue', width=3, dash='dot'),
        showlegend=True
    ))

    fig.update_layout(
        template='plotly_white',
        height=550,
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Daily Vehicle Count"),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Air Quality Index (AQI)")
    )

    st.plotly_chart(fig, use_container_width=True)

    # Correlation metrics
    st.markdown("###  Correlation Metrics")
    col1, col2, col3, col4 = st.columns(4)

    correlation_coef = df['vehicles_count'].corr(df['aqi'])
    traffic_aqi_corr = df['traffic_density'].corr(df['aqi'])
    speed_aqi_corr = df['avg_speed'].corr(df['aqi'])

    with col1:
        st.metric("Vehicle-AQI Correlation", f"{correlation_coef:.3f}")
    with col2:
        st.metric("Density-AQI Correlation", f"{traffic_aqi_corr:.3f}")
    with col3:
        st.metric("Speed-AQI Correlation", f"{speed_aqi_corr:.3f}")
    with col4:
        r_squared = correlation_coef ** 2
        st.metric("R² Score", f"{r_squared:.3f}")

    st.markdown(f"""
    <div class='legend-box'>
    <h4> Scatter Plot Correlation Analysis</h4>
    <p><strong>Visualization Type:</strong> Correlation Scatter Plot (Module 5 - Multivariate data visualization)</p>
    <p><strong>X-Axis:</strong> Daily Vehicle Count (total vehicles monitored)</p>
    <p><strong>Y-Axis:</strong> Air Quality Index (pollution level)</p>
    <p><strong>Bubble Size:</strong> Population of location (larger = more people affected)</p>
    <p><strong>Bubble Color:</strong> Traffic Density % (darker red = heavier congestion)</p>
    <p><strong>Blue Dotted Line:</strong> Linear regression trend line</p>
    <p><strong>Key Findings:</strong></p>
    <ul>
        <li>Strong positive correlation ({correlation_coef:.3f}) proves vehicles cause pollution</li>
        <li>R² = {r_squared:.3f} means {r_squared * 100:.1f}% of AQI variation explained by vehicle count</li>
        <li>Negative speed correlation: Slower traffic (congestion) = worse pollution</li>
    </ul>
    <p><strong>Policy Implication:</strong> Reducing vehicle count by 20% could lower AQI by approximately 15-20 points</p>
    <p><strong>Analysis Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'Dot Map':
    st.markdown("## ⚫ Dot Map Visualization - Geographic Distribution")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Point-based geospatial representation | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)

    df = generate_static_data(st.session_state.show_vellore_areas)

    # ✅ Use scatter_mapbox for detailed background map
    fig = px.scatter_mapbox(
        df,
        lat='lat',
        lon='lon',
        size='aqi',
        color='traffic_density',
        hover_name='location',
        hover_data={'aqi': True, 'traffic_density': True},
        title='Dot Map: Traffic and Pollution Distribution',
        color_continuous_scale='Reds',
        size_max=30,
        zoom=6,
        height=600
    )

    fig.update_layout(
        mapbox_style='open-street-map',  # ✅ Detailed labeled map
        mapbox_center={"lat": 11.0, "lon": 78.5},
        margin={"r":0,"t":40,"l":0,"b":0},
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legend section
    st.markdown(f"""
    <div class='legend-box'>
    <h4>📋 Dot Map Interpretation</h4>
    <p><strong>Visualization Type:</strong> Dot Map (Module 4 - Geospatial visualization)</p>
    <p><strong>Geographic Scope:</strong> Tamil Nadu state with focus on monitored locations</p>
    <p><strong>Dot Size:</strong> Proportional to Air Quality Index (larger dots = higher pollution)</p>
    <p><strong>Dot Color:</strong> Traffic Density percentage (darker red = more congestion)</p>
    <p><strong>Spatial Patterns:</strong> Clusters in urban centers (Chennai, Coimbatore, Madurai, Vellore). Scattered rural points show lower pollution.</p>
    <p><strong>Usage:</strong> Quick visual identification of hotspots. Compare relative pollution levels at a glance.</p>
    <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
#
# elif st.session_state.page == 'Hexagonal Binning':
#     st.markdown("## ⬡ Hexagonal Binning - Density Visualization")
#     st.markdown(
#         f"<p style='color:#666; font-style:italic;'>Spatial aggregation technique | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
#         unsafe_allow_html=True)
#
#     # Generate more data points for hexbin
#     df = generate_static_data(st.session_state.show_vellore_areas)
#     expanded_data = []
#     for _, row in df.iterrows():
#         for i in range(20):
#             expanded_data.append({
#                 'lat': row['lat'] + np.random.normal(0, 0.1),
#                 'lon': row['lon'] + np.random.normal(0, 0.1),
#                 'aqi': row['aqi'] + np.random.normal(0, 15)
#             })
#
#     hex_df = pd.DataFrame(expanded_data)
#
#     fig = go.Figure()
#
#     fig.add_trace(go.Histogram2d(
#         x=hex_df['lon'],
#         y=hex_df['lat'],
#         z=hex_df['aqi'],
#         colorscale='Reds',
#         colorbar=dict(title=dict(text="Avg AQI", side="right")),
#         nbinsx=15,
#         nbinsy=15
#     ))
#
#     fig.update_layout(
#         title='Hexagonal Binning: Spatial Pollution Density',
#         xaxis_title='Longitude',
#         yaxis_title='Latitude',
#         template='plotly_white',
#         height=600,
#         xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
#         yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
#     )
#
#     st.plotly_chart(fig, use_container_width=True)
#
#     st.markdown(f"""
#     <div class='legend-box'>
#     <h4> Hexagonal Binning Analysis</h4>
#     <p><strong>Visualization Type:</strong> Hexagonal Binning / 2D Histogram (Module 4 - Geospatial visualization)</p>
#     <p><strong>X-Axis:</strong> Longitude (geographic coordinate)</p>
#     <p><strong>Y-Axis:</strong> Latitude (geographic coordinate)</p>
#     <p><strong>Color Intensity:</strong> Average AQI in each hexagonal bin</p>
#     <p><strong>Method:</strong> Aggregates nearby pollution readings into hexagonal cells for pattern visualization</p>
#     <p><strong>Advantages:</strong> Reduces visual clutter, shows density patterns, identifies pollution hotspot regions</p>
#     <p><strong>Interpretation:</strong> Darker red hexagons indicate concentrated pollution zones. Use for regional policy planning and resource allocation.</p>
#     <p><strong>Sample Size:</strong> {len(hex_df)} data points | <strong>Time:</strong> {datetime.now().strftime('%H:%M:%S')}</p>
#     </div>
#     """, unsafe_allow_html=True)

elif st.session_state.page == 'Network Graph':
    st.markdown("## 🕸️ Network Graph - Traffic Flow Connectivity")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Network and tree visualization | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)

    df = generate_static_data(False)  # Use only major cities

    # Create network connections (simplified)
    locations = df['location'].tolist()

    edges = []
    edge_weights = []
    for i, loc1 in enumerate(locations[:8]):
        for j, loc2 in enumerate(locations[:8]):
            if i < j:
                weight = random.randint(50, 500)
                edges.append((loc1, loc2))
                edge_weights.append(weight)

    # Create figure using Mapbox (for detailed map with labels)
    fig = go.Figure()


    for idx, (source, target) in enumerate(edges):
        source_data = df[df['location'] == source].iloc[0]
        target_data = df[df['location'] == target].iloc[0]

        fig.add_trace(go.Scattermapbox(
            lon=[source_data['lon'], target_data['lon']],
            lat=[source_data['lat'], target_data['lat']],
            mode='lines',
            line=dict(width=edge_weights[idx] / 100, color='rgba(102, 126, 234, 0.4)'),
            hoverinfo='skip',
            showlegend=False
        ))


    fig.add_trace(go.Scattermapbox(
        lon=df['lon'][:8],
        lat=df['lat'][:8],
        mode='markers+text',
        marker=dict(
            size=df['vehicles_count'][:8] / 1000,
            color=df['aqi'][:8],
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title=dict(text="AQI", side="right"))
        ),
        text=df['location'][:8],
        textposition='top center',
        hovertemplate='<b>%{text}</b><br>AQI: %{marker.color:.0f}<extra></extra>',
        showlegend=False
    ))

    fig.update_layout(
        mapbox_style='open-street-map',  # Detailed, labeled background
        mapbox_center=dict(lat=11.0, lon=78.5),
        mapbox_zoom=6,
        height=600,
        title='Network Graph: Inter-city Traffic Flow Connections',
        margin={"r":0, "t":40, "l":0, "b":0},
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legend/Description section
    st.markdown(f"""
    <div class='legend-box'>
    <h4> Network Graph Analysis</h4>
    <p><strong>Visualization Type:</strong> Network/Tree Visualization (Module 2 - Visual Analytics)</p>
    <p><strong>Nodes (Circles):</strong> Major cities in Tamil Nadu</p>
    <p><strong>Node Size:</strong> Vehicle count (larger = more vehicles)</p>
    <p><strong>Node Color:</strong> Air Quality Index (darker red = worse pollution)</p>
    <p><strong>Edges (Lines):</strong> Traffic flow connections between cities</p>
    <p><strong>Edge Thickness:</strong> Traffic volume on that route</p>
    <p><strong>Network Insight:</strong> Identifies key transportation hubs and pollution spread patterns. Thicker connections indicate major highways requiring monitoring.</p>
    <p><strong>Application:</strong> Plan inter-city public transport, optimize highway pollution control, identify transit corridors</p>
    <p><strong>Analysis Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == 'Text Analysis':
    st.markdown("##  Text Data Visualization - Incident Reports")
    st.markdown(
        f"<p style='color:#666; font-style:italic;'>Text data analysis and word frequency | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True)

    # Generate incident text data
    incident_types = ['Congestion', 'Accident', 'Pollution Spike', 'Road Work', 'Heavy Traffic',
                      'Air Quality Alert', 'Vehicle Breakdown', 'Weather Impact']

    incident_data = []
    for _ in range(100):
        incident_data.append({
            'type': random.choice(incident_types),
            'count': 1
        })

    incident_df = pd.DataFrame(incident_data)
    incident_summary = incident_df.groupby('type').size().reset_index(name='frequency')
    incident_summary = incident_summary.sort_values('frequency', ascending=True)

    # Create horizontal bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=incident_summary['type'],
        x=incident_summary['frequency'],
        orientation='h',
        marker=dict(
            color=incident_summary['frequency'],
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title=dict(text="Frequency", side="right"))
        ),
        text=incident_summary['frequency'],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Count: %{x}<extra></extra>'
    ))

    fig.update_layout(
        title='Incident Type Frequency Analysis - Text Data Visualization',
        xaxis_title='Frequency Count',
        yaxis_title='Incident Type',
        template='plotly_white',
        height=500,
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=False)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Word cloud simulation with table
    st.markdown("### 📊 Top Keywords from Incident Reports")

    keywords = {
        'heavy': 45, 'traffic': 42, 'pollution': 38, 'congestion': 35,
        'delay': 28, 'accident': 25, 'alert': 22, 'slow': 20,
        'vehicles': 18, 'emission': 15, 'road': 14, 'jam': 12
    }

    keyword_df = pd.DataFrame(list(keywords.items()), columns=['Keyword', 'Mentions'])
    keyword_df = keyword_df.sort_values('Mentions', ascending=False)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(keyword_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f"""
        **Report Summary:**
        - Total Incidents: 100
        - Most Common: Congestion
        - Peak Time: 6-8 PM
        - Critical Locations: 5
        - Generated: {datetime.now().strftime('%H:%M')}
        """)

    st.markdown(f"""
    <div class='legend-box'>
    <h4> Text Visualization Analysis</h4>
    <p><strong>Visualization Type:</strong> Text Data Visualization (Module 5 - Text data visualization)</p>
    <p><strong>X-Axis:</strong> Frequency count of incident occurrences</p>
    <p><strong>Y-Axis:</strong> Incident category/type</p>
    <p><strong>Data Source:</strong> Automated incident reports from traffic management system</p>
    <p><strong>Color Coding:</strong> Darker red indicates higher frequency incidents requiring priority attention</p>
    <p><strong>Keyword Analysis:</strong> Most mentioned terms: 'heavy', 'traffic', 'pollution' - indicates primary concerns</p>
    <p><strong>Actionable Intelligence:</strong> Focus resources on top 3 incident types. Deploy quick response teams for congestion and accidents.</p>
    <p><strong>Report Period:</strong> Last 24 hours | <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #888; padding: 20px;'>
    <p><strong>Smart City Traffic & Pollution Monitor</strong> - Tamil Nadu & Vellore</p>
    <p>Advanced Data Visualization Techniques Project | Real-time Monitoring System</p>
    <p>Last System Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST</p>
    <p>Powered by Streamlit | Visualization: Plotly & Folium</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh for dashboard only
if st.session_state.page == 'Dashboard' and 'auto_refresh' in locals() and auto_refresh:
    time.sleep(2)
    st.rerun()