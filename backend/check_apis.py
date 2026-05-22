import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'src')

# Force reload settings after .env change
import importlib
import src.config.settings as s_module
importlib.invalidate_caches()

from src.config.settings import Settings
fresh = Settings()

apis = ["maps", "translate", "vertex", "firebase", "document_ai"]
all_ok = True
for api in apis:
    available = fresh.check_api_available(api)
    status = "OK" if available else "STILL DUMMY"
    print(f"  {api}: {status}")
    if not available:
        all_ok = False

print()
print("All APIs configured:", all_ok)
