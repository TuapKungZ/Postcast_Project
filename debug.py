import sys
import os

print("--- 1. ใครเป็นคนรัน? (Python Executable) ---")
print(sys.executable)

print("\n--- 2. ตอนนี้อยู่ที่ไหน? (Current Directory) ---")
print(os.getcwd())
print("ไฟล์ในห้องนี้มี:", os.listdir())

print("\n--- 3. เส้นทางค้นหาของ Python (sys.path) ---")
for p in sys.path:
    print(p)

print("\n--- 4. ลองเรียก Google ดูซิ ---")
try:
    import google
    print(f"✅ เจอโฟลเดอร์ google ที่: {google.__path__}")
except ImportError as e:
    print(f"❌ ไม่เจอ google เลย: {e}")

try:
    import google.generative_ai
    print("✅ เจอ google.generative_ai สำเร็จ!")
except ImportError as e:
    print(f"❌ เจอ google แต่ไม่เจอ generative_ai: {e}")