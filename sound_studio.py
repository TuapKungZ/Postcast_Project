import asyncio
import edge_tts

# ฟังก์ชันสร้างเสียง
async def generate_voice(text, filename, gender):
    # เลือกเสียง: ผู้ชาย (Niwat) / ผู้หญิง (Premwadee)
    if gender == "male":
        voice = "th-TH-NiwatNeural"
    else:
        voice = "th-TH-PremwadeeNeural"
        
    print(f"🎙️ กำลังอัดเสียง ({gender}): {text[:20]}...")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)
    print(f"✅ บันทึกไฟล์: {filename} เรียบร้อย!")

# ทดสอบระบบ
async def main():
    print("--- 🎧 เริ่มทดสอบระบบเสียง ---")
    
    # ลองให้ Host A (ต้น) พูด
    await generate_voice("สวัสดีครับ ผมชื่อต้น ยินดีที่ได้รู้จักครับ", "voice_ton.mp3", "male")
    
    # ลองให้ Host B (ตาล) พูด
    await generate_voice("สวัสดีค่ะ ตาลเองค่ะ เสียงชัดไหมคะ?", "voice_tarn.mp3", "female")

if __name__ == "__main__":
    asyncio.run(main())