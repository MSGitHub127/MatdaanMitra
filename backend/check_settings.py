import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings

print("Settings loaded successfully!")
print(f"Environment: {settings.environment}")
print(f"Is Dev: {settings.is_dev}")
print(f"GCP Project ID: {settings.gcp_project_id}")
print(f"Frontend URL: {settings.frontend_url}")

# Check API availability
print("\nAPI Availability:")
for api in ["maps", "translate", "vertex", "firebase", "document_ai"]:
    available = settings.check_api_available(api)
    print(f"  {api}: {'Available' if available else 'Not configured (dummy)'}")
