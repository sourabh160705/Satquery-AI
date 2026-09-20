import sys
sys.path.insert(0, 'D:/Satquery-AI/backend')
from engine.location_satellite import LocationSatelliteFetcher

indore = LocationSatelliteFetcher.fetch_scene_for_location(22.7196, 75.8577, "Indore, India")
print("Indore:", indore["metadata"]["filename"], indore["metadata"]["width"], "preview len:", len(indore["preview_base64"]))

bhopal = LocationSatelliteFetcher.fetch_scene_for_location(23.2599, 77.4126, "Bhopal, India")
print("Bhopal:", bhopal["metadata"]["filename"], bhopal["metadata"]["width"], "preview len:", len(bhopal["preview_base64"]))
