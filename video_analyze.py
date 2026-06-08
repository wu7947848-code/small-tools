#!/usr/bin/env python
"""视频场景检测 + Qwen2-VL 动作识别"""

import sys
import cv2
import torch
from PIL import Image
from scenedetect import detect, ContentDetector

MODEL_PATH = "C:/Users/wangl/.cache/modelscope/hub/models/Qwen/Qwen2-VL-2B-Instruct"

def main(video_path):
    # 1. 场景检测
    print("正在检测场景切换...")
    scene_list = detect(video_path, ContentDetector())
    print(f"检测到 {len(scene_list)} 个场景\n")

    # 2. 加载模型
    print("正在加载 Qwen2-VL-2B 模型...")
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_PATH, torch_dtype="auto", device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    print("模型加载完成\n")

    # 3. 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"无法打开视频: {video_path}")
        sys.exit(1)

    # 4. 逐场景分析
    for i, (start, end) in enumerate(scene_list):
        mid_frame = (start.frame_num + end.frame_num) // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        if not ret:
            print(f"场景{i+1:02d}: 读取帧失败")
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": "请用简短中文描述图中人物的动作，只输出动作描述，不超过20个字。"},
                ],
            }
        ]

        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(
            text=[text], images=[pil_image], return_tensors="pt"
        ).to(model.device)

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=30)
        generated_ids = generated_ids[:, inputs.input_ids.shape[1]:]
        response = processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0].strip()

        start_tc = start.get_timecode()
        end_tc = end.get_timecode()
        print(f"场景{i+1:02d} [{start_tc} → {end_tc}]: {response}")

    cap.release()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python video_analyze.py <视频路径>")
        sys.exit(1)
    main(sys.argv[1])
