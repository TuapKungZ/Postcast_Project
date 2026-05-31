import streamlit as st
import os
import asyncio
import edge_tts
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, afx

# --- 1. ตั้งค่าระบบ ---
load_dotenv()
st.set_page_config(page_title="ReadCast Pro: Polyglot", page_icon="🌍", layout="wide")

# ซ่อน Deploy, เมนู 3 จุด, และ footer
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
</style>
""", unsafe_allow_html=True)

# --- 2. ระบบความจำ (Session State) ---
# ต้องประกาศค่าเริ่มต้นกันลืม ก่อนเริ่มทำงาน
if "script" not in st.session_state: st.session_state.script = ""
if "fetched_content" not in st.session_state: st.session_state.fetched_content = ""
if "mode" not in st.session_state: st.session_state.mode = "Normal"

# --- 3. ฟังก์ชันต่างๆ (Backend Logic) ---

def get_text_from_url(url):
    """ดึงข้อความจากลิงก์ข่าว"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text if len(text) > 100 else None
    except Exception as e:
        print(f"Error scraping: {e}")
        return None

def parse_script(text):
    """แยกบทพูดว่าใครพูดประโยคไหน"""
    lines = text.split('\n')
    dialogues = []
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            speaker_label = parts[0].lower()
            
            # แปลงชื่อในบท เป็นรหัสตัวละคร
            if "host a" in speaker_label: speaker = "host_a"
            elif "host b" in speaker_label: speaker = "host_b"
            else: continue
            
            dialogues.append((speaker, parts[1].strip()))
    return dialogues

async def generate_audio_files(dialogues, mode):
    """สร้างไฟล์เสียงทีละท่อน (Async)"""
    files = []
    progress_bar = st.progress(0, text="🎙️ กำลังเริ่มอัดเสียง...")
    total = len(dialogues)
    
    for i, (speaker, text) in enumerate(dialogues):
        filename = f"temp_{i}_{speaker}.mp3"
        
        # --- 🎯 Logic เลือกเสียงตามโหมด ---
        if "English Tutor" in mode:
            # โหมดฝึกภาษา: A=ฝรั่ง, B=ไทย
            if speaker == "host_a":
                voice = "en-US-ChristopherNeural" # เสียงฝรั่งผู้ชาย
            else:
                voice = "th-TH-PremwadeeNeural"   # เสียงไทยผู้หญิง
        else:
            # โหมดข่าวปกติ: ไทยล้วน
            voice = "th-TH-NiwatNeural" if speaker == "host_a" else "th-TH-PremwadeeNeural"
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
            files.append(filename)
        except Exception as e:
            print(f"Error TTS: {e}")
            
        progress_bar.progress((i + 1) / total, text=f"🎙️ อัดท่อนที่ {i+1}/{total}")
    
    progress_bar.empty()
    return files

def mix_audio(voice_files):
    """ตัดต่อเสียงพูดรวมกับเพลง"""
    try:
        # 1. รวมเสียงพูด
        voice_clips = [AudioFileClip(f) for f in voice_files]
        final_voice = concatenate_audioclips(voice_clips)
        
        # 2. ใส่เพลง (ถ้ามีไฟล์ music.mp3)
        if os.path.exists("music.mp3"):
            bgm = AudioFileClip("music.mp3")
            # วนลูปเพลงให้ยาวเท่าเสียงพูด
            bgm = afx.audio_loop(bgm, duration=final_voice.duration)
            # ลดเสียงเพลงเหลือ 12%
            bgm = bgm.volumex(0.12)
            # ผสมรวมกัน
            final_audio = CompositeAudioClip([final_voice, bgm])
        else:
            final_audio = final_voice

        # 3. บันทึกไฟล์
        final_audio.write_audiofile("final_podcast.mp3", fps=44100, verbose=False, logger=None)
        
        # 4. ลบไฟล์ขยะ (Cleanup)
        final_voice.close()
        if os.path.exists("music.mp3"): bgm.close()
        for c in voice_clips: c.close()
        for f in voice_files: 
            try: os.remove(f)
            except: pass
        return True
    except Exception as e:
        st.error(f"Error Mixing: {e}")
        return False

# --- 4. ส่วนหน้าจอ (UI Layout) ---

st.title("🌍 ReadCast: The Global Translator")

# Sidebar: ตั้งค่า
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key (ปลอดภัย)
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key: 
        st.success("✅ เชื่อมต่อ API Key แล้ว")
    else:
        api_key = st.text_input("🔑 ใส่ Google API Key", type="password")
        if not api_key:
            st.warning("กรุณาใส่ API Key ก่อนใช้งาน")
            st.stop()

    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

    st.divider()
    
    # เลือกโหมด
    st.subheader("เลือกรูปแบบรายการ")
    mode_choice = st.radio(
        "Mode:",
        ["🇹🇭 Podcast ทั่วไป (สรุปข่าว)", "🇬🇧 ฝึกภาษา (English Tutor)"],
        captions=["คุยภาษาไทย 100%", "Host A พูดอังกฤษ / Host B แปลไทย"]
    )
    st.session_state.mode = mode_choice

# Main Content แบ่ง 2 คอลัมน์
col1, col2 = st.columns([1, 1])

# --- คอลัมน์ซ้าย: ใส่ข้อมูล ---
with col1:
    st.subheader("1. ใส่เนื้อหา (English Source)")
    
    tab1, tab2 = st.tabs(["🔗 Link (BBC/CNN)", "📝 Text"])
    
    with tab1:
        url = st.text_input("URL ข่าวภาษาอังกฤษ")
        # ปุ่มดึงข้อมูล
        if url and st.button("ดึงข้อมูล"):
            with st.spinner("🕷️ กำลังดูดเนื้อหา..."):
                fetched = get_text_from_url(url)
                if fetched:
                    st.session_state.fetched_content = fetched
                    st.success(f"ดึงข้อมูลเสร็จ! ({len(fetched)} ตัวอักษร)")
                else:
                    st.error("ดึงข้อมูลไม่ได้ (เว็บอาจบล็อก)")
        
        # แสดงสถานะว่ามีข้อมูลในความจำไหม
        if st.session_state.fetched_content:
            st.info("✅ มีเนื้อหาข่าวในระบบแล้ว (กด 'เขียนบท' ได้เลย)")

    with tab2:
        manual_text = st.text_area("วางบทความเอง", height=150)

    # ปุ่มสั่ง AI เขียนบท
    if st.button("✨ เขียนบท (Draft Script)", type="primary"):
        # เช็คข้อมูลจากความจำ หรือ ช่องกรอกเอง
        final_content = st.session_state.fetched_content if st.session_state.fetched_content else manual_text
        
        if not final_content:
            st.warning("⚠️ ยังไม่มีเนื้อหาครับ ให้ใส่ Link หรือข้อความก่อน")
        else:
            with st.spinner("🤖 AI กำลังเขียนบท..."):
                # เลือก Prompt ตามโหมด
                if "English Tutor" in st.session_state.mode:
                    prompt = f"""
                    คุณคือครูสอนภาษาอังกฤษ จัดรายการ Podcast คู่กับนักเรียนไทย
                    บทบาท:
                    - Host A (Teacher): คัดเลือกประโยคภาษาอังกฤษจากข่าวมาพูด (ทีละประโยคสั้นๆ) เน้นเสียง Native
                    - Host B (Student): แปลไทย อธิบายศัพท์ยาก หรือสรุปใจความสำคัญ
                    รูปแบบเป๊ะๆ:
                    Host A: [English Sentence]
                    Host B: [Thai Translation/Explanation]
                    (สลับกันไปเรื่อยๆ จนจบเนื้อหาสำคัญ)
                    เนื้อหาต้นฉบับ: {final_content[:4500]}
                    """
                else:
                    prompt = f"""
                    สรุปบทความนี้เป็น Podcast ภาษาไทยสนุกๆ
                    Host A (ชาย), Host B (หญิง)
                    รูปแบบเป๊ะๆ:
                    Host A: ข้อความ
                    Host B: ข้อความ
                    ห้ามใส่ตัวหนา ** ในชื่อคน
                    เนื้อหา: {final_content[:4500]}
                    """
                
                try:
                    response = model.generate_content(prompt)
                    st.session_state.script = response.text
                    st.rerun() # รีเฟรชหน้าจอเพื่อโชว์บทในคอลัมน์ขวา
                except Exception as e:
                    st.error(f"AI Error: {e}")

# --- คอลัมน์ขวา: แก้ไขและผลิต ---
with col2:
    st.subheader("2. ตรวจสอบบท & ผลิตเสียง")
    
    if st.session_state.script:
        # ช่องแก้ไขบท
        edited_script = st.text_area("แก้ไขบทพูดได้ที่นี่:", value=st.session_state.script, height=450)
        st.session_state.script = edited_script
        
        st.write(f"โหมดปัจจุบัน: **{st.session_state.mode}**")

        # ปุ่มผลิตเสียง
        if st.button("🎧 ผลิตรายการ (Generate Audio)", type="primary"):
            dialogues = parse_script(st.session_state.script)
            
            if dialogues:
                # ส่งโหมดไปให้ฟังก์ชันเลือกเสียง
                voice_files = asyncio.run(generate_audio_files(dialogues, st.session_state.mode))
                
                with st.spinner("🎵 กำลังมิกซ์เสียงและใส่ดนตรี..."):
                    if mix_audio(voice_files):
                        st.success("🎉 เสร็จสมบูรณ์!")
                        st.balloons()
                        
                        # เครื่องเล่น
                        st.audio("final_podcast.mp3")
                        
                        # ปุ่มโหลด
                        with open("final_podcast.mp3", "rb") as f:
                            st.download_button("📥 ดาวน์โหลด MP3", f, "readcast_tutor.mp3")
            else:
                st.error("❌ รูปแบบบทไม่ถูกต้อง (ต้องมี Host A: / Host B:)")
    else:
        st.info("👈 รอข้อมูลจากขั้นตอนที่ 1")