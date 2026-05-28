import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from dotenv import load_dotenv, dotenv_values 
import gradio as gr
import uuid
import os
import glob
import gc

load_dotenv() 
# 1. Local Environment Setup
os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN") 
os.environ['HF_HOME'] = os.getenv("HF_HOME")

# 2. Load the Pipeline
print("Downloading/Loading CogVideoX-2B to local hard drive...")
print("Grab a coffee, this will take a while...")
pipe = CogVideoXPipeline.from_pretrained(
    "THUDM/CogVideoX-2b", 
    torch_dtype=torch.float16
)

# 3. Extreme VRAM Survival Hacks for 6GB GPUs
print("Applying memory optimizations...")
pipe.enable_sequential_cpu_offload() 
pipe.vae.enable_slicing()
pipe.vae.enable_tiling()

def cleanup_old_videos(directory="./generated_videos", max_files=5):
    if not os.path.exists(directory): return
    files = glob.glob(f"{directory}/*.mp4")
    if len(files) <= max_files: return
    files.sort(key=os.path.getctime)
    while len(files) > max_files:
        try: os.remove(files.pop(0))
        except: pass

# 4. The Generation Function
def generate_video(prompt, progress=gr.Progress(track_tqdm=True)):
    # Flush local memory before starting
    gc.collect()
    torch.cuda.empty_cache()
    
    # Dropped steps to 15 so your laptop doesn't take 3 hours
    video_frames = pipe(
        prompt=prompt,
        num_inference_steps=15, 
        guidance_scale=6.0,
    ).frames[0]
    
    os.makedirs("./generated_videos", exist_ok=True)
    cleanup_old_videos("./generated_videos", max_files=5)
    
    out_path = f"./generated_videos/{uuid.uuid4()}.mp4"
    export_to_video(video_frames, out_path, fps=8)
    
    return out_path

# 5. The Gradio UI
with gr.Blocks(theme=gr.themes.Soft(), css="footer {visibility: hidden;}") as demo:
    gr.Markdown("# 🎬 AI Video Generator")
    
    with gr.Row():
        with gr.Column(scale=1): 
            prompt_in = gr.Textbox(
                label="Text Prompt", 
                placeholder="A cinematic drone shot...",
                lines=7
            )
            submit_btn = gr.Button("Generate Video", variant="primary")
            
        with gr.Column(scale=1):
            video_out = gr.Video(label="Generated Video", height=320, interactive=False)
            
    submit_btn.click(
        fn=generate_video,
        inputs=[prompt_in],
        outputs=video_out
    )

# Run it on your local browser!
demo.launch()