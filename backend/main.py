import sys

project_path = '/home/dant1one/Chat/backend'
if project_path not in sys.path:
    sys.path.append(project_path)

from app.main import app as application