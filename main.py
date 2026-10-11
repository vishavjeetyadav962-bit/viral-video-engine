import os
import uuid
import requests
import asyncio
import edge_tts
from google import genai
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

def download_pixabay_videos(query, target_count=3):
    if not PIXABAY_API_KEY:
        print("Pixabay Key missing!")
        return []
    
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={query}&video_type=film&per_page=10"
    res = requests.get(url)
    downloaded_files = []
    
    if res.status_code == 200:
        hits = res.json().get("hits", [])
        count = 0
        for hit in hits:
            videos = hit.get("videos", {})
            video_url = videos.get("medium", {}).get("url") or videos.get("small", {}).get("url")
            if video_url:
                v_res = requests.get(video_url)
                file_name = f"clip_{uuid.uuid4().hex[:6]}.mp4"
                with open(file_name, "wb") as f:
                    f.write(v_res.content)
                downloaded_files.append(file_name)
                count += 1
                if count >= target_count:
                    break
    return downloaded_files

async def generate_assets(topic="Future of AI"):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Create a 30-second highly viral YouTube Shorts script about: {topic}.
    Target Audience: United States (High CPM).
    Language: Native Fluent English.
    Format output ONLY as plain text narration script suitable for direct voiceover.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    script_text = response.text.strip()
    
    audio_path = "voice.mp3"
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save(audio_path)
    
    return script_text, audio_path

def render_final_video(audio_path, video_files, output_path="final_short.mp4"):
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    
    clips = []
    for vf in video_files:
        try:
            clip = VideoFileClip(vf).without_audio()
            clip = clip.resize(height=1920)
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w/2, width=1080)
            clips.append(clip)
        except Exception as e:
            print("Clip error:", e)
            
    if not clips:
        return None
        
    final_clip = concatenate_videoclips(clips, method="compose")
    
    if final_clip.duration < audio_duration:
        final_clip = final_clip.loop(duration=audio_duration)
    else:
        final_clip = final_clip.subclip(0, audio_duration)
        
    final_clip = final_clip.set_audio(audio_clip)
    final_clip.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast")
    return output_path

if __name__ == "__main__":
    topic = "Secret Space Technologies"
    script, audio = asyncio.run(generate_assets(topic))
    clips = download_pixabay_videos(topic, target_count=4)
    render_final_video(audio, clips, "viral_short.mp4")
