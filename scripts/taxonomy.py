# -*- coding: utf-8 -*-
"""赛事方向标签：从标题 / 赛道 / 简介里抽取可用于筛选的方向。

只做「规则匹配 + 多标签」，不调用模型，保证可解释、可复现。
"""
from __future__ import annotations

import re

# key, label, keywords
RULES = [
    ("agent", "智能体", ["智能体", "agent", "multi-agent", "多智能体", "autogen", "langgraph"]),
    ("llm", "大模型", ["大模型", "llm", "语言模型", "foundation model", "gpt", "qwen", "llama",
                      "千问", "文心", "混元", "豆包", "deepseek"]),
    ("embodied", "具身/机器人", ["具身", "机器人", "机械臂", "人形", "四足", "robotics", "embodied"]),
    ("aigc", "AIGC/生成式", ["aigc", "生成式", "文生图", "文生视频", "视频生成", "图像生成",
                            "音乐生成", "3d 生成", "3d生成", "扩散模型", "diffusion"]),
    ("multimodal", "多模态/视觉", ["多模态", "multimodal", "计算机视觉", "图像", "视频理解",
                                  "语音", "ocr", "目标检测", "分割", "识别"]),
    ("algorithm", "算法/数据", ["算法", "数据竞赛", "数据挖掘", "机器学习", "深度学习", "推荐",
                               "预测", "排序", "风控", "时间序列"]),
    ("compute", "算力/芯片", ["算力", "芯片", "推理", "训练", "gpu", "昇腾", "cann", "寒武纪",
                              "摩尔线程", "模型压缩", "端侧"]),
    ("autonomous", "自动驾驶/遥感", ["自动驾驶", "智能驾驶", "车载", "无人机", "遥感", "卫星",
                                    "车道", "感知"]),
    ("vertical", "行业应用", ["医疗", "医学", "金融", "银行", "保险", "教育", "工业", "制造",
                              "农业", "政务", "法律", "气象", "能源", "电力", "生物", "药物",
                              "交通", "城市"]),
    ("open", "开源/开放数据", ["开源", "开放数据", "open source", "数据集", "语料"]),
]

LABELS = {key: label for key, label, _ in RULES}
LABELS["other"] = "其他"
ORDER = [key for key, _, _ in RULES] + ["other"]


def _blob(rec: dict) -> str:
    parts = [
        rec.get("title") or "",
        " ".join(str(t) for t in (rec.get("tracks") or [])),
        rec.get("summary") or "",
        rec.get("notes") or "",
        rec.get("prize") or "",
    ]
    return " ".join(parts).lower()


def directions_for(rec: dict) -> list[str]:
    """返回 1–3 个方向 key；没有命中时返回 ['other']。"""
    blob = _blob(rec)
    hits = []
    for key, _, words in RULES:
        if any(w.lower() in blob for w in words):
            hits.append(key)
    if not hits:
        return ["other"]
    return hits[:3]


def direction_counts(records: list[dict]) -> list[tuple[str, str, int]]:
    counts = {key: 0 for key in ORDER}
    for rec in records:
        for key in rec.get("directions") or directions_for(rec):
            counts[key] = counts.get(key, 0) + 1
    return [(key, LABELS[key], counts.get(key, 0)) for key in ORDER if counts.get(key, 0)]


def clean_text(text: str, limit: int = 300) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s[:limit]
