from dotenv import load_dotenv
import os

dotenv_path = '.env'
load_dotenv(dotenv_path)

print("DATABASE_URL:", os.getenv('DATABASE_URL'))
