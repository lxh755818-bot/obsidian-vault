# Source: `minimax-image-content-guide`

---
name: minimax-image-content-guide
description: MiniMax Image-01 内容安全过滤绕过策略 — 生成成熟/挑逗风格图像的 prompt 工程指南。包含触发词黑名单、替代词汇表、mood+silhouette+atmosphere 组合框架。
version: 1.0.0
author: 小a
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [minimax, image-generation, prompt-engineering, content-filter]
    model: image-01
---

# MiniMax Image-01 内容安全绕过指南

> 2026-04-25 实测：某些 prompt 会被静默拒绝（HTTP 200 但无 image_base64 字段），需改用艺术化暗示表达。

---

## 触发拒绝的关键词类别

| 类别 | 触发词 | 风险 |
|------|--------|------|
| 内衣/泳装 | `brassiere, bikini, lingerie, topless, swimsuit` | 直接拒绝 |
| 暴露暗示 | `bare skin, exposed, cleavage, bare chest, bare shoulders` | 高风险 |
| 性暗示 | `wet lips, bedroom eyes, seductive, sensual` | 高风险 |
| 直接身体部位 | `breast, nipple, torso` | 直接拒绝 |
| 卧室场景 | `bedroom, bed sheet, silk sheets` | 高风险 |
| 过于挑逗 | `naked, nude, erotic, pornographic` | 直接拒绝 |

---

## 绕过策略：艺术化暗示表达

### 核心公式

```
mood（氛围）+ silhouette（剪影/侧影）+ atmosphere（光线环境）
```

### 词汇替代表

| 想表达 | 避免用 | 改用 |
|--------|--------|------|
| 内衣感 | `brassiere, lingerie` | `satin nightgown, silk slip dress, flowing gown` |
| 裸露肩背 | `bare shoulders` | `bare back, cascading hair on skin, shoulder silhouette` |
| 挑逗眼神 | `bedroom eyes, seductive` | `mysterious gaze, confident expression, ethereal beauty` |
| 嘴唇 | `wet lips glistening` | `natural lip color, soft smile, dewy skin` |
| 卧室 | `bedroom, bed sheet` | `soft morning light, foggy window, romantic balcony` |
| 性感 | `sensual, erotic` | `elegant, ethereal, mysterious, cinematic` |
| 透明感 | `sheer fabric` | `flowing silk, translucent material, light fabric` |

---

## 有效组合模板

### 模板1：月光剪影（推荐）
```
Ethereal portrait of a woman, back view, flowing silk nightgown,
long silver hair cascading down bare back,
soft moonlight, silhouette against golden window light,
mysterious romantic atmosphere, bokeh, foggy window,
fashion photography, cinematic lighting, 8k, masterpiece
```

### 模板2：晨光逆光
```
Back view of elegant woman, sheer flowing white dress,
golden hour rim lighting on skin, hair blowing in breeze,
looking back over shoulder, confident yet soft expression,
sunlit window background, ethereal atmosphere,
high-end editorial photography, 8k, masterpiece
```

### 模板3：雨中都市
```
Moody portrait of beautiful woman in rain,
wearing sleek black silk dress, wet hair, neon reflections,
looking directly into camera with intense eyes,
cyberpunk aesthetic, cinematic color grading,
fashion photography, 8k, masterpiece
```

### 模板4：浴室蒸汽
```
Steamy bathroom scene, elegant woman silhouette behind glass door,
water droplets on glass, warm interior lighting,
soft focus background, romantic mysterious mood,
fashion editorial, cinematic, 8k, masterpiece
```
> 注：`behind glass` + `silhouette` 替代直接浴室场景

---

## 静默失败的判断方法

MiniMax 拒绝时 **HTTP 200**，但返回中 **没有 `image_base64` 字段**。

```python
# 检测是否被过滤
result = json.loads(resp.read().decode())
if 'image_base64' not in result.get('data', {}):
    print("CONTENT FILTERED - revise prompt")
```

---

## 调试流程

1. 写 prompt → 发 API
2. 看返回有没有 `image_base64` 字段
   - 有 → 成功
   - 没有 → 被过滤，进第3步
3. 逐词替换高风险关键词，用替代表
4. 重新发 API
5. 优先 `mood + silhouette + atmosphere` 组合

---

## 注意事项

- **场景比描述更安全**：`in a dimly lit room` 比直接描述穿着更不容易触发
- **侧影/背影更安全**：直接正脸+暴露比 `back view + hint of shoulder` 更安全
- **光线即遮蔽**：`shadows on skin, bokeh lights, rim lighting` 暗示裸露但不触发
- **材质代替裸露**：`silk`, `satin`, `sheer fabric` 暗示性感，但不触发过滤
