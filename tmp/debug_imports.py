try:
    print("Importing app.main...")
    import app.main
    print("Success importing app.main!")
except Exception as e:
    import traceback
    print("Failed importing app.main:")
    traceback.print_exc()

try:
    print("\nImporting app.api.routes...")
    import app.api.routes
    print("Success importing app.api.routes!")
except Exception as e:
    import traceback
    print("Failed importing app.api.routes:")
    traceback.print_exc()
