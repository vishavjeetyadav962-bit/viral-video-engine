import os
import uuid
import requests
import asyncio
import edge_tts
from google import genai
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

# Secrets मधून Keys घेणे
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

def download_pixabay_videos(query, target_count=3):
    """ Pixabay वरून HD व्हिडिओ क्लिप्स डाऊनलोड करणे """
    if not PIXABAY_API_KEY:
        print("Pixabay API Key सापडली नाही!")
        return []
    
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={query}&video_type=film&per_page=10"
    try:
        res = requests.get(url, timeout=15)
        downloaded_files = []
        
        if res.status_code == 200:
            hits = res.json().get("hits", [])
            count = 0
            for hit in hits:
                videos = hit.get("videos", {})
                video_url = (videos.get("medium", {}).get("url") or 
                             videos.get("small", {}).get("url") or 
                             videos.get("large", {}).get("url"))
                if video_url:
                    v_res = requests.get(video_url, timeout=30)
                    file_name = f"clip_{uuid.uuid4().hex[:6]}.mp4"
                    with open(file_name, "wb") as f:
                        f.write(v_res.content)
                    downloaded_files.append(file_name)
                    count += 1
                    if count >= target_count:
                        break
        return downloaded_files
    except Exception as e:
        print(f"Pixabay download error: {e}")
        return []

async def generate_assets(topic="Future of Artificial Intelligence"):
    """ Gemini API dware script ani edge-tts dware voiceover banavane """
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = (
        f"Create a 30-second highly viral YouTube Shorts script about: {topic}.\n"
        "Target Audience: United States (High CPM).\n"
        "Language: Native Fluent English.\n"
        "Format output ONLY as plain text narration script suitable for direct voiceover.\n"
        "Do NOT include any sound effects, labels, or stage directions like [Music], [Narrator], etc."
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    script_text = response.text.strip()
    print("--- Generated Script ---")
    print(script_text)
    
    audio_path = "voice.mp3"
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save(audio_path)
    
    return script_text, audio_path

def render_final_video(audio_path, video_files, output_path="final_short.mp4"):
    """ क्लिप्स आणि ऑडिओ एकत्र करून ९:१६ व्हर्टिकल व्हिडिओ तयार करणे """
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    
    clips = []
    for vf in video_files:
        try:
            clip = VideoFileClip(vf).without_audio()
            # 9:16 Shorts फॉरमॅटसाठी आकार (1080x1920)
            clip = clip.resize(height=1920)
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w / 2, width=1080)
            clips.append(clip)
        except Exception as e:
            print(f"Video clip processing error ({vf}): {e}")
            
    if not clips:
        print("एकही क्लिप रेंडरिंगसाठी तयार नाही!")
        return None
        
    final_clip = concatenate_videoclips(clips, method="compose")
    
    # ऑडिओच्या लांबीनुसार व्हिडिओ लूप करणे किंवा कट करणे
    if final_clip.duration < audio_duration:
        final_clip = final_clip.loop(duration=audio_duration)
    else:
        final_clip = final_clip.subclip(0, audio_duration)
        
    final_clip = final_clip.set_audio(audio_clip)
    final_clip.write_videofile(
        output_path, 
        fps=30, 
        codec="libx264", 
        audio_codec="aac", 
        preset="ultrafast"
    )
    print(f"व्हिडिओ यशस्वीरीत्या रेंडर झाला: {output_path}")
    return output_path

if __name__ == "__main__":
    topic = "Secret Space Technologies"
    print("१. स्क्रिप्ट आणि व्हॉईस बनवत आहे...")
    script, audio = asyncio.run(generate_assets(topic))
    
    print("२. Pixabay वरून क्लिप्स डाऊनलोड करत आहे...")
    clips = download_pixabay_videos(topic, target_count=4)
    
    print("३. फायनल व्हिडिओ रेंडर करत आहे...")
    render_final_video(audio, clips, "viral_short.mp4")
