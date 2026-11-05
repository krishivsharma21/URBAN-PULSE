import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from geopy.distance import geodesic

# Configure application logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("URBAN_PULSE_BACKEND")

app = Flask(__name__)
CORS(app)

# Configuration constants
HOSPITALS_FILE = os.path.join(os.path.dirname(__file__), 'hospitals.json')
SYSTEM_VERSION = "2.5.0-PROD"

def load_hospitals():
    """
    Safely loads the hospitals registry JSON file from disk (supporting large datasets).
    Returns an empty list if the file is missing or corrupted.
    """
    if os.path.exists(HOSPITALS_FILE):
        try:
            with open(HOSPITALS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Successfully loaded {len(data)} medical assets from registry.")
                return data
        except json.JSONDecodeError as jde:
            logger.error(f"JSON Decode Error while parsing hospitals.json: {jde}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading hospitals file: {e}")
            return []
    logger.warning(f"Hospitals file not found at path: {HOSPITALS_FILE}")
    return []

# ==========================================
# CORE VIEW ROUTES
# ==========================================

@app.route('/')
def home():
    """
    Renders the primary URBAN PULSE command dashboard template.
    """
    logger.info("Serving main dashboard interface.")
    return render_template('index.html', app_name="URBAN PULSE", version=SYSTEM_VERSION)

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Render/Container monitors.
    """
    return jsonify({
        "status": "healthy",
        "system": "URBAN PULSE Emergency Engine",
        "timestamp": datetime.utcnow().isoformat(),
        "version": SYSTEM_VERSION
    }), 200

# ==========================================
# HOSPITAL REGISTRY API ROUTES
# ==========================================

@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """
    Retrieves the complete list of registered hospitals in the network.
    """
    hospitals = load_hospitals()
    return jsonify({
        "status": "success",
        "system": "URBAN PULSE Emergency Network",
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(hospitals),
        "data": hospitals
    }), 200

# ==========================================
# EMERGENCY ROUTING & GEOSPATIAL API ROUTES
# ==========================================

@app.route('/api/nearest', methods=['POST'])
def find_nearest_hospitals():
    """
    Calculates geographical distances using geodesic algorithms from user coordinates 
    to all registered medical assets, supporting flexible coordinate schema keys.
    """
    req_data = request.get_json() or {}
    user_lat = req_data.get('latitude')
    user_lon = req_data.get('longitude')
    max_results = int(req_data.get('limit', 5))
    
    if user_lat is None or user_lon is None:
        logger.warning("Routing request rejected: Latitude and Longitude are required.")
        return jsonify({
            "status": "error",
            "message": "Latitude and longitude parameters are required."
        }), 400
        
    try:
        user_location = (float(user_lat), float(user_lon))
    except (ValueError, TypeError) as err:
        logger.error(f"Coordinate parsing error: {err}")
        return jsonify({
            "status": "error",
            "message": "Invalid coordinate format. Must be floating-point values."
        }), 400
        
    hospitals = load_hospitals()
    if not hospitals:
        return jsonify({
            "status": "success",
            "system": "URBAN PULSE Routing Engine",
            "count": 0,
            "nearest": []
        }), 200
        
    scored_hospitals = []
    for h in hospitals:
        try:
            # Support multiple key name conventions for massive datasets (e.g., latitude, lat, Y)
            h_lat = float(h.get('latitude') or h.get('lat') or h.get('Y') or 0)
            h_lon = float(h.get('longitude') or h.get('lon') or h.get('X') or 0)
            
            if h_lat == 0 or h_lon == 0:
                continue
                
            hospital_coords = (h_lat, h_lon)
            
            # Calculate precise geodesic distance in kilometers
            distance_km = geodesic(user_location, hospital_coords).kilometers
            
            h_copy = dict(h)
            h_copy['latitude'] = h_lat
            h_copy['longitude'] = h_lon
            h_copy['distance_km'] = round(distance_km, 2)
            h_copy['estimated_eta_mins'] = round((distance_km / 40.0) * 60, 1) # Assumes average 40 km/h transit
            scored_hospitals.append(h_copy)
        except Exception:
            continue
            
    # Sort assets by distance ascending (closest first)
    scored_hospitals.sort(key=lambda x: x['distance_km'])
    
    logger.info(f"Routed dispatch from user coordinate {user_location}. Processed {len(hospitals)} assets, found {len(scored_hospitals)} eligible units.")
    
    return jsonify({
        "status": "success",
        "system": "URBAN PULSE Routing Engine",
        "timestamp": datetime.utcnow().isoformat(),
        "query_coordinates": {"latitude": user_lat, "longitude": user_lon},
        "count": len(scored_hospitals[:max_results]),
        "nearest": scored_hospitals[:max_results]
    }), 200

# ==========================================
# APPLICATION ENTRYPOINT
# ==========================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting URBAN PULSE production server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)