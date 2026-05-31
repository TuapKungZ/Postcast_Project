import os
import asyncio
import edge_tts
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from moviepy.editor import AudioFileClip, concatenate_audioclips

# --- 1. ตั้งค่าระบบ ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# --- 2. ฟังก์ชันดูดเนื้อหาจากเว็บ (Web Scraper) ---
def get_text_from_url(url):
    print(f"🌐 กำลังเชื่อมต่อกับเว็บ: {url} ...")
    try:
        # แอบปลอมตัวเป็นคน (ไม่ใช่บอท)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ดึงเฉพาะข้อความในแท็ก <p> (ย่อหน้า)
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        
        if len(text) < 100:
            return None # เนื้อหาน้อยเกินไป น่าจะดึงผิด
            
        return text
    except Exception as e:
        print(f"❌ ดึงข้อมูลไม่ได้: {e}")
        return None

# --- 3. สร้าง AI Writer ---
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction="""
    คุณคือ Pro Podcast Scriptwriter.
    หน้าที่: สรุปบทความให้เป็นบทสนทนา Podcast (Host A และ Host B).
    - ห้ามใช้ Markdown ตัวหนาในชื่อคนพูด (ห้ามใช้ **Host A**)
    - รูปแบบ:
    Host A: ...
    Host B: ...
    """
)

# --- 4. แยกบท (Parser) ---
def parse_script(text):
    lines = text.split('\n')
    dialogues = []
    for line in lines:
        line = line.replace("**", "").strip()
        if ":" in line and ("Host A" in line or "Host B" in line):
            parts = line.split(":", 1)
            speaker = "male" if "Host A" in parts[0] else "female"
            dialogues.append((speaker, parts[1].strip()))
    return dialogues

# --- 5. สร้างเสียง (Voice) ---
async def generate_audio_files(dialogues):
    print("\n--- 🎙️ เริ่มอัดเสียง... ---")
    files = []
    for i, (speaker, text) in enumerate(dialogues):
        filename = f"temp_{i}_{speaker}.mp3"
        voice = "th-TH-NiwatNeural" if speaker == "male" else "th-TH-PremwadeeNeural"
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
            files.append(filename)
            print(f"✅ ท่อนที่ {i+1} เรียบร้อย")
        except: pass
    return files

# --- 6. ตัดต่อ (Editor) ---
def combine_audio(files, output_file="final_podcast.mp3"):
    print(f"\n--- ✂️ กำลังตัดต่อ... ---")
    try:
        clips = [AudioFileClip(f) for f in files]
        final_clip = concatenate_audioclips(clips)
        final_clip.write_audiofile(output_file, verbose=False, logger=None)
        for c in clips: c.close()
        for f in files: os.remove(f)
        print("🧹 เก็บกวาดเรียบร้อย")
    except Exception as e: print(f"❌ ตัดต่อพลาด: {e}")

# --- 7. Main Workflow ---
async def main():
    print("\n🎧 --- ReadCast Ultimate Edition --- 🎧")
    choice = input("เลือกแหล่งข้อมูล (1=ไฟล์ source.txt, 2=ลิงก์เว็บ): ")
    
    content = ""
    
    if choice == "1":
        # อ่านจากไฟล์
        try:
            with open("source.txt", "r", encoding="utf-8") as f:
                content = f.read()
        except:
            print("❌ หาไฟล์ source.txt ไม่เจอ")
            return
            
    elif choice == "2":
        # อ่านจากลิงก์
        url = input("แปะลิงก์บทความที่นี่: ")
        content = get_text_from_url(url)
        if not content:
            print("❌ ไม่สามารถดึงเนื้อหาจากลิงก์นี้ได้ (เว็บอาจจะบล็อกบอท)")
            return
    else:
        print("❌ เลือกผิดครับ")
        return

    print(f"✅ ได้เนื้อหามาแล้ว ({len(content)} ตัวอักษร)")
    content = content[:6000] # ตัดไม่ให้ยาวเกิน

    # --- เริ่มกระบวนการ ---
    print("📝 AI กำลังเขียนบท...")
    prompt = f"สรุปบทความนี้เป็น Podcast สนุกๆ (ห้ามใส่ตัวหนาที่ชื่อคน):\n\n{content}"
    response = model.generate_content(prompt)
    script = response.text
    
    dialogues = parse_script(script)
    if dialogues:
        audio_files = await generate_audio_files(dialogues)
        combine_audio(audio_files)
        print(f"\n🎉🎉🎉 เสร็จสมบูรณ์! ไฟล์อยู่ที่ 'final_podcast.mp3'")
        
        # (แถม) ลองเล่นไฟล์เสียงเลย (เฉพาะ Windows)
        os.system("start final_podcast.mp3")
    else:
        print("❌ AI เขียนบทออกมาผิดฟอร์แมต")

if __name__ == "__main__":
    asyncio.run(main())