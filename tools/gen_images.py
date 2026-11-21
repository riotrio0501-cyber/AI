"""無料の画像生成AI（Animagine XL 4.0）をこのパソコンの中で動かして絵を作る。
設定: assets/image_plan.json
使い方:
  python3 tools/gen_images.py            # まだ無い絵だけ作る
  python3 tools/gen_images.py 父/close   # 指定した絵だけ作り直す
初回はモデル（約7GB）を Hugging Face から自動ダウンロードする。
"""
import json, sys, time
from pathlib import Path
import torch
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path.home() / "models"
torch.set_num_threads(max(1, torch.get_num_threads()))


def ensure_models():
    from huggingface_hub import snapshot_download, hf_hub_download
    m = MODELS / "animagine-xl-4.0"
    if not (m / "unet").exists():
        snapshot_download("cagliostrolab/animagine-xl-4.0", local_dir=str(m),
                          allow_patterns=["model_index.json", "scheduler/*", "text_encoder*/*", "tokenizer*/*", "unet/*", "vae/*"])
    l = MODELS / "lcm-lora-sdxl"
    if not (l / "pytorch_lora_weights.safetensors").exists():
        hf_hub_download("latent-consistency/lcm-lora-sdxl", "pytorch_lora_weights.safetensors", local_dir=str(l))
    return m, l


_pipes = {}


def pipes(plan):
    if _pipes:
        return _pipes
    from diffusers import (StableDiffusionXLPipeline, StableDiffusionXLInpaintPipeline,
                           LCMScheduler, EulerAncestralDiscreteScheduler)
    m, l = ensure_models()
    base = StableDiffusionXLPipeline.from_pretrained(str(m), torch_dtype=torch.bfloat16)
    if plan.get("fast", True):
        base.load_lora_weights(str(l)); base.fuse_lora()
        base.scheduler = LCMScheduler.from_config(base.scheduler.config)
    else:
        base.scheduler = EulerAncestralDiscreteScheduler.from_config(base.scheduler.config)
    _pipes["t2i"] = base
    _pipes["inpaint"] = StableDiffusionXLInpaintPipeline(**base.components)
    return _pipes


def out_path(name):
    a, b = name.split("/")
    if a == "shots":
        return ROOT / "assets/shots" / f"{b}.png"
    if a == "bg":
        return ROOT / "assets/backgrounds" / f"{b}.png"
    return ROOT / "assets/characters" / a / f"{b}.png"


def ellipse_mask(size, box, feather=12):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse(box, fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def generate(item, plan):
    p = pipes(plan)
    fast = plan.get("fast", True)
    steps, cfg = (item.get("steps", 8), item.get("cfg", 1.5)) if fast else (item.get("steps", 25), item.get("cfg", 5.0))
    prompt = f"{item['prompt']}, {plan['style']}"
    neg = plan["negative"] + (", " + item["negative"] if item.get("negative") else "")
    g = torch.Generator().manual_seed(item.get("seed", 0))
    w, h = item.get("size", plan.get("size", [832, 1216]))
    if "from" in item:  # 元の絵の一部（口や顔）だけ描き直す
        src = Image.open(out_path(item["from"])).convert("RGB")
        mask = ellipse_mask(src.size, item["mask"], item.get("feather", 12))
        res = p["inpaint"](prompt, negative_prompt=neg, image=src, mask_image=mask,
                           width=src.width, height=src.height, strength=item.get("strength", 0.85),
                           num_inference_steps=max(steps, int(steps / item.get("strength", 0.85)) + 1),
                           guidance_scale=cfg, generator=g).images[0]
        # マスクの外は元の絵のまま残す（顔や背景がズレないように）
        return Image.composite(res, src, mask)
    return p["t2i"](prompt, negative_prompt=neg, width=w, height=h, num_inference_steps=steps,
                    guidance_scale=cfg, generator=g).images[0]


def main():
    plan = json.loads((ROOT / "assets/image_plan.json").read_text())
    only = sys.argv[1:]
    for item in plan["images"]:
        out = out_path(item["name"])
        if only and item["name"] not in only:
            continue
        if not only and out.exists():
            continue
        if "from" in item and "mask" not in item:
            print(f"  {item['name']}: 口の位置(mask)が未設定なのでスキップ"); continue
        t = time.time()
        img = generate(item, plan)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        print(f"  {item['name']} → {out.relative_to(ROOT)} ({time.time() - t:.0f}秒)")


if __name__ == "__main__":
    main()
