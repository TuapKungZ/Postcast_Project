import streamlit as st
import os
import asyncio
import edge_tts
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, afx

# --- 1. Config ---
load_dotenv()
st.set_page_config(page_title="ReadCast Pro: Polyglot", page_icon="🌍", layout="wide")

# --- 2. Initialize Session State ---
if "script" not in st.session_state: st.session_state.script = ""
if "step" not in st.session_state: st.session_state.step = 1
if "mode" not in st.session_state: st.session_state.mode = "Normal" # เก็บโหมดที่เลือก

# --- 3. Functions ---
def get_text_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text if len(text) > 100 else None
    except: return None

def parse_script(text):
    lines = text.split('\n')
    dialogues = []
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            speaker_label = parts[0].lower()
            
            # แยกฝั่งชาย/หญิง
            if "host a" in speaker_label: speaker = "host_a"
            elif "host b" in speaker_label: speaker = "host_b"
            else: continue
            
            dialogues.append((speaker, parts[1].strip()))
    return dialogues

async def generate_audio_files(dialogues, mode):
    files = []
    progress_bar = st.progress(0, text="🎙️ กำลังเริ่มอัดเสียง...")
    total = len(dialogues)
    
    for i, (speaker, text) in enumerate(dialogues):
        filename = f"temp_{i}_{speaker}.mp3"
        
        # --- 🎯 Logic เลือกเสียงตามโหมด ---
        if mode == "🇬🇧 ฝึกภาษา (English Tutor)":
            if speaker == "host_a":
                # Host A เป็นครูฝรั่ง (เสียงผู้ชาย US)
                voice = "en-US-ChristopherNeural" 
            else:
                # Host B เป็นนักเรียนไทย (เสียงผู้หญิง TH)
                voice = "th-TH-PremwadeeNeural"
        else:
            # โหมดปกติ (ไทยล้วน)
            voice = "th-TH-NiwatNeural" if speaker == "host_a" else "th-TH-PremwadeeNeural"
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
            files.append(filename)
        except: pass
        progress_bar.progress((i + 1) / total, text=f"🎙️ อัดท่อนที่ {i+1}/{total}")
    
    progress_bar.empty()
    return files

def mix_audio(voice_files):
    try:
        voice_clips = [AudioFileClip(f) for f in voice_files]
        final_voice = concatenate_audioclips(voice_clips)
        
        if os.path.exists("music.mp3"):
            bgm = AudioFileClip("music.mp3")
            bgm = afx.audio_loop(bgm, duration=final_voice.duration).volumex(0.12)
            final_audio = CompositeAudioClip([final_voice, bgm])
        else:
            final_audio = final_voice

        final_audio.write_audiofile("final_podcast.mp3", fps=44100, verbose=False, logger=None)
        
        final_voice.close()
        if os.path.exists("music.mp3"): bgm.close()
        for c in voice_clips: c.close()
        for f in voice_files: os.remove(f)
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- 4. UI Layout ---
st.title("🌍 ReadCast: The Global Translator")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key Handling
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key: st.success("✅ เชื่อมต่อ API Key แล้ว")
    else:
        api_key = st.text_input("🔑 ใส่ Google API Key", type="password")
        if not api_key: st.stop()

    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

    # --- 🎛️ ตัวเลือกโหมดใหม่ ---
    st.subheader("เลือกรูปแบบรายการ")
    mode = st.radio(
        "Mode:",
        ["🇹🇭 Podcast ทั่วไป (สรุปข่าว)", "🇬🇧 ฝึกภาษา (English Tutor)"],
        captions=["คุยภาษาไทย 100%", "Host A พูดอังกฤษ / Host B แปลไทย"]
    )
    st.session_state.mode = mode

# Main Content
col1, col2 = st.columns([1, 1])

# Step 1: Input
with col1:
    st.subheader("1. ใส่เนื้อหา (English Source)")
    
    # --- เพิ่ม: สร้างตัวแปรความจำ ถ้ายังไม่มี ---
    if "fetched_content" not in st.session_state:
        st.session_state.fetched_content = ""

    tab1, tab2 = st.tabs(["🔗 Link (BBC/CNN)", "📝 Text"])
    
    with tab1:
        url = st.text_input("URL ข่าวภาษาอังกฤษ")
        if url and st.button("ดึงข้อมูล"):
            with st.spinner("Loading..."):
                text = get_text_from_url(url)
                if text: 
                    # --- แก้: บันทึกลงความจำระยะยาว ---
                    st.session_state.fetched_content = text
                    st.success(f"ดึงข้อมูลเสร็จ! ({len(text)} ตัวอักษร)")
                else:
                    st.error("ดึงข้อมูลไม่ได้ (เว็บอาจบล็อก)")
                    
        # โชว์ให้เห็นหน่อยว่ามีข้อมูลค้างอยู่ไหม
        if st.session_state.fetched_content:
            st.info("✅ มีเนื้อหาข่าวในระบบแล้ว พร้อมเขียนบท")

    with tab2:
        manual_text = st.text_area("วางบทความภาษาอังกฤษ", height=150)

    if st.button("✨ เขียนบท (Draft Script)", type="primary"):
        # --- แก้: เช็คจากความจำระยะยาว แทนตัวแปรชั่วคราว ---
        final_content = st.session_state.fetched_content if st.session_state.fetched_content else manual_text
        
        if not final_content:
            st.warning("ใส่เนื้อหาก่อนครับ")
        else:
            with st.spinner("AI กำลังออกแบบบทเรียน..."):
                
                # --- 🧠 Prompt แยกตามโหมด ---
                if st.session_state.mode == "🇬🇧 ฝึกภาษา (English Tutor)":
                    prompt = f"""
                    คุณคือครูสอนภาษาอังกฤษ จัดรายการ Podcast คู่กับนักเรียนไทย
                    
                    บทบาท:
                    - Host A (Teacher): พูดประโยคภาษาอังกฤษจากเนื้อหาข่าว (ทีละประโยคสั้นๆ) เน้นเสียง Native
                    - Host B (Student): แปลไทย อธิบายศัพท์ยาก หรือสรุปใจความสำคัญแบบเป็นกันเอง
                    
                    รูปแบบ (Strict Format):
                    Host A: [English Sentence]
                    Host B: [Thai Translation/Explanation]
                    (สลับกันไปเรื่อยๆ จนจบเนื้อหาสำคัญ)
                    
                    เนื้อหาต้นฉบับ:
                    {final_content[:4000]}
                    """
                else:
                    prompt = f"""
                    สรุปบทความนี้เป็น Podcast ภาษาไทยสนุกๆ
                    Host A (ชาย), Host B (หญิง)
                    รูปแบบ: "Host A: ข้อความ", "Host B: ข้อความ"
                    เนื้อหา: {final_content[:4000]}
                    """
                
                res = model.generate_content(prompt)
                st.session_state.script = res.text
                st.session_state.step = 2
                st.rerun()

# Step 2: Edit & Produce
with col2:
    st.subheader("2. ตรวจสอบบท & ผลิตเสียง")
    
    if st.session_state.script:
        edited_script = st.text_area("แก้ไขบทพูด:", value=st.session_state.script, height=400)
        st.session_state.script = edited_script
        
        st.info(f"Mode: {st.session_state.mode}")

        if st.button("🎧 ผลิตรายการ (Generate Audio)", type="primary"):
            dialogues = parse_script(st.session_state.script)
            if dialogues:
                # ส่ง mode ไปด้วย เพื่อเลือกเสียงให้ถูก
                voice_files = asyncio.run(generate_audio_files(dialogues, st.session_state.mode))
                
                with st.spinner("🎵 กำลังมิกซ์เสียง..."):
                    if mix_audio(voice_files):
                        st.success("เสร็จสมบูรณ์!")
                        st.audio("final_podcast.mp3")
                        with open("final_podcast.mp3", "rb") as f:
                            st.download_button("ดาวน์โหลด MP3", f, "tutor_podcast.mp3")
            else:
                st.error("รูปแบบบทไม่ถูกต้อง")
    else:
        st.info("👈 รอข้อมูลจากขั้นตอนที่ 1")